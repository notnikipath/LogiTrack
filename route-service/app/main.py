from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from shared.logitrack_common import (
    Role,
    RoutePlan,
    RouteRequest,
    RouteRerouteRequest,
    RouteStatus,
    Settings,
    ShipmentOrder,
    TransportMode,
    Waypoint,
    build_audit_event,
    has_permission,
    predict_eta_minutes,
    reroute_eta_delta,
)

settings = Settings(service_name="route-service", service_port=8402)
app = FastAPI(title="LogiTrack Route Service", version="1.0.0")

routes: dict[str, RoutePlan] = {}
audit_log: list[dict[str, Any]] = []


class RouteCalculationRequest(BaseModel):
    order: ShipmentOrder
    traffic_index: float = 0.3
    weather_risk: float = 0.2
    actor_id: str
    actor_role: Role


class RouteAssignRequest(BaseModel):
    vehicle_id: str
    actor_id: str
    actor_role: Role


RouteCalculationRequest.model_rebuild()
RouteAssignRequest.model_rebuild()


def _assert_permission(role: Role, action: str) -> None:
    if not has_permission(role, action):
        raise HTTPException(status_code=403, detail=f"Role {role.value} cannot perform {action}")


def _audit(actor_id: str, actor_role: Role, action: str, object_id: str, details: dict[str, Any] | None = None) -> None:
    audit_log.append(
        build_audit_event(
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            object_type="route",
            object_id=object_id,
            details=details or {},
        ).model_dump(mode="json")
    )


def _hub_for_mode(mode: TransportMode) -> str:
    return {
        TransportMode.ROAD: "Транспортный хаб М7",
        TransportMode.RAIL: "Сортировочная станция Вязьма",
        TransportMode.SEA: "Порт Санкт-Петербург",
        TransportMode.AIR: "Карго-терминал Шереметьево",
        TransportMode.MULTIMODAL: "Мультимодальный терминал Владимир",
    }[mode]


def _build_route(order: ShipmentOrder, traffic_index: float, weather_risk: float) -> RoutePlan:
    stop_count = 2 if order.transport_mode == TransportMode.MULTIMODAL else 1
    duration = predict_eta_minutes(
        order.distance_km,
        order.transport_mode,
        traffic_index,
        weather_risk,
        stop_count=stop_count,
    )
    now = datetime.now(UTC)
    eta = now + timedelta(minutes=duration)
    waypoints = [
        Waypoint(waypoint_id=str(uuid4()), sequence=1, location=order.origin, eta=now),
        Waypoint(
            waypoint_id=str(uuid4()),
            sequence=2,
            location=_hub_for_mode(order.transport_mode),
            eta=now + timedelta(minutes=max(duration // 2, 30)),
            stop_minutes=40,
        ),
        Waypoint(waypoint_id=str(uuid4()), sequence=3, location=order.destination, eta=eta),
    ]
    optimization_score = round(max(60.0, 96 - traffic_index * 20 - weather_risk * 14 - stop_count * 2), 2)
    return RoutePlan(
        route_id=str(uuid4()),
        order_id=order.order_id,
        transport_mode=order.transport_mode,
        distance_km=order.distance_km,
        estimated_duration_minutes=duration,
        estimated_eta=eta,
        traffic_index=traffic_index,
        weather_risk=weather_risk,
        waypoints=waypoints,
        status=RouteStatus.DRAFT,
        optimization_score=optimization_score,
    )


def _seed_demo() -> None:
    demo_order = ShipmentOrder(
        order_id="ORD-DEMO",
        customer_id="CUST-001",
        origin="Москва",
        destination="Казань",
        transport_mode=TransportMode.ROAD,
        cargo_type="refrigerated",
        weight_kg=8200,
        volume_m3=34,
        distance_km=1540,
        delivery_deadline=datetime.now(UTC) + timedelta(days=2),
        cost={"base_cost": 0, "fuel_surcharge": 0, "cold_chain_surcharge": 0, "customs_surcharge": 0, "total_cost": 0},
    )
    route = _build_route(demo_order, 0.34, 0.18)
    route.route_id = "ROUTE-DEMO"
    route.status = RouteStatus.ASSIGNED
    route.assigned_vehicle_id = "VEH-101"
    routes[route.route_id] = route


_seed_demo()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.get("/routes")
async def list_routes(order_id: str | None = None) -> dict[str, Any]:
    items = []
    for route in routes.values():
        if order_id and route.order_id != order_id:
            continue
        items.append(route.model_dump(mode="json"))
    items.sort(key=lambda item: item["estimated_eta"])
    return {"items": items, "count": len(items)}


@app.get("/routes/{route_id}")
async def get_route(route_id: str) -> dict[str, Any]:
    route = routes.get(route_id)
    if route is None:
        raise HTTPException(status_code=404, detail="Route not found")
    return route.model_dump(mode="json")


@app.post("/routes/calculate")
async def calculate_route(request: RouteCalculationRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "route:create")
    route = _build_route(request.order, request.traffic_index, request.weather_risk)
    routes[route.route_id] = route
    _audit(
        request.actor_id,
        request.actor_role,
        "route.calculate",
        route.route_id,
        {"order_id": request.order.order_id},
    )
    return route.model_dump(mode="json")


@app.post("/routes/plan")
async def plan_route(request: RouteRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "route:create")
    for route in routes.values():
        if route.order_id == request.order_id:
            return route.model_dump(mode="json")
    raise HTTPException(status_code=404, detail="No synced order snapshot for route planning")


@app.post("/routes/{route_id}/assign")
async def assign_vehicle(route_id: str, request: RouteAssignRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "route:update")
    route = routes.get(route_id)
    if route is None:
        raise HTTPException(status_code=404, detail="Route not found")
    route.assigned_vehicle_id = request.vehicle_id
    route.status = RouteStatus.ASSIGNED
    _audit(request.actor_id, request.actor_role, "route.assign_vehicle", route_id, {"vehicle_id": request.vehicle_id})
    return route.model_dump(mode="json")


@app.post("/routes/{route_id}/reroute")
async def reroute(route_id: str, request: RouteRerouteRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "route:update")
    route = routes.get(route_id)
    if route is None:
        raise HTTPException(status_code=404, detail="Route not found")
    route.estimated_duration_minutes = reroute_eta_delta(
        route.estimated_duration_minutes,
        request.traffic_delay_minutes,
        request.weather_risk,
    )
    route.weather_risk = request.weather_risk
    route.estimated_eta = datetime.now(UTC) + timedelta(minutes=route.estimated_duration_minutes)
    if route.waypoints:
        route.waypoints[-1].eta = route.estimated_eta
    route.status = RouteStatus.REROUTED
    _audit(
        request.actor_id,
        request.actor_role,
        "route.reroute",
        route_id,
        {"delay_minutes": request.traffic_delay_minutes},
    )
    return route.model_dump(mode="json")


@app.get("/calendar")
async def route_calendar() -> dict[str, Any]:
    items = [
        {
            "route_id": route.route_id,
            "order_id": route.order_id,
            "estimated_eta": route.estimated_eta,
            "status": route.status,
            "assigned_vehicle_id": route.assigned_vehicle_id,
        }
        for route in routes.values()
    ]
    return {"items": items, "count": len(items)}


@app.get("/audit")
async def get_audit(limit: int = 100, actor_role: Role = Role.ADMIN) -> dict[str, Any]:
    _assert_permission(actor_role, "audit:read")
    return {"items": audit_log[-limit:]}

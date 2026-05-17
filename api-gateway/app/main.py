from __future__ import annotations

from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from shared.logitrack_common import AssignRouteWorkflowResult, Role, Settings, sign_token, verify_token


class GatewaySettings(BaseSettings):
    service_name: str = "api-gateway"
    service_port: int = 8400

    order_service_url: str = "http://order-service:8401"
    route_service_url: str = "http://route-service:8402"
    tracking_service_url: str = "http://tracking-service:8403"
    warehouse_service_url: str = "http://warehouse-service:8404"
    integration_service_url: str = "http://integration-service:8405"
    analytics_service_url: str = "http://analytics-service:8406"
    notification_service_url: str = "http://notification-service:8407"

    jwt_secret: str = Settings().jwt_secret
    token_exp_minutes: int = 240

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = GatewaySettings()
app = FastAPI(title="LogiTrack API Gateway", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5177",
        "http://127.0.0.1:5177",
        "http://localhost:5176",
        "http://127.0.0.1:5176",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AuthRequest(BaseModel):
    user_id: str
    role: Role
    language: str = Field(default="ru", pattern="^(ru|en)$")


class AssignRouteRequest(BaseModel):
    order_id: str
    traffic_index: float = Field(default=0.3, ge=0, le=1)
    weather_risk: float = Field(default=0.2, ge=0, le=1)
    actor_id: str
    actor_role: Role


class RerouteWorkflowRequest(BaseModel):
    route_id: str
    traffic_delay_minutes: int = Field(ge=0)
    weather_risk: float = Field(ge=0, le=1)
    recipient: str
    actor_id: str
    actor_role: Role


AuthRequest.model_rebuild()
AssignRouteRequest.model_rebuild()
RerouteWorkflowRequest.model_rebuild()


async def _post_json(client: httpx.AsyncClient, url: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = await client.post(url, json=payload)
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()


async def _get_json(client: httpx.AsyncClient, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    response = await client.get(url, params=params)
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()


def _service_urls() -> dict[str, str]:
    return {
        "order": settings.order_service_url,
        "route": settings.route_service_url,
        "tracking": settings.tracking_service_url,
        "warehouse": settings.warehouse_service_url,
        "integration": settings.integration_service_url,
        "analytics": settings.analytics_service_url,
        "notification": settings.notification_service_url,
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/auth/token")
async def issue_token(request: AuthRequest) -> dict[str, str]:
    token = sign_token(
        {"sub": request.user_id, "role": request.role.value, "language": request.language},
        settings.jwt_secret,
        exp_minutes=settings.token_exp_minutes,
    )
    return {"access_token": token, "token_type": "Bearer"}


@app.post("/auth/verify")
async def verify_auth(token: str) -> dict[str, Any]:
    payload = verify_token(token, settings.jwt_secret)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload


@app.get("/services/health")
async def service_health() -> dict[str, Any]:
    statuses: dict[str, Any] = {}
    async with httpx.AsyncClient(timeout=10.0) as client:
        for name, base_url in _service_urls().items():
            try:
                statuses[name] = await _get_json(client, f"{base_url}/health")
            except HTTPException as exc:
                statuses[name] = {"status": "error", "detail": exc.detail}
            except httpx.HTTPError as exc:
                statuses[name] = {"status": "error", "detail": str(exc)}
    return statuses


@app.post("/workflow/assign-route")
async def assign_route_workflow(request: AssignRouteRequest) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=25.0) as client:
        order = await _get_json(client, f"{settings.order_service_url}/orders/{request.order_id}")
        await _post_json(
            client,
            f"{settings.integration_service_url}/integrations/gps/sync",
            {
                "system_name": "gps",
                "payload": {"order_id": request.order_id, "tracks": 4800},
                "actor_id": request.actor_id,
                "actor_role": request.actor_role.value,
            },
        )
        route = await _post_json(
            client,
            f"{settings.route_service_url}/routes/calculate",
            {
                "order": order,
                "traffic_index": request.traffic_index,
                "weather_risk": request.weather_risk,
                "actor_id": request.actor_id,
                "actor_role": request.actor_role.value,
            },
        )
        available = await _get_json(
            client,
            f"{settings.tracking_service_url}/vehicles/available",
            {"mode": order["transport_mode"], "capacity_kg": order["weight_kg"]},
        )
        if not available["items"]:
            raise HTTPException(status_code=409, detail="No available vehicle for requested load")
        vehicle = available["items"][0]
        assignment = await _post_json(
            client,
            f"{settings.tracking_service_url}/vehicles/assign",
            {
                "vehicle_id": vehicle["vehicle_id"],
                "order_id": request.order_id,
                "route_id": route["route_id"],
                "actor_id": request.actor_id,
                "actor_role": request.actor_role.value,
            },
        )
        await _post_json(
            client,
            f"{settings.route_service_url}/routes/{route['route_id']}/assign",
            {
                "vehicle_id": vehicle["vehicle_id"],
                "actor_id": request.actor_id,
                "actor_role": request.actor_role.value,
            },
        )
        notification = await _post_json(
            client,
            f"{settings.notification_service_url}/notify/driver-route",
            {
                "driver_id": vehicle["driver_id"],
                "route_id": route["route_id"],
                "order_id": request.order_id,
                "eta": route["estimated_eta"],
                "actor_role": Role.DISPATCHER.value,
            },
        )
        analytics = await _post_json(
            client,
            f"{settings.analytics_service_url}/analytics/ingest/route",
            {
                "order_id": request.order_id,
                "route_id": route["route_id"],
                "vehicle_id": vehicle["vehicle_id"],
                "driver_id": vehicle["driver_id"],
                "predicted_duration_minutes": route["estimated_duration_minutes"],
                "total_cost": order["cost"]["total_cost"],
                "distance_km": order["distance_km"],
                "load_kg": order["weight_kg"],
                "capacity_kg": vehicle["capacity_kg"],
            },
        )
        await _post_json(
            client,
            f"{settings.order_service_url}/orders/{request.order_id}/status",
            {
                "status": "planned",
                "actor_id": request.actor_id,
                "actor_role": request.actor_role.value,
            },
        )
    result = AssignRouteWorkflowResult(
        order=order,
        route=route,
        vehicle=assignment["vehicle"],
        notification=notification,
        analytics=analytics,
    )
    return result.model_dump(mode="json")


@app.post("/workflow/reroute")
async def reroute_workflow(request: RerouteWorkflowRequest) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=20.0) as client:
        route = await _post_json(
            client,
            f"{settings.route_service_url}/routes/{request.route_id}/reroute",
            {
                "traffic_delay_minutes": request.traffic_delay_minutes,
                "weather_risk": request.weather_risk,
                "actor_id": request.actor_id,
                "actor_role": request.actor_role.value,
            },
        )
        notification = await _post_json(
            client,
            f"{settings.notification_service_url}/notify/delay",
            {
                "recipient": request.recipient,
                "order_id": route["order_id"],
                "delay_minutes": request.traffic_delay_minutes,
                "actor_role": Role.DISPATCHER.value,
            },
        )
    return {"route": route, "notification": notification}


@app.get("/dashboard/{order_id}/{vehicle_id}")
async def dashboard(order_id: str, vehicle_id: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=20.0) as client:
        order = await _get_json(client, f"{settings.order_service_url}/orders/{order_id}")
        routes = await _get_json(client, f"{settings.route_service_url}/routes", {"order_id": order_id})
        tracking = await _get_json(client, f"{settings.tracking_service_url}/tracking/{vehicle_id}")
        violations = await _get_json(client, f"{settings.tracking_service_url}/violations/{vehicle_id}")
        warehouse = await _get_json(client, f"{settings.warehouse_service_url}/dashboard")
        inventory = await _get_json(client, f"{settings.warehouse_service_url}/inventory")
        fleet = await _get_json(
            client,
            f"{settings.analytics_service_url}/analytics/fleet",
            {"actor_role": Role.DISPATCHER.value},
        )
        kpi = await _get_json(client, f"{settings.analytics_service_url}/analytics/kpi")
        integration = await _get_json(client, f"{settings.integration_service_url}/integrations/history")
        notifications = await _get_json(client, f"{settings.notification_service_url}/notify/history")
        assignment = None
        try:
            assignment = await _get_json(client, f"{settings.tracking_service_url}/assignments/{order_id}")
        except HTTPException:
            assignment = {
                "vehicle_id": vehicle_id,
                "driver_id": "N/A",
                "route_id": routes["items"][0]["route_id"] if routes["items"] else "N/A",
            }
        if assignment.get("driver_id") not in {None, "N/A"}:
            driver_metrics = await _get_json(
                client,
                f"{settings.analytics_service_url}/analytics/driver/{assignment['driver_id']}",
            )
        else:
            driver_metrics = {
                "driver_id": "N/A",
                "kpi": 0,
                "on_time_ratio": 0,
                "incident_rate": 0,
                "fuel_efficiency": 0,
            }

    return {
        "order": order,
        "routes": routes,
        "tracking": tracking,
        "violations": violations,
        "warehouse": warehouse,
        "inventory": inventory,
        "fleet": fleet,
        "kpi": kpi,
        "integration": integration,
        "notifications": notifications,
        "assignment": assignment,
        "driver_metrics": driver_metrics,
    }

from __future__ import annotations

from statistics import mean
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from shared.logitrack_common import (
    Role,
    Settings,
    cost_per_km,
    driver_kpi,
    eta_mape,
    has_permission,
    route_build_seconds,
    transport_load,
)

settings = Settings(service_name="analytics-service", service_port=8406)
app = FastAPI(title="LogiTrack Analytics Service", version="1.0.0")

predicted_eta_samples: list[float] = [1180, 1260, 990, 1410]
actual_eta_samples: list[float] = [1235, 1305, 1020, 1488]
load_samples: list[float] = [0.71, 0.78, 0.82]
cost_per_km_samples: list[float] = [51.4, 48.9, 53.1]
driver_profiles: dict[str, dict[str, Any]] = {
    "DRV-007": {"on_time_ratio": 0.92, "incident_rate": 0.08, "fuel_efficiency": 0.81},
    "DRV-021": {"on_time_ratio": 0.87, "incident_rate": 0.11, "fuel_efficiency": 0.76},
}
route_records: dict[str, dict[str, Any]] = {}


class RouteIngestRequest(BaseModel):
    order_id: str
    route_id: str
    vehicle_id: str
    driver_id: str
    predicted_duration_minutes: float = Field(gt=0)
    actual_duration_minutes: float | None = Field(default=None, gt=0)
    total_cost: float = Field(ge=0)
    distance_km: float = Field(gt=0)
    load_kg: float = Field(ge=0)
    capacity_kg: float = Field(gt=0)


class TelemetryAnalyticsRequest(BaseModel):
    vehicle_id: str
    driver_id: str
    incident_count: int = Field(ge=0)
    fuel_efficiency: float = Field(ge=0, le=1)
    load_kg: float = Field(ge=0)
    capacity_kg: float = Field(gt=0)


RouteIngestRequest.model_rebuild()
TelemetryAnalyticsRequest.model_rebuild()


def _assert_permission(role: Role, action: str) -> None:
    if not has_permission(role, action):
        raise HTTPException(status_code=403, detail=f"Role {role.value} cannot {action}")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/analytics/ingest/route")
async def ingest_route(request: RouteIngestRequest) -> dict[str, Any]:
    actual = request.actual_duration_minutes or round(request.predicted_duration_minutes * 1.06, 2)
    predicted_eta_samples.append(request.predicted_duration_minutes)
    actual_eta_samples.append(actual)
    load_ratio = transport_load(request.load_kg, request.capacity_kg)
    cpk = cost_per_km(request.total_cost, request.distance_km)
    load_samples.append(load_ratio)
    cost_per_km_samples.append(cpk)
    route_records[request.order_id] = {
        "order_id": request.order_id,
        "route_id": request.route_id,
        "vehicle_id": request.vehicle_id,
        "driver_id": request.driver_id,
        "predicted_duration_minutes": request.predicted_duration_minutes,
        "actual_duration_minutes": actual,
        "cost_per_km": cpk,
        "load_ratio": load_ratio,
    }
    return {
        "status": "accepted",
        "order_id": request.order_id,
        "eta_mape": eta_mape(predicted_eta_samples, actual_eta_samples),
    }


@app.post("/analytics/ingest/telemetry")
async def ingest_telemetry(request: TelemetryAnalyticsRequest) -> dict[str, Any]:
    profile = driver_profiles.setdefault(
        request.driver_id,
        {"on_time_ratio": 0.88, "incident_rate": 0.1, "fuel_efficiency": request.fuel_efficiency},
    )
    profile["incident_rate"] = min(1.0, round((profile["incident_rate"] + request.incident_count / 10) / 2, 2))
    profile["fuel_efficiency"] = round((profile["fuel_efficiency"] + request.fuel_efficiency) / 2, 2)
    load_samples.append(transport_load(request.load_kg, request.capacity_kg))
    return {"status": "accepted", "driver_id": request.driver_id}


@app.get("/analytics/order/{order_id}")
async def order_metrics(order_id: str) -> dict[str, Any]:
    if order_id not in route_records:
        raise HTTPException(status_code=404, detail="Order analytics not found")
    return route_records[order_id]


@app.get("/analytics/driver/{driver_id}")
async def driver_metrics(driver_id: str) -> dict[str, Any]:
    profile = driver_profiles.get(driver_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Driver not found")
    score = driver_kpi(profile["on_time_ratio"], profile["incident_rate"], profile["fuel_efficiency"])
    return {"driver_id": driver_id, **profile, "kpi": score}


@app.get("/analytics/fleet")
async def fleet_metrics(actor_role: Role = Role.DISPATCHER) -> dict[str, Any]:
    _assert_permission(actor_role, "analytics:read")
    return {
        "avg_load_ratio": round(mean(load_samples), 2) if load_samples else 0.0,
        "avg_cost_per_km": round(mean(cost_per_km_samples), 2) if cost_per_km_samples else 0.0,
        "eta_mape": eta_mape(predicted_eta_samples, actual_eta_samples),
        "tracked_routes": len(route_records),
    }


@app.get("/analytics/kpi")
async def kpi() -> dict[str, Any]:
    return {
        "route_build_seconds_estimate": route_build_seconds(
            cache_hit_ratio=0.78,
            complexity_score=1.1,
            in_memory_boost=True,
        ),
        "eta_mape_pct": eta_mape(predicted_eta_samples, actual_eta_samples),
        "avg_load_ratio": round(mean(load_samples), 2) if load_samples else 0.0,
        "target_route_build_seconds": settings.route_build_target_seconds,
        "target_eta_mape_pct": settings.eta_mape_target,
        "capacity_target_vehicles": settings.concurrent_vehicle_target,
    }


@app.get("/dashboards/{role}")
async def dashboard(role: Role) -> dict[str, Any]:
    widgets = {
        Role.DRIVER: ["current_route", "alerts", "fuel", "chat"],
        Role.DISPATCHER: ["fleet_map", "eta_risk", "delays", "driver_kpi"],
        Role.LOGISTICIAN: ["order_cost", "capacity", "integrations", "warehouse"],
        Role.WAREHOUSE: ["zones", "shipments", "receipts", "critical_stock"],
        Role.ADMIN: ["audit", "throughput", "integrations", "capacity_target"],
    }
    return {"role": role.value, "widgets": widgets[role], "fleet": await fleet_metrics(Role.DISPATCHER)}

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException

from shared.logitrack_common import (
    DriverAlert,
    Role,
    Settings,
    TelemetryBatch,
    TelemetryPoint,
    TransportMode,
    Vehicle,
    VehicleAssignmentRequest,
    build_audit_event,
    detect_driver_violations,
    has_permission,
    parallel_track_plan,
)

settings = Settings(service_name="tracking-service", service_port=8403)
app = FastAPI(title="LogiTrack Tracking Service", version="1.0.0")

vehicles: dict[str, Vehicle] = {
    "VEH-101": Vehicle(
        vehicle_id="VEH-101",
        plate_number="А123ВС77",
        mode=TransportMode.ROAD,
        capacity_kg=12000,
        temperature_control=True,
        region="ЦФО",
        driver_id="DRV-007",
        status="available",
        current_location="Москва",
    ),
    "VEH-202": Vehicle(
        vehicle_id="VEH-202",
        plate_number="В456ОР16",
        mode=TransportMode.ROAD,
        capacity_kg=9500,
        temperature_control=False,
        region="ПФО",
        driver_id="DRV-021",
        status="available",
        current_location="Нижний Новгород",
    ),
    "VEH-303": Vehicle(
        vehicle_id="VEH-303",
        plate_number="TRN-88",
        mode=TransportMode.RAIL,
        capacity_kg=42000,
        temperature_control=False,
        region="Урал",
        driver_id="DRV-RAIL-1",
        status="available",
        current_location="Екатеринбург",
    ),
}
telemetry_store: dict[str, list[TelemetryPoint]] = {
    "VEH-101": [
        TelemetryPoint(
            vehicle_id="VEH-101",
            timestamp=datetime.now(UTC) - timedelta(minutes=20),
            latitude=55.7558,
            longitude=37.6176,
            speed_kph=72,
            fuel_level_pct=78,
            cargo_temp_c=4.0,
            rest_gap_hours=2.5,
        )
    ]
}
assignments: dict[str, dict[str, str]] = {
    "ORD-DEMO": {
        "vehicle_id": "VEH-101",
        "route_id": "ROUTE-DEMO",
        "driver_id": "DRV-007",
    }
}
alerts: dict[str, list[DriverAlert]] = {"VEH-101": []}
audit_log: list[dict[str, Any]] = []


def _assert_permission(role: Role, action: str) -> None:
    if not has_permission(role, action):
        raise HTTPException(status_code=403, detail=f"Role {role.value} cannot perform {action}")


def _audit(actor_id: str, actor_role: Role, action: str, object_id: str, details: dict[str, Any] | None = None) -> None:
    audit_log.append(
        build_audit_event(
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            object_type="tracking",
            object_id=object_id,
            details=details or {},
        ).model_dump(mode="json")
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.get("/vehicles")
async def list_vehicles(mode: TransportMode | None = None) -> dict[str, Any]:
    items = []
    for vehicle in vehicles.values():
        if mode and vehicle.mode != mode:
            continue
        items.append(vehicle.model_dump(mode="json"))
    return {"items": items, "count": len(items)}


@app.get("/vehicles/available")
async def available_vehicles(mode: TransportMode, capacity_kg: float = 0) -> dict[str, Any]:
    items = [
        vehicle.model_dump(mode="json")
        for vehicle in vehicles.values()
        if vehicle.mode == mode and vehicle.status == "available" and vehicle.capacity_kg >= capacity_kg
    ]
    return {"items": items, "count": len(items)}


@app.post("/vehicles/assign")
async def assign_vehicle(request: VehicleAssignmentRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "tracking:assign")
    vehicle = vehicles.get(request.vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    if vehicle.status != "available":
        raise HTTPException(status_code=409, detail="Vehicle is not available")
    vehicle.status = "assigned"
    assignments[request.order_id] = {
        "vehicle_id": request.vehicle_id,
        "route_id": request.route_id,
        "driver_id": vehicle.driver_id,
    }
    _audit(
        request.actor_id,
        request.actor_role,
        "tracking.assign_vehicle",
        request.vehicle_id,
        {"order_id": request.order_id},
    )
    return {
        "vehicle": vehicle.model_dump(mode="json"),
        "assignment": assignments[request.order_id],
    }


@app.post("/telemetry/ingest")
async def ingest_telemetry(request: TelemetryBatch) -> dict[str, Any]:
    if request.actor_role not in {Role.DRIVER, Role.DISPATCHER, Role.ADMIN}:
        raise HTTPException(status_code=403, detail="Forbidden")
    accepted = 0
    violations_count = 0
    for point in request.points:
        telemetry_store.setdefault(point.vehicle_id, []).append(point)
        accepted += 1
        findings = detect_driver_violations([point.speed_kph], point.rest_gap_hours)
        for finding in findings:
            alert = DriverAlert(
                alert_id=str(uuid4()),
                vehicle_id=point.vehicle_id,
                driver_id=vehicles.get(point.vehicle_id, Vehicle(
                    vehicle_id=point.vehicle_id,
                    plate_number="UNKNOWN",
                    mode=TransportMode.ROAD,
                    capacity_kg=1,
                    region="UNKNOWN",
                    driver_id="UNKNOWN",
                    current_location="UNKNOWN",
                )).driver_id,
                severity=finding["severity"],
                message=finding["message"],
            )
            alerts.setdefault(point.vehicle_id, []).append(alert)
            violations_count += 1
    return {"accepted": accepted, "violations_detected": violations_count}


@app.get("/tracking/{vehicle_id}")
async def vehicle_track(vehicle_id: str) -> dict[str, Any]:
    return {
        "vehicle_id": vehicle_id,
        "items": [point.model_dump(mode="json") for point in telemetry_store.get(vehicle_id, [])][-100:],
    }


@app.get("/violations/{vehicle_id}")
async def violation_feed(vehicle_id: str) -> dict[str, Any]:
    return {
        "vehicle_id": vehicle_id,
        "items": [alert.model_dump(mode="json") for alert in alerts.get(vehicle_id, [])],
        "count": len(alerts.get(vehicle_id, [])),
    }


@app.get("/processing/parallel-plan")
async def processing_plan(track_count: int = 5000, regions: int = 8) -> dict[str, int]:
    return parallel_track_plan(track_count, regions)


@app.get("/assignments/{order_id}")
async def get_assignment(order_id: str) -> dict[str, Any]:
    assignment = assignments.get(order_id)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return assignment


@app.get("/audit")
async def get_audit(limit: int = 100, actor_role: Role = Role.ADMIN) -> dict[str, Any]:
    _assert_permission(actor_role, "audit:read")
    return {"items": audit_log[-limit:]}

from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException

from shared.logitrack_common import (
    IntegrationSyncRequest,
    IntegrationSyncResult,
    Role,
    Settings,
    build_audit_event,
    has_permission,
    recommend_map_cache_regions,
)

settings = Settings(service_name="integration-service", service_port=8405)
app = FastAPI(title="LogiTrack Integration Service", version="1.0.0")

sync_history: list[IntegrationSyncResult] = [
    IntegrationSyncResult(
        sync_id="SYNC-001",
        system_name="gps",
        status="ok",
        details={"provider": "GLONASS", "vehicles": 1240},
    )
]
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
            object_type="integration",
            object_id=object_id,
            details=details or {},
        ).model_dump(mode="json")
    )


def _register_sync(system_name: str, details: dict[str, Any], actor_id: str, actor_role: Role) -> dict[str, Any]:
    result = IntegrationSyncResult(sync_id=str(uuid4()), system_name=system_name, status="ok", details=details)
    sync_history.append(result)
    _audit(actor_id, actor_role, f"integration.{system_name}.sync", result.sync_id, details)
    return result.model_dump(mode="json")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/integrations/sync")
async def generic_sync(request: IntegrationSyncRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "integration:manage")
    return _register_sync(request.system_name, request.payload, request.actor_id, request.actor_role)


@app.post("/integrations/gps/sync")
async def gps_sync(request: IntegrationSyncRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "integration:manage")
    details = {"provider": "GPS", "tracks": request.payload.get("tracks", 4800), "status": "streaming"}
    return _register_sync("gps", details, request.actor_id, request.actor_role)


@app.post("/integrations/glonass/sync")
async def glonass_sync(request: IntegrationSyncRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "integration:manage")
    details = {"provider": "GLONASS", "vehicles": request.payload.get("vehicles", 1200), "status": "online"}
    return _register_sync("glonass", details, request.actor_id, request.actor_role)


@app.post("/integrations/1c-erp/export")
async def export_1c(request: IntegrationSyncRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "integration:manage")
    details = {"documents": request.payload.get("documents", 12), "direction": "export", "system": "1C:ERP"}
    return _register_sync("1c_erp", details, request.actor_id, request.actor_role)


@app.get("/maps/cache/plan")
async def map_cache_plan(regions: str = "ЦФО,ПФО,ЮФО") -> dict[str, Any]:
    region_list = [item.strip() for item in regions.split(",") if item.strip()]
    return {"priority_regions": recommend_map_cache_regions(region_list), "provider": settings.maps_provider_url}


@app.get("/integrations/history")
async def history(system_name: str | None = None) -> dict[str, Any]:
    items = [
        item.model_dump(mode="json")
        for item in sync_history
        if not system_name or item.system_name == system_name
    ]
    return {"items": items, "count": len(items)}


@app.get("/audit")
async def get_audit(limit: int = 100, actor_role: Role = Role.ADMIN) -> dict[str, Any]:
    _assert_permission(actor_role, "audit:read")
    return {"items": audit_log[-limit:]}

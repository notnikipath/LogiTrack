from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException

from shared.logitrack_common import (
    Role,
    Settings,
    WarehouseItem,
    WarehouseOperation,
    WarehouseOperationRequest,
    WarehouseOperationType,
    build_audit_event,
    has_permission,
)

settings = Settings(service_name="warehouse-service", service_port=8404)
app = FastAPI(title="LogiTrack Warehouse Service", version="1.0.0")

inventory: dict[str, WarehouseItem] = {
    "SKU-APPLE": WarehouseItem(
        sku="SKU-APPLE",
        description="Охлажденные продукты",
        quantity=180,
        zone="COLD-A1",
        weight_kg=14.2,
    ),
    "SKU-TV": WarehouseItem(
        sku="SKU-TV",
        description="Телевизоры 43\"",
        quantity=42,
        zone="DRY-B2",
        weight_kg=9.5,
    ),
    "SKU-MED": WarehouseItem(
        sku="SKU-MED",
        description="Медицинские наборы",
        quantity=90,
        zone="SAFE-C1",
        weight_kg=2.8,
    ),
}
operations: list[WarehouseOperation] = []
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
            object_type="warehouse",
            object_id=object_id,
            details=details or {},
        ).model_dump(mode="json")
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.get("/inventory")
async def list_inventory(zone: str | None = None) -> dict[str, Any]:
    items = []
    for item in inventory.values():
        if zone and item.zone != zone:
            continue
        items.append(item.model_dump(mode="json"))
    return {"items": items, "count": len(items)}


@app.post("/operations")
async def register_operation(request: WarehouseOperationRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "warehouse:update")
    item = inventory.setdefault(
        request.sku,
        WarehouseItem(sku=request.sku, description=request.sku, quantity=0, zone=request.zone, weight_kg=0),
    )
    if request.operation == WarehouseOperationType.RECEIPT:
        item.quantity += request.quantity
        item.zone = request.zone
    elif request.operation == WarehouseOperationType.SHIPMENT:
        if item.quantity < request.quantity:
            raise HTTPException(status_code=409, detail="Insufficient stock for shipment")
        item.quantity -= request.quantity
    else:
        item.zone = request.zone
    operation = WarehouseOperation(
        operation_id=str(uuid4()),
        order_id=request.order_id,
        operation=request.operation,
        sku=request.sku,
        quantity=request.quantity,
        zone=request.zone,
        actor_id=request.actor_id,
    )
    operations.append(operation)
    _audit(request.actor_id, request.actor_role, "warehouse.operation", operation.operation_id, {"sku": request.sku})
    return {"operation": operation.model_dump(mode="json"), "item": item.model_dump(mode="json")}


@app.get("/operations")
async def list_operations(order_id: str | None = None) -> dict[str, Any]:
    items = [op.model_dump(mode="json") for op in operations if not order_id or op.order_id == order_id]
    return {"items": items, "count": len(items)}


@app.get("/dashboard")
async def warehouse_dashboard() -> dict[str, Any]:
    zones: dict[str, int] = {}
    for item in inventory.values():
        zones[item.zone] = zones.get(item.zone, 0) + item.quantity
    return {
        "total_sku": len(inventory),
        "total_units": sum(item.quantity for item in inventory.values()),
        "zones": zones,
        "operations_count": len(operations),
    }


@app.get("/audit")
async def get_audit(limit: int = 100, actor_role: Role = Role.ADMIN) -> dict[str, Any]:
    _assert_permission(actor_role, "audit:read")
    return {"items": audit_log[-limit:]}

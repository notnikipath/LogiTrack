from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from shared.logitrack_common import (
    CargoType,
    CostBreakdown,
    OrderStatus,
    Role,
    Settings,
    ShipmentDocument,
    ShipmentOrder,
    ShipmentOrderCreateRequest,
    TransportMode,
    build_audit_event,
    has_permission,
)

settings = Settings(service_name="order-service", service_port=8401)
app = FastAPI(title="LogiTrack Order Service", version="1.0.0")


def _calculate_cost(
    mode: TransportMode,
    distance_km: float,
    weight_kg: float,
    cargo_type: CargoType,
    requires_customs: bool,
) -> CostBreakdown:
    rate_per_km = {
        TransportMode.ROAD: 46.0,
        TransportMode.RAIL: 31.0,
        TransportMode.SEA: 18.0,
        TransportMode.AIR: 135.0,
        TransportMode.MULTIMODAL: 58.0,
    }[mode]
    base_cost = round(distance_km * rate_per_km + weight_kg * 0.55, 2)
    fuel_surcharge = round(base_cost * (0.12 if mode in {TransportMode.ROAD, TransportMode.MULTIMODAL} else 0.06), 2)
    cold_chain_surcharge = 9500.0 if cargo_type == CargoType.REFRIGERATED else 0.0
    customs_surcharge = 17000.0 if requires_customs else 0.0
    total_cost = round(base_cost + fuel_surcharge + cold_chain_surcharge + customs_surcharge, 2)
    return CostBreakdown(
        base_cost=base_cost,
        fuel_surcharge=fuel_surcharge,
        cold_chain_surcharge=cold_chain_surcharge,
        customs_surcharge=customs_surcharge,
        total_cost=total_cost,
    )


def _seed_demo_order() -> ShipmentOrder:
    cost = _calculate_cost(
        TransportMode.ROAD,
        distance_km=1540,
        weight_kg=8200,
        cargo_type=CargoType.REFRIGERATED,
        requires_customs=False,
    )
    return ShipmentOrder(
        order_id="ORD-DEMO",
        customer_id="CUST-001",
        origin="Москва",
        destination="Казань",
        transport_mode=TransportMode.ROAD,
        cargo_type=CargoType.REFRIGERATED,
        weight_kg=8200,
        volume_m3=34,
        distance_km=1540,
        delivery_deadline=datetime.now(UTC) + timedelta(days=2),
        status=OrderStatus.CREATED,
        requires_customs=False,
        cost=cost,
        documents=[
            ShipmentDocument(
                document_id="DOC-TTN-001",
                document_type="ttn",
                url="https://cdn.logitrack.local/docs/ORD-DEMO-ttn.pdf",
            ),
            ShipmentDocument(
                document_id="DOC-INV-001",
                document_type="invoice",
                url="https://cdn.logitrack.local/docs/ORD-DEMO-invoice.pdf",
            ),
        ],
    )


orders: dict[str, ShipmentOrder] = {"ORD-DEMO": _seed_demo_order()}
audit_log: list[dict] = []


class StatusUpdateRequest(BaseModel):
    status: OrderStatus
    actor_id: str
    actor_role: Role


class DocumentCreateRequest(BaseModel):
    document_type: str
    url: str
    actor_id: str
    actor_role: Role


StatusUpdateRequest.model_rebuild()
DocumentCreateRequest.model_rebuild()


def _assert_permission(role: Role, action: str) -> None:
    if not has_permission(role, action):
        raise HTTPException(status_code=403, detail=f"Role {role.value} cannot perform {action}")


def _audit(actor_id: str, actor_role: Role, action: str, object_id: str, details: dict | None = None) -> None:
    audit_log.append(
        build_audit_event(
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            object_type="order",
            object_id=object_id,
            details=details or {},
        ).model_dump(mode="json")
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.get("/orders")
async def list_orders(status: OrderStatus | None = None) -> dict:
    items = []
    for order in orders.values():
        if status and order.status != status:
            continue
        items.append(order.model_dump(mode="json"))
    return {"items": items, "count": len(items)}


@app.get("/orders/{order_id}")
async def get_order(order_id: str, actor_role: Role = Role.DISPATCHER) -> dict:
    _assert_permission(actor_role, "order:read")
    order = orders.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order.model_dump(mode="json")


@app.post("/orders")
async def create_order(request: ShipmentOrderCreateRequest) -> dict:
    _assert_permission(request.actor_role, "order:create")
    cost = _calculate_cost(
        request.transport_mode,
        request.distance_km,
        request.weight_kg,
        request.cargo_type,
        request.requires_customs,
    )
    order = ShipmentOrder(
        order_id=str(uuid4()),
        customer_id=request.customer_id,
        origin=request.origin,
        destination=request.destination,
        transport_mode=request.transport_mode,
        cargo_type=request.cargo_type,
        weight_kg=request.weight_kg,
        volume_m3=request.volume_m3,
        distance_km=request.distance_km,
        delivery_deadline=request.delivery_deadline,
        status=OrderStatus.CREATED,
        requires_customs=request.requires_customs,
        cost=cost,
    )
    orders[order.order_id] = order
    _audit(request.actor_id, request.actor_role, "order.create", order.order_id)
    return order.model_dump(mode="json")


@app.post("/orders/{order_id}/status")
async def update_status(order_id: str, request: StatusUpdateRequest) -> dict:
    _assert_permission(request.actor_role, "order:update")
    order = orders.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    order.status = request.status
    _audit(request.actor_id, request.actor_role, "order.status.update", order_id, {"status": request.status.value})
    return order.model_dump(mode="json")


@app.post("/orders/{order_id}/documents")
async def add_document(order_id: str, request: DocumentCreateRequest) -> dict:
    _assert_permission(request.actor_role, "order:update")
    order = orders.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    document = ShipmentDocument(document_id=str(uuid4()), document_type=request.document_type, url=request.url)
    order.documents.append(document)
    _audit(request.actor_id, request.actor_role, "order.document.add", order_id, {"document_id": document.document_id})
    return document.model_dump(mode="json")


@app.get("/quotes/estimate")
async def estimate_quote(
    transport_mode: TransportMode,
    distance_km: float,
    weight_kg: float,
    cargo_type: CargoType = CargoType.GENERAL,
    requires_customs: bool = False,
) -> dict:
    return _calculate_cost(transport_mode, distance_km, weight_kg, cargo_type, requires_customs).model_dump(mode="json")


@app.get("/audit")
async def get_audit(limit: int = 100, actor_role: Role = Role.ADMIN) -> dict:
    _assert_permission(actor_role, "audit:read")
    return {"items": audit_log[-limit:]}
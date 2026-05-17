from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TransportMode(str, Enum):
    ROAD = "road"
    RAIL = "rail"
    SEA = "sea"
    AIR = "air"
    MULTIMODAL = "multimodal"


class CargoType(str, Enum):
    GENERAL = "general"
    REFRIGERATED = "refrigerated"
    HAZARDOUS = "hazardous"
    FRAGILE = "fragile"
    OVERSIZED = "oversized"


class OrderStatus(str, Enum):
    CREATED = "created"
    PLANNED = "planned"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    DELAYED = "delayed"
    CANCELLED = "cancelled"


class RouteStatus(str, Enum):
    DRAFT = "draft"
    ASSIGNED = "assigned"
    ACTIVE = "active"
    REROUTED = "rerouted"
    COMPLETED = "completed"


class WarehouseOperationType(str, Enum):
    RECEIPT = "receipt"
    SHIPMENT = "shipment"
    MOVE = "move"


class NotificationChannel(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    TELEGRAM = "telegram"
    PUSH = "push"
    WEBHOOK = "webhook"


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Role(str, Enum):
    DRIVER = "driver"
    DISPATCHER = "dispatcher"
    LOGISTICIAN = "logistician"
    WAREHOUSE = "warehouse"
    ADMIN = "admin"


class ShipmentDocument(BaseModel):
    document_id: str
    document_type: str
    url: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CostBreakdown(BaseModel):
    base_cost: float = Field(ge=0)
    fuel_surcharge: float = Field(ge=0)
    cold_chain_surcharge: float = Field(ge=0)
    customs_surcharge: float = Field(ge=0)
    total_cost: float = Field(ge=0)
    currency: str = "RUB"


class ShipmentOrderCreateRequest(BaseModel):
    customer_id: str
    origin: str
    destination: str
    transport_mode: TransportMode
    cargo_type: CargoType = CargoType.GENERAL
    weight_kg: float = Field(gt=0)
    volume_m3: float = Field(gt=0)
    distance_km: float = Field(gt=0)
    delivery_deadline: datetime
    requires_customs: bool = False
    actor_id: str
    actor_role: Role


class ShipmentOrder(BaseModel):
    order_id: str
    customer_id: str
    origin: str
    destination: str
    transport_mode: TransportMode
    cargo_type: CargoType
    weight_kg: float
    volume_m3: float
    distance_km: float
    delivery_deadline: datetime
    status: OrderStatus = OrderStatus.CREATED
    requires_customs: bool = False
    cost: CostBreakdown
    documents: list[ShipmentDocument] = Field(default_factory=list)
    assigned_vehicle_id: str | None = None
    assigned_driver_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Waypoint(BaseModel):
    waypoint_id: str
    sequence: int = Field(ge=1)
    location: str
    eta: datetime
    stop_minutes: int = Field(ge=0, default=0)


class RouteRequest(BaseModel):
    order_id: str
    traffic_index: float = Field(default=0.3, ge=0, le=1)
    weather_risk: float = Field(default=0.2, ge=0, le=1)
    actor_id: str
    actor_role: Role


class RoutePlan(BaseModel):
    route_id: str
    order_id: str
    transport_mode: TransportMode
    distance_km: float = Field(gt=0)
    estimated_duration_minutes: int = Field(gt=0)
    estimated_eta: datetime
    traffic_index: float = Field(ge=0, le=1)
    weather_risk: float = Field(ge=0, le=1)
    waypoints: list[Waypoint] = Field(default_factory=list)
    status: RouteStatus = RouteStatus.DRAFT
    optimization_score: float = Field(ge=0, le=100)
    assigned_vehicle_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RouteRerouteRequest(BaseModel):
    traffic_delay_minutes: int = Field(ge=0)
    weather_risk: float = Field(ge=0, le=1)
    actor_id: str
    actor_role: Role


class Vehicle(BaseModel):
    vehicle_id: str
    plate_number: str
    mode: TransportMode
    capacity_kg: float = Field(gt=0)
    temperature_control: bool = False
    region: str
    driver_id: str
    status: str = "available"
    current_location: str
    current_load_kg: float = Field(ge=0, default=0)


class VehicleAssignmentRequest(BaseModel):
    vehicle_id: str
    order_id: str
    route_id: str
    actor_id: str
    actor_role: Role


class TelemetryPoint(BaseModel):
    vehicle_id: str
    timestamp: datetime
    latitude: float
    longitude: float
    speed_kph: float = Field(ge=0)
    fuel_level_pct: float = Field(ge=0, le=100)
    cargo_temp_c: float | None = None
    rest_gap_hours: float = Field(ge=0, default=0)


class TelemetryBatch(BaseModel):
    points: list[TelemetryPoint] = Field(default_factory=list)
    actor_role: Role


class WarehouseItem(BaseModel):
    sku: str
    description: str
    quantity: int = Field(ge=0)
    zone: str
    weight_kg: float = Field(ge=0)
    status: str = "available"


class WarehouseOperationRequest(BaseModel):
    order_id: str
    operation: WarehouseOperationType
    sku: str
    quantity: int = Field(gt=0)
    zone: str
    actor_id: str
    actor_role: Role


class WarehouseOperation(BaseModel):
    operation_id: str
    order_id: str
    operation: WarehouseOperationType
    sku: str
    quantity: int
    zone: str
    actor_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class IntegrationSyncRequest(BaseModel):
    system_name: str
    payload: dict[str, Any] = Field(default_factory=dict)
    actor_id: str
    actor_role: Role


class IntegrationSyncResult(BaseModel):
    sync_id: str
    system_name: str
    status: str
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DriverAlert(BaseModel):
    alert_id: str
    vehicle_id: str
    driver_id: str
    severity: Severity
    message: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class NotificationPayload(BaseModel):
    channel: NotificationChannel
    recipient: str
    subject: str
    body: str
    severity: Severity = Severity.INFO
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AuditEvent(BaseModel):
    event_id: str
    actor_id: str
    actor_role: Role | str
    action: str
    object_type: str
    object_id: str
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AssignRouteWorkflowResult(BaseModel):
    order: dict[str, Any]
    route: dict[str, Any]
    vehicle: dict[str, Any]
    notification: dict[str, Any]
    analytics: dict[str, Any]
    assigned_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
from pathlib import Path

from fastapi.testclient import TestClient

from tests.integration.helpers import load_module

ROOT = Path(__file__).resolve().parents[2]

order_module = load_module("order_module", ROOT / "order-service" / "app" / "main.py")
route_module = load_module("route_module", ROOT / "route-service" / "app" / "main.py")
tracking_module = load_module("tracking_module", ROOT / "tracking-service" / "app" / "main.py")
warehouse_module = load_module("warehouse_module", ROOT / "warehouse-service" / "app" / "main.py")
integration_module = load_module("integration_module", ROOT / "integration-service" / "app" / "main.py")
analytics_module = load_module("analytics_module", ROOT / "analytics-service" / "app" / "main.py")
notification_module = load_module("notification_module", ROOT / "notification-service" / "app" / "main.py")

order_client = TestClient(order_module.app)
route_client = TestClient(route_module.app)
tracking_client = TestClient(tracking_module.app)
warehouse_client = TestClient(warehouse_module.app)
integration_client = TestClient(integration_module.app)
analytics_client = TestClient(analytics_module.app)
notification_client = TestClient(notification_module.app)


def test_order_route_assignment_flow() -> None:
    order_response = order_client.get("/orders/ORD-DEMO")
    assert order_response.status_code == 200
    order = order_response.json()
    assert order["origin"] == "Москва"

    route_response = route_client.post(
        "/routes/calculate",
        json={
            "order": order,
            "traffic_index": 0.28,
            "weather_risk": 0.15,
            "actor_id": "DSP-001",
            "actor_role": "dispatcher",
        },
    )
    assert route_response.status_code == 200
    route = route_response.json()
    assert route["estimated_duration_minutes"] > 0

    available = tracking_client.get(
        "/vehicles/available",
        params={"mode": order["transport_mode"], "capacity_kg": order["weight_kg"]},
    )
    assert available.status_code == 200
    vehicle = available.json()["items"][0]

    assign = tracking_client.post(
        "/vehicles/assign",
        json={
            "vehicle_id": vehicle["vehicle_id"],
            "order_id": order["order_id"],
            "route_id": route["route_id"],
            "actor_id": "DSP-001",
            "actor_role": "dispatcher",
        },
    )
    assert assign.status_code == 200

    analytics = analytics_client.post(
        "/analytics/ingest/route",
        json={
            "order_id": order["order_id"],
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
    assert analytics.status_code == 200

    notice = notification_client.post(
        "/notify/driver-route",
        json={
            "driver_id": vehicle["driver_id"],
            "route_id": route["route_id"],
            "order_id": order["order_id"],
            "eta": route["estimated_eta"],
            "actor_role": "dispatcher",
        },
    )
    assert notice.status_code == 200


def test_tracking_warehouse_and_integrations_flow() -> None:
    telemetry = tracking_client.post(
        "/telemetry/ingest",
        json={
            "points": [
                {
                    "vehicle_id": "VEH-101",
                    "timestamp": "2026-04-24T09:30:00Z",
                    "latitude": 55.91,
                    "longitude": 49.14,
                    "speed_kph": 111,
                    "fuel_level_pct": 61,
                    "cargo_temp_c": 3.8,
                    "rest_gap_hours": 5.0,
                }
            ],
            "actor_role": "driver",
        },
    )
    assert telemetry.status_code == 200
    assert telemetry.json()["violations_detected"] >= 1

    warehouse = warehouse_client.post(
        "/operations",
        json={
            "order_id": "ORD-DEMO",
            "operation": "shipment",
            "sku": "SKU-APPLE",
            "quantity": 10,
            "zone": "COLD-A1",
            "actor_id": "WH-001",
            "actor_role": "warehouse",
        },
    )
    assert warehouse.status_code == 200

    gps_sync = integration_client.post(
        "/integrations/gps/sync",
        json={
            "system_name": "gps",
            "payload": {"tracks": 9000},
            "actor_id": "LOG-001",
            "actor_role": "logistician",
        },
    )
    assert gps_sync.status_code == 200

    fleet = analytics_client.get("/analytics/fleet", params={"actor_role": "dispatcher"})
    assert fleet.status_code == 200
    assert "eta_mape" in fleet.json()
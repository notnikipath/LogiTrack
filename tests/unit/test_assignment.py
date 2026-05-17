from shared.logitrack_common import detect_driver_violations, optimize_load, predict_eta_minutes
from shared.logitrack_common.schemas import TransportMode


def test_predict_eta_minutes() -> None:
    eta = predict_eta_minutes(1200, TransportMode.ROAD, traffic_index=0.3, weather_risk=0.2, stop_count=1)
    assert eta > 0
    assert eta < 3000



def test_detect_driver_violations_flags_speed_and_rest() -> None:
    findings = detect_driver_violations([72, 95, 112], rest_gap_hours=5.2)
    codes = {item["code"] for item in findings}
    assert "overspeed" in codes
    assert "rest_violation" in codes



def test_optimize_load_respects_capacity() -> None:
    plan = optimize_load(
        [
            {"item_id": "A", "weight_kg": 1200, "priority": 8},
            {"item_id": "B", "weight_kg": 3400, "priority": 4},
            {"item_id": "C", "weight_kg": 1800, "priority": 7},
        ],
        vehicle_capacity_kg=4000,
    )
    assert plan["loaded_weight_kg"] <= 4000
    assert plan["selected_ids"]
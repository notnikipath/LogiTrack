from __future__ import annotations

from collections import Counter

from .schemas import Severity, TransportMode

MODE_SPEED = {
    TransportMode.ROAD: 62,
    TransportMode.RAIL: 78,
    TransportMode.SEA: 34,
    TransportMode.AIR: 640,
    TransportMode.MULTIMODAL: 55,
}


def predict_eta_minutes(
    distance_km: float,
    transport_mode: TransportMode,
    traffic_index: float,
    weather_risk: float,
    stop_count: int = 0,
) -> int:
    base_speed = MODE_SPEED[transport_mode]
    traffic_penalty = 1 + max(traffic_index, 0) * 0.55
    weather_penalty = 1 + max(weather_risk, 0) * 0.35
    service_time = stop_count * 18
    duration_hours = (distance_km / max(base_speed, 1)) * traffic_penalty * weather_penalty
    return max(30, round(duration_hours * 60 + service_time))


def reroute_eta_delta(current_minutes: int, traffic_delay_minutes: int, weather_risk: float) -> int:
    weather_buffer = round(traffic_delay_minutes * weather_risk * 0.35)
    return max(5, current_minutes + traffic_delay_minutes + weather_buffer)


def detect_driver_violations(speed_samples: list[float], rest_gap_hours: float) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    overspeed = [speed for speed in speed_samples if speed > 90]
    if overspeed:
        findings.append(
            {
                "severity": Severity.WARNING.value,
                "code": "overspeed",
                "message": f"Detected {len(overspeed)} overspeed samples above 90 km/h.",
            }
        )
    if speed_samples and max(speed_samples) > 110:
        findings.append(
            {
                "severity": Severity.CRITICAL.value,
                "code": "dangerous_speed",
                "message": "Critical speeding event above 110 km/h.",
            }
        )
    if rest_gap_hours > 4.5:
        findings.append(
            {
                "severity": Severity.CRITICAL.value,
                "code": "rest_violation",
                "message": "Driver exceeded recommended rest interval.",
            }
        )
    return findings


def optimize_load(
    items: list[dict[str, float]],
    vehicle_capacity_kg: float,
    current_load_kg: float = 0,
) -> dict[str, object]:
    remaining = max(vehicle_capacity_kg - current_load_kg, 0)
    selected: list[str] = []
    total_weight = 0.0
    scored = []
    for item in items:
        priority = float(item.get("priority", 1))
        weight = float(item.get("weight_kg", 0))
        density = priority / max(weight, 1)
        scored.append((density, item))
    scored.sort(reverse=True, key=lambda entry: entry[0])
    for _, item in scored:
        weight = float(item.get("weight_kg", 0))
        if weight <= remaining:
            remaining -= weight
            total_weight += weight
            selected.append(str(item.get("item_id")))
    utilization = round(total_weight / max(vehicle_capacity_kg, 1), 2)
    return {"selected_ids": selected, "loaded_weight_kg": total_weight, "utilization": utilization}


def recommend_map_cache_regions(regions: list[str]) -> list[str]:
    if not regions:
        return []
    top = Counter(regions).most_common(3)
    return [region for region, _ in top]

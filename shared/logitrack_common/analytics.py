from __future__ import annotations


def eta_mape(predicted_minutes: list[float], actual_minutes: list[float]) -> float:
    if not predicted_minutes or not actual_minutes or len(predicted_minutes) != len(actual_minutes):
        return 0.0
    errors = []
    for predicted, actual in zip(predicted_minutes, actual_minutes, strict=True):
        if actual <= 0:
            continue
        errors.append(abs((actual - predicted) / actual))
    if not errors:
        return 0.0
    return round(sum(errors) / len(errors) * 100, 2)


def route_build_seconds(cache_hit_ratio: float, complexity_score: float, in_memory_boost: bool = True) -> float:
    base = 7.2 - min(max(cache_hit_ratio, 0.0), 1.0) * 2.1
    complexity_penalty = max(complexity_score - 1.0, 0) * 0.65
    boost = 1.15 if in_memory_boost else 0.0
    return round(max(1.1, base + complexity_penalty - boost), 2)


def transport_load(load_kg: float, capacity_kg: float) -> float:
    if capacity_kg <= 0:
        return 0.0
    return round(min(max(load_kg / capacity_kg, 0.0), 1.0), 2)


def cost_per_km(total_cost: float, distance_km: float) -> float:
    if distance_km <= 0:
        return 0.0
    return round(total_cost / distance_km, 2)


def driver_kpi(on_time_ratio: float, incident_rate: float, fuel_efficiency: float) -> float:
    score = on_time_ratio * 55 + (1 - min(max(incident_rate, 0), 1)) * 25 + fuel_efficiency * 20
    return round(score, 2)


def parallel_track_plan(track_count: int, regions: int) -> dict[str, int]:
    workers = min(32, max(2, regions * 2, track_count // 180))
    batch_size = max(50, track_count // max(workers, 1)) if track_count else 50
    return {"workers": workers, "batch_size": batch_size, "track_count": track_count}
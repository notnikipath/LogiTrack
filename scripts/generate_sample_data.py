from __future__ import annotations

import json
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

TRANSPORT_MODES = ["road", "rail", "sea", "air", "multimodal"]
CARGO_TYPES = ["general", "refrigerated", "hazardous", "fragile", "oversized"]
REGIONS = ["ЦФО", "ПФО", "ЮФО", "СЗФО", "Урал", "Сибирь"]
CITIES = ["Москва", "Казань", "Екатеринбург", "Новосибирск", "Самара", "Санкт-Петербург"]


def generate_record(index: int) -> dict:
    transport_mode = random.choice(TRANSPORT_MODES)
    cargo_type = random.choice(CARGO_TYPES)
    origin = random.choice(CITIES)
    destination = random.choice([city for city in CITIES if city != origin])
    predicted_eta = random.randint(240, 2400)
    actual_eta = max(200, round(predicted_eta * random.uniform(0.92, 1.11)))
    return {
        "order_id": f"ORD-{index:05d}",
        "vehicle_id": f"VEH-{random.randint(100, 999)}",
        "driver_id": f"DRV-{random.randint(1, 250):03d}",
        "origin": origin,
        "destination": destination,
        "transport_mode": transport_mode,
        "cargo_type": cargo_type,
        "distance_km": random.randint(120, 3800),
        "weight_kg": random.randint(400, 22000),
        "predicted_eta_minutes": predicted_eta,
        "actual_eta_minutes": actual_eta,
        "cost_rub": round(random.uniform(18000, 340000), 2),
        "fuel_level_pct": round(random.uniform(18, 98), 2),
        "avg_speed_kph": round(random.uniform(42, 88), 2),
        "incident_count": random.randint(0, 3),
        "region": random.choice(REGIONS),
        "created_at": (datetime.now(UTC) - timedelta(minutes=index)).isoformat(),
    }


if __name__ == "__main__":
    random.seed(42)
    output = Path(__file__).resolve().parents[1] / "data" / "samples" / "logistics_events.json"
    payload = [generate_record(index) for index in range(1, 12001)]
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(payload)} records to {output}")
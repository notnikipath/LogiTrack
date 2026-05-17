from __future__ import annotations

import json
import urllib.request

BASE = "http://localhost:8480"


def request(method: str, path: str, payload: dict | None = None) -> dict:
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode("utf-8"))


if __name__ == "__main__":
    result = request(
        "POST",
        "/workflow/assign-route",
        {
            "order_id": "ORD-DEMO",
            "traffic_index": 0.32,
            "weather_risk": 0.18,
            "actor_id": "DSP-001",
            "actor_role": "dispatcher",
        },
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
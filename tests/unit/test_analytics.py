from shared.logitrack_common import cost_per_km, eta_mape, parallel_track_plan, route_build_seconds, transport_load


def test_eta_mape() -> None:
    assert eta_mape([100, 110], [105, 100]) > 0



def test_route_build_seconds_under_reasonable_bounds() -> None:
    value = route_build_seconds(cache_hit_ratio=0.8, complexity_score=1.0, in_memory_boost=True)
    assert 0 < value < 10



def test_parallel_track_plan_has_workers() -> None:
    plan = parallel_track_plan(5400, 8)
    assert plan["workers"] >= 2
    assert plan["batch_size"] >= 50



def test_transport_load_and_cost_per_km() -> None:
    assert transport_load(8000, 10000) == 0.8
    assert cost_per_km(50000, 1000) == 50.0
# Algorithms

## Route calculation

ETA is estimated from transport mode base speed, traffic penalty, weather risk, and service stop count. The route score decreases as traffic and weather risks rise.

## Dynamic rerouting

Reroute recalculates duration by adding direct traffic delay and a proportional weather buffer. This keeps the ETA change explainable for dispatchers.

## Driver violation detection

The tracking module marks:

- warning for overspeed samples above 90 km/h
- critical event above 110 km/h
- critical rest violation above 4.5 hours without break

## Load optimization

Cargo units are ranked by priority density so higher-priority freight gets packed first while respecting vehicle capacity.

## Analytics

- ETA quality uses MAPE across predicted and actual arrival durations
- Route build KPI estimates route calculation latency from cache hit ratio and complexity
- Driver KPI combines on-time ratio, incident rate, and fuel efficiency
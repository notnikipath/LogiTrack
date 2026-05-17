# Architecture

## Context

LogiTrack supports multimodal transportation planning with a dispatcher-centric control plane. The system covers shipment order intake, route optimization, vehicle assignment, telemetry collection, warehouse events, analytics, and notifications.

## Service map

- `api-gateway`: entry point, token issuance, service health, workflow orchestration, dispatcher dashboard aggregation
- `order-service`: shipment orders, cost breakdown, TTN and invoice metadata, order lifecycle
- `route-service`: optimal route calculation, dynamic reroute, route calendar and ETA generation
- `tracking-service`: vehicle availability, GPS telemetry ingestion, driver violation detection, assignment registry
- `warehouse-service`: inbound and outbound operations, SKU visibility, zone-based balance
- `integration-service`: GPS or GLONASS synchronization, 1C ERP export, map cache planning
- `analytics-service`: ETA MAPE, route build KPI, fleet load, cost per km, driver KPI
- `notification-service`: route notifications, delay alerts, message history
- `frontend`: logistics cockpit for dispatchers

## Infrastructure

- PostgreSQL for operational data
- TimescaleDB for telemetry workloads and future hypertables
- Redis for caching and short-lived coordination
- Redpanda as Kafka-compatible event broker
- Docker Compose for local deployment

## Key workflows

1. Order creation and pricing in `order-service`
2. Route calculation in `route-service`
3. Vehicle search and assignment in `tracking-service`
4. Notification of the driver in `notification-service`
5. Route analytics ingestion in `analytics-service`
6. Warehouse updates for shipment release in `warehouse-service`

## Scalability notes

- Route computation exposes in-memory optimization hints and cache-aware KPI estimation
- Tracking supports parallel processing planning for thousands of telemetry streams
- Analytics is separated from operational services to isolate heavy reads
- External integrations are isolated behind `integration-service`
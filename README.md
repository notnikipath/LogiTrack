# LogiTrack

LogiTrack is a microservice logistics platform for route planning, real-time vehicle tracking, warehouse coordination, order execution, and dispatch analytics.

## Modules

- `api-gateway` - orchestration, auth, unified dashboard
- `order-service` - shipment orders, cost estimation, transport documents
- `route-service` - route calculation, dynamic rerouting, route calendar
- `tracking-service` - vehicle pool, GPS telemetry, driver violation detection
- `warehouse-service` - receipts, shipments, zone-based stock control
- `integration-service` - GPS or GLONASS sync, 1C ERP export, map cache planning
- `analytics-service` - ETA accuracy, transport load, driver KPI, fleet dashboards
- `notification-service` - driver alerts, delay notifications, dispatch messaging
- `frontend` - dispatcher control tower UI

## Optional improvements implemented

- Dynamic rerouting based on traffic and weather
- ETA prediction for delivery planning
- Driver violation detection for speed and rest rules
- GPS and GLONASS integration endpoints
- Parallel track processing plan
- Dispatcher dashboard frontend

## Tech stack

- Backend: Python FastAPI microservices
- Data: PostgreSQL, TimescaleDB, Redis
- Queue: Redpanda Kafka-compatible broker
- Frontend: React + Vite
- Integration: REST, Webhooks, OpenStreetMap-compatible map provider

## Local run

```bash
cd 'your/project/folder'
docker compose up --build -d
```

## Useful URLs

- Frontend: `http://localhost:5177`
- Gateway health: `http://localhost:8480/health`
- Services health: `http://localhost:8480/services/health`
- Swagger: `http://localhost:8480/docs`

## Validation

```bash
python -m ruff check .
python -m pytest -q
docker compose config
```

## Demo workflow

```bash
python scripts/demo_pipeline.py
```

## Sample data

Generate logistics demo data:

```bash
python scripts/generate_sample_data.py
```

Result file: `data/samples/logistics_events.json`

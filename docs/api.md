# API Overview

## Gateway

- `POST /auth/token`
- `POST /auth/verify`
- `GET /services/health`
- `POST /workflow/assign-route`
- `POST /workflow/reroute`
- `GET /dashboard/{order_id}/{vehicle_id}`

## Order service

- `GET /orders`
- `GET /orders/{order_id}`
- `POST /orders`
- `POST /orders/{order_id}/status`
- `POST /orders/{order_id}/documents`
- `GET /quotes/estimate`

## Route service

- `GET /routes`
- `GET /routes/{route_id}`
- `POST /routes/calculate`
- `POST /routes/{route_id}/assign`
- `POST /routes/{route_id}/reroute`
- `GET /calendar`

## Tracking service

- `GET /vehicles`
- `GET /vehicles/available`
- `POST /vehicles/assign`
- `POST /telemetry/ingest`
- `GET /tracking/{vehicle_id}`
- `GET /violations/{vehicle_id}`
- `GET /processing/parallel-plan`

## Warehouse service

- `GET /inventory`
- `POST /operations`
- `GET /operations`
- `GET /dashboard`

## Integration service

- `POST /integrations/sync`
- `POST /integrations/gps/sync`
- `POST /integrations/glonass/sync`
- `POST /integrations/1c-erp/export`
- `GET /maps/cache/plan`
- `GET /integrations/history`

## Analytics service

- `POST /analytics/ingest/route`
- `POST /analytics/ingest/telemetry`
- `GET /analytics/order/{order_id}`
- `GET /analytics/driver/{driver_id}`
- `GET /analytics/fleet`
- `GET /analytics/kpi`
- `GET /dashboards/{role}`

## Notification service

- `POST /notify/send`
- `POST /notify/driver-route`
- `POST /notify/delay`
- `GET /notify/history`
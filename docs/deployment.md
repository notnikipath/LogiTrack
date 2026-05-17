# Deployment

## Requirements

- Docker
- Docker Compose
- Python 3.11 for local lint or tests

## Start

```bash
cd d:\Шарага\Кинжибаев\task_11
docker compose up --build -d
```

## Stop

```bash
docker compose down
```

## Validate

```bash
python -m ruff check .
python -m pytest -q
docker compose config
```

## Ports

- `8480` gateway
- `5177` frontend
- `8401-8407` backend services
- `55435` PostgreSQL
- `55436` TimescaleDB
- `6383` Redis
- `19092` Redpanda Kafka API
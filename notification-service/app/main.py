from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from shared.logitrack_common import NotificationChannel, Role, Settings, Severity, has_permission

settings = Settings(service_name="notification-service", service_port=8407)
app = FastAPI(title="LogiTrack Notification Service", version="1.0.0")

messages: list[dict[str, Any]] = []


class NotificationRequest(BaseModel):
    channel: NotificationChannel
    recipient: str
    subject: str
    body: str
    severity: Severity = Severity.INFO
    actor_role: Role


class DriverRouteNotificationRequest(BaseModel):
    driver_id: str
    route_id: str
    order_id: str
    eta: str
    actor_role: Role


class DelayNotificationRequest(BaseModel):
    recipient: str
    order_id: str
    delay_minutes: int
    actor_role: Role


NotificationRequest.model_rebuild()
DriverRouteNotificationRequest.model_rebuild()
DelayNotificationRequest.model_rebuild()


def _assert_permission(role: Role, action: str) -> None:
    if not has_permission(role, action):
        raise HTTPException(status_code=403, detail=f"Role {role.value} cannot {action}")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/notify/send")
async def send_notification(request: NotificationRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "notification:send")
    payload = request.model_dump(mode="json")
    payload["status"] = "queued"
    messages.append(payload)
    return payload


@app.post("/notify/driver-route")
async def notify_driver(request: DriverRouteNotificationRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "notification:send")
    payload = {
        "channel": NotificationChannel.PUSH.value,
        "recipient": request.driver_id,
        "subject": f"Назначен рейс {request.route_id}",
        "body": f"Заказ {request.order_id} назначен. Плановый ETA: {request.eta}",
        "severity": Severity.INFO.value,
        "status": "queued",
    }
    messages.append(payload)
    return payload


@app.post("/notify/delay")
async def notify_delay(request: DelayNotificationRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "notification:send")
    payload = {
        "channel": NotificationChannel.SMS.value,
        "recipient": request.recipient,
        "subject": f"Задержка по заказу {request.order_id}",
        "body": f"Ожидаемая задержка составляет {request.delay_minutes} минут.",
        "severity": Severity.WARNING.value,
        "status": "queued",
    }
    messages.append(payload)
    return payload


@app.get("/notify/history")
async def history() -> dict[str, Any]:
    return {"items": messages, "count": len(messages)}
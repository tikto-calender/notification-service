"""FastAPI-based Telegram notification service for TikTo.

Chuyên trách nhận yêu cầu từ Backend để:
1. Kiểm tra sức khỏe (Healthcheck)
2. Gửi tin nhắn thông báo (Telegram) cho Tasks & Events
3. Gửi thông báo thử nghiệm (Test message qua Telegram)
"""

from __future__ import annotations

import json
import os
import urllib.request
from datetime import UTC, datetime
from threading import Lock
from uuid import uuid4

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

# --- Tự động nạp file .env nếu có ---
def load_env() -> None:
    env_file = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.isfile(env_file):
        with open(env_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    if key and key not in os.environ:
                        os.environ[key] = val


load_env()

SERVICE_VERSION = "1.2.1"

NOTIFICATIONS: dict[str, dict] = {}
NOTIFICATIONS_LOCK = Lock()


def clean(value: object, maximum: int = 500) -> str:
    return value.strip()[:maximum] if isinstance(value, str) else ""


def account_status() -> dict[str, object]:
    provider = clean(os.environ.get("NOTIFICATION_PROVIDER"), 50)
    name = clean(os.environ.get("NOTIFICATION_ACCOUNT_NAME"), 120)
    # Tự động nhận diện tài khoản Telegram nếu có token
    if not provider and os.environ.get("TELEGRAM_BOT_TOKEN"):
        provider = "telegram"
        name = clean(os.environ.get("TELEGRAM_CHAT_ID"), 120) or "@channel"

    return {
        "connected": bool(provider and name),
        "provider": provider or None,
        "name": name or None,
    }


def send_telegram_message(message: str) -> bool:
    """Gửi tin nhắn qua Telegram Bot API (sử dụng urllib thuần)."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except Exception as exc:
        print(f"[notification-service] Lỗi gửi Telegram: {exc}")
        return False


def dispatch_notification(channel: str, target_type: str, message: str) -> bool:
    """Gửi thông báo tới Telegram (hoặc in Log nếu chưa cấu hình token)."""
    channel_upper = channel.upper()
    now_str = datetime.now(UTC).strftime("%H:%M - %d/%m/%Y")

    if channel_upper == "TELEGRAM":
        telegram_text = (
            f"🔔 <b>[TikTo Reminder]</b>\n"
            f"📌 <b>Loại:</b> {target_type}\n"
            f"📝 <b>Nội dung:</b> {message}\n"
            f"⏰ <b>Thời gian:</b> {now_str}"
        )
        sent = send_telegram_message(telegram_text)
        if sent:
            return True
        print(f"[notification-service] Không gửi được qua Telegram (kiểm tra token/chat_id), fallback in Log: [{target_type}] {message}")

    # Fallback kênh LOG
    print(f"[notification-service][LOG] [{target_type}] {message}")
    return True


# --- Pydantic Models cho Swagger UI ---


class NotificationCreate(BaseModel):
    message: str = Field(..., min_length=1, max_length=500, description="Nội dung cần nhắc nhở")
    scheduledAt: str = Field(..., description="Thời gian nhắc nhở (ISO format)")
    targetType: str = Field(default="TASK", description="Loại đối tượng (TASK / EVENT / SYSTEM)")
    targetId: str | None = Field(default="", description="ID của task hoặc event")
    channel: str = Field(default="TELEGRAM", description="Kênh gửi: TELEGRAM (hoặc LOG)")


class TestNotificationCreate(BaseModel):
    message: str | None = Field(default="TikTo test notification", description="Nội dung gửi thử")
    channel: str = Field(default="TELEGRAM", description="Kênh gửi thử: TELEGRAM (hoặc LOG)")


# --- Khởi tạo FastAPI App ---

app = FastAPI(
    title="TikTo Telegram Notification Service",
    description="Microservice chuyên trách gửi thông báo nhắc lịch (Tasks & Events) qua Telegram Bot.",
    version=SERVICE_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.get("/health", tags=["1. Sức khỏe hệ thống"])
def health_check() -> dict:
    """Backend gọi vào đây để kiểm tra kết nối với Notification Service."""
    return {
        "status": "ok",
        "service": "tikto-notification",
        "version": SERVICE_VERSION,
        "backend": "memory",
        "account": account_status(),
    }


@app.post("/notifications", status_code=status.HTTP_201_CREATED, tags=["2. Gửi thông báo Telegram"])
def create_notification(payload: NotificationCreate) -> dict:
    """Backend gọi vào đây để bắn thông báo Task hoặc Event sang Telegram."""
    try:
        datetime.fromisoformat(payload.scheduledAt.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid scheduledAt format: {exc}",
        ) from exc

    now = datetime.now(UTC).isoformat()
    channel = clean(payload.channel, 30) or "TELEGRAM"
    target_type = clean(payload.targetType, 30) or "TASK"
    msg = clean(payload.message, 500)

    # Gửi qua Telegram
    dispatched = dispatch_notification(channel, target_type, msg)

    notification = {
        "id": str(uuid4()),
        "targetType": target_type,
        "targetId": clean(payload.targetId, 120),
        "channel": channel,
        "message": msg,
        "scheduledAt": payload.scheduledAt,
        "status": "SENT" if dispatched else "SCHEDULED",
        "createdAt": now,
        "updatedAt": now,
    }
    if dispatched:
        notification["sentAt"] = now

    with NOTIFICATIONS_LOCK:
        NOTIFICATIONS[notification["id"]] = notification

    return {"data": notification}


@app.post("/notifications/test", status_code=status.HTTP_201_CREATED, tags=["2. Gửi thông báo Telegram"])
def send_test_notification(payload: TestNotificationCreate | None = None) -> dict:
    """Bắn ngay một tin nhắn thử nghiệm qua Telegram Bot để kiểm tra kết nối."""
    msg = clean(payload.message, 500) if payload and payload.message else "TikTo test notification"
    channel = clean(payload.channel, 30) if payload and payload.channel else "TELEGRAM"
    now = datetime.now(UTC).isoformat()

    dispatched = dispatch_notification(channel, "SYSTEM", msg)

    notification = {
        "id": str(uuid4()),
        "targetType": "SYSTEM",
        "targetId": "manual-test",
        "channel": channel,
        "message": msg,
        "scheduledAt": now,
        "status": "SENT",
        "sentAt": now,
        "createdAt": now,
        "updatedAt": now,
    }

    with NOTIFICATIONS_LOCK:
        NOTIFICATIONS[notification["id"]] = notification

    print(f"[notification-service] Đã gửi test notification (channel={channel}, id={notification['id']})")
    return {"data": notification}


@app.get("/notifications", tags=["3. Lịch sử thông báo"])
def list_notifications() -> dict:
    """Xem danh sách các thông báo đã gửi gần đây."""
    with NOTIFICATIONS_LOCK:
        notifications = sorted(
            (dict(item) for item in NOTIFICATIONS.values()),
            key=lambda item: item["createdAt"],
            reverse=True,
        )
    return {"data": notifications}


@app.delete("/notifications/{notification_id}", tags=["3. Lịch sử thông báo"])
def cancel_notification(notification_id: str) -> dict:
    """Hủy một thông báo."""
    with NOTIFICATIONS_LOCK:
        notification = NOTIFICATIONS.get(notification_id)
        if notification is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found.",
            )
        notification["status"] = "CANCELED"
        notification["updatedAt"] = datetime.now(UTC).isoformat()
        response = dict(notification)

    return {"data": response}


def run() -> None:
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)


if __name__ == "__main__":
    run()

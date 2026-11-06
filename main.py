"""Framework-free, in-memory notification service for TikTo."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
from uuid import uuid4

NOTIFICATIONS: dict[str, dict] = {}
NOTIFICATIONS_LOCK = Lock()
SERVICE_VERSION = "1.1.3"


def clean(value: object, maximum: int = 500) -> str:
    return value.strip()[:maximum] if isinstance(value, str) else ""


def account_status() -> dict[str, object]:
    provider = clean(os.environ.get("NOTIFICATION_PROVIDER"), 50)
    name = clean(os.environ.get("NOTIFICATION_ACCOUNT_NAME"), 120)
    return {
        "connected": bool(provider and name),
        "provider": provider or None,
        "name": name or None,
    }


class NotificationHandler(BaseHTTPRequestHandler):
    server_version = f"TikToNotification/{SERVICE_VERSION}"

    def _send_json(self, status: HTTPStatus, body: dict) -> None:
        encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 1_000_000:
            raise ValueError("Request body is too large.")
        if length == 0:
            return {}
        value = json.loads(self.rfile.read(length))
        if not isinstance(value, dict):
            raise ValueError("JSON body must be an object.")
        return value

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._send_json(
                HTTPStatus.OK,
                {
                    "status": "ok",
                    "service": "tikto-notification",
                    "version": SERVICE_VERSION,
                    "backend": "memory",
                    "account": account_status(),
                },
            )
            return

        if self.path == "/notifications":
            with NOTIFICATIONS_LOCK:
                notifications = sorted(
                    (dict(item) for item in NOTIFICATIONS.values()),
                    key=lambda item: item["createdAt"],
                    reverse=True,
                )
            self._send_json(HTTPStatus.OK, {"data": notifications})
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": "Route not found."})

    def do_POST(self) -> None:  # noqa: N802
        if self.path not in {"/notifications", "/notifications/test"}:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Route not found."})
            return

        try:
            body = self._read_json()
            message = clean(body.get("message"), 500)
            if self.path == "/notifications/test":
                now = datetime.now(UTC).isoformat()
                notification = {
                    "id": str(uuid4()),
                    "targetType": "SYSTEM",
                    "targetId": "manual-test",
                    "channel": "LOG",
                    "message": message or "TikTo test notification",
                    "scheduledAt": now,
                    "status": "SENT",
                    "sentAt": now,
                    "createdAt": now,
                    "updatedAt": now,
                }
                with NOTIFICATIONS_LOCK:
                    NOTIFICATIONS[notification["id"]] = notification
                print(f"[notification-service] sent test notification id={notification['id']}")
                self._send_json(HTTPStatus.CREATED, {"data": notification})
                return

            scheduled_at = clean(body.get("scheduledAt"), 40)
            if not message or not scheduled_at:
                raise ValueError("message and scheduledAt are required.")
            datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))

            now = datetime.now(UTC).isoformat()
            notification = {
                "id": str(uuid4()),
                "targetType": clean(body.get("targetType"), 30) or "TASK",
                "targetId": clean(body.get("targetId"), 120),
                "channel": clean(body.get("channel"), 30) or "LOG",
                "message": message,
                "scheduledAt": scheduled_at,
                "status": "SCHEDULED",
                "createdAt": now,
                "updatedAt": now,
            }
            with NOTIFICATIONS_LOCK:
                NOTIFICATIONS[notification["id"]] = notification
            self._send_json(HTTPStatus.CREATED, {"data": notification})
        except (ValueError, json.JSONDecodeError) as error:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})

    def do_DELETE(self) -> None:  # noqa: N802
        prefix = "/notifications/"
        if not self.path.startswith(prefix):
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Route not found."})
            return

        with NOTIFICATIONS_LOCK:
            notification = NOTIFICATIONS.get(self.path.removeprefix(prefix))
            if notification is not None:
                notification["status"] = "CANCELED"
                notification["updatedAt"] = datetime.now(UTC).isoformat()
                response = dict(notification)
            else:
                response = None

        if response is None:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Notification not found."})
            return
        self._send_json(HTTPStatus.OK, {"data": response})

    def log_message(self, message_format: str, *args: object) -> None:
        print(f"[notification-service] {message_format % args}")


def run() -> None:
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), NotificationHandler)
    print(f"TikTo notification service running at http://localhost:{port} (memory)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    run()

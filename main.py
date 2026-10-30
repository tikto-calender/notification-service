"""Minimal standalone notification service for TikTo."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from uuid import uuid4


NOTIFICATIONS: dict[str, dict] = {}


class NotificationHandler(BaseHTTPRequestHandler):
    server_version = "TikToNotification/1.0"

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
            self._send_json(HTTPStatus.OK, {"status": "ok", "service": "tikto-notification"})
            return
        if self.path == "/notifications":
            self._send_json(HTTPStatus.OK, {"data": list(NOTIFICATIONS.values())})
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "Route not found."})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/notifications":
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Route not found."})
            return

        try:
            body = self._read_json()
            message = str(body.get("message", "")).strip()
            scheduled_at = str(body.get("scheduledAt", "")).strip()
            if not message or not scheduled_at:
                raise ValueError("message and scheduledAt are required.")

            notification_id = str(uuid4())
            notification = {
                "id": notification_id,
                "targetType": str(body.get("targetType", "TASK")),
                "targetId": str(body.get("targetId", "")),
                "channel": str(body.get("channel", "LOG")),
                "message": message,
                "scheduledAt": scheduled_at,
                "status": "SCHEDULED",
                "createdAt": datetime.now(UTC).isoformat(),
            }
            NOTIFICATIONS[notification_id] = notification
            self._send_json(HTTPStatus.CREATED, {"data": notification})
        except (ValueError, json.JSONDecodeError) as error:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})

    def do_DELETE(self) -> None:  # noqa: N802
        prefix = "/notifications/"
        if not self.path.startswith(prefix):
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Route not found."})
            return
        notification = NOTIFICATIONS.get(self.path.removeprefix(prefix))
        if notification is None:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Notification not found."})
            return
        notification["status"] = "CANCELED"
        self._send_json(HTTPStatus.OK, {"data": notification})

    def log_message(self, message_format: str, *args: object) -> None:
        print(f"[notification-service] {message_format % args}")


def run() -> None:
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), NotificationHandler)
    print(f"TikTo notification service running at http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    run()

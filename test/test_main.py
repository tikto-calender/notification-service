import json
import os
import threading
import unittest
import urllib.error
import urllib.request

import main


class NotificationServiceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = main.ThreadingHTTPServer(("127.0.0.1", 0), main.NotificationHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def setUp(self) -> None:
        with main.NOTIFICATIONS_LOCK:
            main.NOTIFICATIONS.clear()
        os.environ.pop("NOTIFICATION_PROVIDER", None)
        os.environ.pop("NOTIFICATION_ACCOUNT_NAME", None)

    def request(self, path: str, method: str = "GET", body: dict | None = None) -> tuple[int, dict]:
        encoded = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=encoded,
            method=method,
            headers={"Content-Type": "application/json"} if encoded else {},
        )
        try:
            response = urllib.request.urlopen(request, timeout=2)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return response.status, json.load(response)

    def test_health_reports_source_version_and_disconnected_account(self) -> None:
        status, body = self.request("/health")

        self.assertEqual(status, 200)
        self.assertEqual(body["version"], main.SERVICE_VERSION)
        self.assertEqual(
            body["account"],
            {"connected": False, "provider": None, "name": None},
        )

    def test_health_reports_configured_account_without_exposing_secrets(self) -> None:
        os.environ["NOTIFICATION_PROVIDER"] = "telegram"
        os.environ["NOTIFICATION_ACCOUNT_NAME"] = "@tikto_bot"
        os.environ["TELEGRAM_BOT_TOKEN"] = "must-not-leak"

        _, body = self.request("/health")

        self.assertEqual(
            body["account"],
            {"connected": True, "provider": "telegram", "name": "@tikto_bot"},
        )
        self.assertNotIn("must-not-leak", json.dumps(body))

    def test_notification_can_be_created_and_canceled(self) -> None:
        status, created = self.request(
            "/notifications",
            method="POST",
            body={
                "message": "Upcoming task",
                "scheduledAt": "2026-11-03T10:00:00Z",
                "channel": "LOG",
            },
        )

        self.assertEqual(status, 201)
        notification = created["data"]
        self.assertEqual(notification["status"], "SCHEDULED")

        status, canceled = self.request(
            f"/notifications/{notification['id']}",
            method="DELETE",
        )
        self.assertEqual(status, 200)
        self.assertEqual(canceled["data"]["status"], "CANCELED")

    def test_notification_test_is_sent_immediately_and_stored(self) -> None:
        status, created = self.request(
            "/notifications/test",
            method="POST",
            body={},
        )

        self.assertEqual(status, 201)
        notification = created["data"]
        self.assertEqual(notification["targetType"], "SYSTEM")
        self.assertEqual(notification["targetId"], "manual-test")
        self.assertEqual(notification["channel"], "LOG")
        self.assertEqual(notification["message"], "TikTo test notification")
        self.assertEqual(notification["status"], "SENT")
        self.assertEqual(notification["scheduledAt"], notification["sentAt"])

        status, listed = self.request("/notifications")

        self.assertEqual(status, 200)
        self.assertEqual(len(listed["data"]), 1)
        self.assertEqual(listed["data"][0]["id"], notification["id"])


if __name__ == "__main__":
    unittest.main()

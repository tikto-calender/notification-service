import json
import os
import unittest
from fastapi.testclient import TestClient

import main


class NotificationServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(main.app)
        with main.NOTIFICATIONS_LOCK:
            main.NOTIFICATIONS.clear()
        os.environ.pop("NOTIFICATION_PROVIDER", None)
        os.environ.pop("NOTIFICATION_ACCOUNT_NAME", None)
        os.environ.pop("DEFAULT_NOTIFICATION_CHANNEL", None)
        os.environ.pop("TELEGRAM_BOT_TOKEN", None)
        os.environ.pop("TELEGRAM_CHAT_ID", None)

    def test_health_reports_source_version_and_disconnected_account(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["version"], main.SERVICE_VERSION)
        self.assertEqual(
            body["account"],
            {"connected": False, "provider": None, "name": None},
        )

    def test_health_reports_configured_account_without_exposing_secrets(self) -> None:
        os.environ["NOTIFICATION_PROVIDER"] = "telegram"
        os.environ["NOTIFICATION_ACCOUNT_NAME"] = "@tikto_bot"
        os.environ["TELEGRAM_BOT_TOKEN"] = "must-not-leak"

        response = self.client.get("/health")
        body = response.json()
        self.assertEqual(
            body["account"],
            {"connected": True, "provider": "telegram", "name": "@tikto_bot"},
        )
        self.assertNotIn("must-not-leak", json.dumps(body))

    def test_notification_can_be_created_and_canceled(self) -> None:
        response = self.client.post(
            "/notifications",
            json={
                "message": "Upcoming task",
                "scheduledAt": "2026-11-03T10:00:00Z",
                "channel": "LOG",
            },
        )
        self.assertEqual(response.status_code, 201)
        created = response.json()
        notification = created["data"]
        self.assertEqual(notification["status"], "SCHEDULED")

        response = self.client.delete(f"/notifications/{notification['id']}")
        self.assertEqual(response.status_code, 200)
        canceled = response.json()
        self.assertEqual(canceled["data"]["status"], "CANCELED")

    def test_notification_test_is_sent_immediately_and_stored(self) -> None:
        response = self.client.post("/notifications/test", json={})
        self.assertEqual(response.status_code, 201)
        created = response.json()
        notification = created["data"]
        self.assertEqual(notification["targetType"], "SYSTEM")
        self.assertEqual(notification["targetId"], "manual-test")
        self.assertEqual(notification["channel"], "LOG")
        self.assertEqual(notification["message"], "TikTo test notification")
        self.assertEqual(notification["status"], "SENT")
        self.assertEqual(notification["scheduledAt"], notification["sentAt"])

        response = self.client.get("/notifications")
        self.assertEqual(response.status_code, 200)
        listed = response.json()
        self.assertEqual(len(listed["data"]), 1)
        self.assertEqual(listed["data"][0]["id"], notification["id"])


if __name__ == "__main__":
    unittest.main()

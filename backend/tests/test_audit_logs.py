import unittest

from fastapi.testclient import TestClient

from app.index import app
from app.database import SessionLocal
from app.models import AuditLogRecord


class AuditLogsEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        with SessionLocal() as db:
            db.query(AuditLogRecord).delete()
            db.commit()

    def test_audit_logs_endpoint_returns_empty_list_when_none_exist(self) -> None:
        response = self.client.get("/api/audit-logs")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])


if __name__ == "__main__":
    unittest.main()

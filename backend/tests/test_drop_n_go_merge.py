import os
import tempfile
import unittest

from fastapi.testclient import TestClient


db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
db_file.close()
os.environ["DATABASE_URL"] = f"sqlite:///{db_file.name}"

from app.index import app


class DropNGoMergeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_generate_qr_codes_returns_created_codes(self) -> None:
        response = self.client.post("/api/qr/generate", json={"branch_id": 1, "count": 2})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 2)
        self.assertTrue(all(code["code"] for code in payload))


if __name__ == "__main__":
    unittest.main()

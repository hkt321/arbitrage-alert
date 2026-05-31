import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.api.main import app
from app.api import main as api_main


class ApiTest(unittest.TestCase):
    def test_health(self):
        client = TestClient(app)
        response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_opportunity_cache_reuses_fresh_data(self):
        calls = []
        cache = api_main.ApiCache(ttl_seconds=60)

        first = cache.get(False, lambda: calls.append("load") or [{"code": "A"}])
        second = cache.get(False, lambda: calls.append("load") or [{"code": "B"}])
        third = cache.get(True, lambda: calls.append("load") or [{"code": "C"}])

        self.assertEqual(first["data"], [{"code": "A"}])
        self.assertFalse(first["meta"]["cached"])
        self.assertEqual(second["data"], [{"code": "A"}])
        self.assertTrue(second["meta"]["cached"])
        self.assertEqual(third["data"], [{"code": "C"}])
        self.assertFalse(third["meta"]["cached"])
        self.assertEqual(calls, ["load", "load"])


if __name__ == "__main__":
    unittest.main()

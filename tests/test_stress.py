import unittest
import asyncio
import sqlite3
import os
from fastapi.testclient import TestClient
from skill_action_sandbox.core import SandboxEngine
from skill_action_sandbox.models import ToolRequest, PolicyTier
from skill_action_sandbox.web import app

class TestStressSandbox(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_path = "test_stress_audit.db"
        cls.engine = SandboxEngine(db_path=cls.db_path)
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        try:
            if os.path.exists(cls.db_path):
                os.remove(cls.db_path)
        except Exception:
            pass

    def setUp(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM audit_log")
            conn.commit()

    def test_high_throughput_audit_logging(self):
        """Test SQLite write performance and integrity under load."""
        iterations = 50
        async def run_batch():
            tasks = []
            for i in range(iterations):
                req = ToolRequest(tool_name=f"test_{i}", arguments={"val": i})
                tasks.append(self.engine.execute(req))
            return await asyncio.gather(*tasks)

        results = asyncio.run(run_batch())
        self.assertEqual(len(results), iterations)
        
        with sqlite3.connect(self.db_path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
            self.assertEqual(count, iterations)

    def test_concurrency_lock_integrity(self):
        """Test SandboxState async lock for race conditions."""
        from skill_action_sandbox.web import state
        
        async def add_concurrent():
            await state.add_action("concurrent_task", 0.5)

        async def run_stress():
            await asyncio.gather(*[add_concurrent() for _ in range(30)])

        asyncio.run(run_stress())
        self.assertGreaterEqual(len(state.get_all()), 30)

    def test_path_traversal_security_guard(self):
        """Verify Pydantic validator blocks malicious input."""
        with self.assertRaises(ValueError):
            ToolRequest(tool_name="read", arguments={"path": "../../etc/passwd"})
        
        with self.assertRaises(ValueError):
            ToolRequest(tool_name="read", arguments={"path": "/root/secret"})

    def test_fastapi_endpoint_load(self):
        """Test API responsiveness and state persistence."""
        for i in range(10):
            response = self.client.post("/actions", json={"name": f"task_{i}", "complexity": 0.1})
            self.assertEqual(response.status_code, 200)
        
        metrics = self.client.get("/api/metrics")
        self.assertEqual(metrics.status_code, 200)
        self.assertGreaterEqual(metrics.json()["count"], 10)

    def test_policy_enforcement_logic(self):
        """Verify SandboxEngine correctly rejects unauthorized dangerous tools."""
        req = ToolRequest(
            tool_name="rm_rf_root", 
            arguments={}, 
            tier=PolicyTier.DANGEROUS_EXEC
        )
        
        result = asyncio.run(self.engine.execute(req))
        self.assertEqual(result["status"], "error")
        self.assertIn("denied", result["message"])
        
        # Verify audit log captured the failure
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT status FROM audit_log WHERE id = ?", (req.request_id,))
            row = cursor.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], "FAILED")

if __name__ == "__main__":
    unittest.main()

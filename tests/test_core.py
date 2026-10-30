import unittest
import os
import sqlite3
import asyncio
from skill_action_sandbox.models import ToolRequest, PolicyTier
from skill_action_sandbox.core import SandboxEngine

class TestSandboxCore(unittest.TestCase):
    def setUp(self):
        self.db_path = "test_sandbox.db"
        self.engine = SandboxEngine(db_path=self.db_path)

    def tearDown(self):
        self.engine = None
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except PermissionError:
                pass

    def test_tool_request_path_traversal_prevention(self):
        with self.assertRaises(ValueError):
            ToolRequest(tool_name="read", arguments={"path": "../etc/passwd"})
        with self.assertRaises(ValueError):
            ToolRequest(tool_name="read", arguments={"path": "/root/secret"})

    def test_tool_request_valid_input(self):
        req = ToolRequest(tool_name="safe_read", arguments={"file": "data.txt"})
        self.assertEqual(req.tool_name, "safe_read")
        self.assertEqual(req.arguments["file"], "data.txt")

    def test_engine_initialization(self):
        self.assertTrue(os.path.exists(self.db_path))
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_log'")
        self.assertIsNotNone(cursor.fetchone())
        conn.close()

    def test_policy_enforcement_dangerous_tier(self):
        req = ToolRequest(tool_name="rm_rf_slash", arguments={"target": "all"}, tier=PolicyTier.DANGEROUS_EXEC)
        result = asyncio.run(self.engine.execute(req))
        self.assertEqual(result["status"], "error")
        self.assertIn("denied", result["message"])

    def test_policy_enforcement_allowlist(self):
        req = ToolRequest(tool_name="safe_read", arguments={"file": "test.txt"}, tier=PolicyTier.DANGEROUS_EXEC)
        result = asyncio.run(self.engine.execute(req))
        self.assertEqual(result["status"], "success")

    def test_audit_log_persistence(self):
        req = ToolRequest(tool_name="test_tool", arguments={"key": "val"})
        asyncio.run(self.engine.execute(req))
        conn = sqlite3.connect(self.db_path)
        row = conn.execute("SELECT tool_name, status FROM audit_log WHERE id=?", (req.request_id,)).fetchone()
        conn.close()
        self.assertEqual(row[0], "test_tool")
        self.assertEqual(row[1], "SUCCESS")

    def test_audit_log_error_capture(self):
        req = ToolRequest(tool_name="bad_tool", arguments={"x": 1}, tier=PolicyTier.DANGEROUS_EXEC)
        asyncio.run(self.engine.execute(req))
        conn = sqlite3.connect(self.db_path)
        row = conn.execute("SELECT status, error FROM audit_log WHERE id=?", (req.request_id,)).fetchone()
        conn.close()
        self.assertEqual(row[0], "FAILED")
        self.assertIsNotNone(row[1])

    def test_policy_tier_enum_values(self):
        self.assertEqual(PolicyTier.READ_ONLY.value, "READ_ONLY")
        self.assertEqual(PolicyTier.DANGEROUS_EXEC.value, "DANGEROUS_EXEC")

    def test_request_id_uniqueness(self):
        req1 = ToolRequest(tool_name="t1", arguments={})
        req2 = ToolRequest(tool_name="t2", arguments={})
        self.assertNotEqual(req1.request_id, req2.request_id)

    def test_engine_execution_return_format(self):
        req = ToolRequest(tool_name="safe_read", arguments={})
        result = asyncio.run(self.engine.execute(req))
        self.assertIn("status", result)
        self.assertIn("data", result)
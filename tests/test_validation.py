import unittest
import uuid
import os
import sqlite3
import asyncio
from pydantic import ValidationError
from src.skill_action_sandbox.models import ToolRequest, PolicyTier
from src.skill_action_sandbox.core import SandboxEngine

class TestValidation(unittest.TestCase):
    """Exhaustive validation suite for SkillAction Sandbox components."""

    def setUp(self):
        self.db_path = "test_validation.db"
        self.engine = SandboxEngine(db_path=self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_valid_tool_request(self):
        req = ToolRequest(tool_name="test_tool", arguments={"key": "value"})
        self.assertEqual(req.tool_name, "test_tool")
        self.assertEqual(req.tier, PolicyTier.READ_ONLY)

    def test_path_traversal_detection(self):
        with self.assertRaises(ValidationError):
            ToolRequest(tool_name="fs_read", arguments={"path": "../etc/passwd"})

    def test_absolute_path_detection(self):
        with self.assertRaises(ValidationError):
            ToolRequest(tool_name="fs_read", arguments={"path": "/root/secret"})

    def test_policy_tier_enforcement_denied(self):
        req = ToolRequest(
            tool_name="rm_rf_root", 
            arguments={"target": "all"}, 
            tier=PolicyTier.DANGEROUS_EXEC
        )
        result = asyncio.run(self.engine.execute(req))
        self.assertEqual(result["status"], "error")
        self.assertIn("denied", result["message"])

    def test_policy_tier_enforcement_allowed(self):
        req = ToolRequest(
            tool_name="safe_read", 
            arguments={"file": "data.txt"}, 
            tier=PolicyTier.DANGEROUS_EXEC
        )
        result = asyncio.run(self.engine.execute(req))
        self.assertEqual(result["status"], "success")

    def test_audit_log_persistence(self):
        req = ToolRequest(tool_name="test_log", arguments={"a": 1})
        asyncio.run(self.engine.execute(req))
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM audit_log WHERE id = ?", (req.request_id,))
        row = cursor.fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "SUCCESS")

if __name__ == "__main__":
    unittest.main()
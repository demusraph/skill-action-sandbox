import unittest
import os
import sqlite3
import asyncio
from pydantic import ValidationError
from src.skill_action_sandbox.models import ToolRequest, PolicyTier
from src.skill_action_sandbox.core import SandboxEngine

class TestSandboxBoundaries(unittest.TestCase):
    def setUp(self):
        self.db_path = "test_sandbox.db"
        self.engine = SandboxEngine(db_path=self.db_path)

    def tearDown(self):
        # Close any potential connections by forcing garbage collection or ensuring engine is cleaned
        self.engine = None
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except PermissionError:
                pass

    def test_path_traversal_boundary_dot_dot(self):
        with self.assertRaises(ValidationError):
            ToolRequest(tool_name="read", arguments={"path": "../etc/passwd"})

    def test_path_traversal_boundary_root_prefix(self):
        with self.assertRaises(ValidationError):
            ToolRequest(tool_name="read", arguments={"path": "/root/secret"})

    def test_dangerous_tier_unauthorized_tool(self):
        request = ToolRequest(
            tool_name="rm_rf",
            arguments={"target": "all"},
            tier=PolicyTier.DANGEROUS_EXEC
        )
        result = asyncio.run(self.engine.execute(request))
        self.assertEqual(result["status"], "error")
        self.assertIn("denied", result["message"])

    def test_dangerous_tier_authorized_tool(self):
        request = ToolRequest(
            tool_name="safe_read",
            arguments={"file": "data.txt"},
            tier=PolicyTier.DANGEROUS_EXEC
        )
        result = asyncio.run(self.engine.execute(request))
        self.assertEqual(result["status"], "success")

    def test_empty_arguments_boundary(self):
        request = ToolRequest(tool_name="ping", arguments={})
        result = asyncio.run(self.engine.execute(request))
        self.assertEqual(result["status"], "success")

    def test_identical_request_id_collision(self):
        req1 = ToolRequest(tool_name="test", arguments={})
        req2 = ToolRequest(tool_name="test", arguments={})
        self.assertNotEqual(req1.request_id, req2.request_id)

    def test_database_persistence_boundary(self):
        request = ToolRequest(tool_name="test_log", arguments={"key": "val"})
        asyncio.run(self.engine.execute(request))
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT tool_name FROM audit_log WHERE id = ?", (request.request_id,))
            row = cursor.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], "test_log")

    def test_large_payload_handling(self):
        large_args = {f"key_{i}": "x" * 100 for i in range(10)}
        request = ToolRequest(tool_name="bulk", arguments=large_args)
        result = asyncio.run(self.engine.execute(request))
        self.assertEqual(result["status"], "success")

    def test_invalid_tier_assignment(self):
        with self.assertRaises(ValidationError):
            ToolRequest(tool_name="test", arguments={}, tier="INVALID_TIER")

    def test_read_only_tier_enforcement(self):
        request = ToolRequest(
            tool_name="any_tool_name",
            arguments={},
            tier=PolicyTier.READ_ONLY
        )
        result = asyncio.run(self.engine.execute(request))
        self.assertEqual(result["status"], "success")

if __name__ == "__main__":
    unittest.main()
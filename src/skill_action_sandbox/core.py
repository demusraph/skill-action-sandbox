import sqlite3
import json
import logging
import datetime
from typing import Dict, Any, Optional
from .models import ToolRequest, AuditEntry, PolicyTier

class SandboxEngine:
    def __init__(self, db_path: str = "sandbox_audit.db"):
        self.db_path = db_path
        self._init_db()
        self.logger = logging.getLogger("SandboxEngine")

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id TEXT PRIMARY KEY,
                    timestamp DATETIME,
                    tool_name TEXT,
                    status TEXT,
                    payload TEXT,
                    error TEXT
                )
            """)
            conn.execute("PRAGMA journal_mode=WAL")
        finally:
            conn.close()

    async def execute(self, request: ToolRequest) -> Dict[str, Any]:
        """Executes a tool request with policy enforcement."""
        try:
            self._enforce_policy(request)
            result = {"status": "success", "simulated": True, "data": f"Executed {request.tool_name}"}
            self._log_audit(request, "SUCCESS")
            return result
        except Exception as e:
            self._log_audit(request, "FAILED", str(e))
            return {"status": "error", "message": str(e)}

    def _enforce_policy(self, request: ToolRequest):
        if request.tier == PolicyTier.DANGEROUS_EXEC:
            if request.tool_name not in ["safe_read", "safe_list"]:
                raise PermissionError(f"Tier {request.tier} denied for {request.tool_name}")

    def _log_audit(self, request: ToolRequest, status: str, error: Optional[str] = None):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "INSERT INTO audit_log VALUES (?, ?, ?, ?, ?, ?)",
                (
                    request.request_id,
                    str(datetime.datetime.utcnow()),
                    request.tool_name,
                    status,
                    json.dumps(request.arguments),
                    error
                )
            )
            conn.commit()
        finally:
            conn.close()
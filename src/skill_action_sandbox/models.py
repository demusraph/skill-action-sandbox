from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, validator
import uuid
import datetime
import os

class PolicyTier(str, Enum):
    READ_ONLY = "READ_ONLY"
    STAGED_WRITE = "STAGED_WRITE"
    DANGEROUS_EXEC = "DANGEROUS_EXEC"

class ToolRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    tier: PolicyTier = PolicyTier.READ_ONLY
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    @validator("arguments")
    def sanitize_paths(cls, v):
        for key, value in v.items():
            if isinstance(value, str) and (".." in value or value.startswith("/")):
                raise ValueError(f"Security Violation: Path traversal attempt detected in {key}")
        return v

class AuditEntry(BaseModel):
    id: str
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    tool_name: str
    status: str
    payload: Dict[str, Any]
    error: Optional[str] = None
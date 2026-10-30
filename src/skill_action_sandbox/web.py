import asyncio
import time
import uuid
from dataclasses import dataclass
from typing import List, Dict, Any
from fastapi import FastAPI, Body
from pydantic import BaseModel

app = FastAPI(title="SkillAction Sandbox")

@dataclass
class SkillAction:
    id: str
    name: str
    complexity: float
    status: str
    created_at: float

class ActionInput(BaseModel):
    name: str
    complexity: float

class SandboxState:
    def __init__(self):
        self.actions: Dict[str, SkillAction] = {}
        self.lock = asyncio.Lock()

    async def add_action(self, name: str, complexity: float) -> SkillAction:
        async with self.lock:
            action = SkillAction(
                id=str(uuid.uuid4())[:8],
                name=name,
                complexity=complexity,
                status="pending",
                created_at=time.time()
            )
            self.actions[action.id] = action
            return action

    def get_all(self) -> List[SkillAction]:
        return list(self.actions.values())

state = SandboxState()

@app.post("/actions")
async def create_action(data: ActionInput = Body(...)):
    action = await state.add_action(data.name, data.complexity)
    return {"id": action.id, "status": "created"}

@app.get("/api/metrics")
async def get_metrics():
    return {"count": len(state.get_all())}
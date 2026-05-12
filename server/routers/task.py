"""Task module router for FastAPI server."""

from typing import Any

from fastapi import APIRouter, HTTPException

from feishu_kit.core.client import FeishuClient
from feishu_kit.modules.task import TaskService
from server.base import BaseModule


# ── Router factory ──────────────────────────────────────────

def _handle(exc: Exception):
    """Unified error handler."""
    raise HTTPException(status_code=502, detail=str(exc))


def create_task_router(service: TaskService) -> APIRouter:
    router = APIRouter()

    @router.get("/tasks")
    async def list_tasks(page_size: int = 20):
        try:
            return await service.list_tasks(page_size)
        except Exception as e:
            _handle(e)

    @router.get("/tasks/{task_id}")
    async def get_task(task_id: str):
        try:
            return await service.get_task(task_id)
        except Exception as e:
            _handle(e)

    @router.post("/tasks")
    async def create_task(body: dict[str, Any]):
        try:
            return await service.create_task(body)
        except Exception as e:
            _handle(e)

    @router.patch("/tasks/{task_id}")
    async def update_task(task_id: str, body: dict[str, Any]):
        try:
            return await service.update_task(task_id, body)
        except Exception as e:
            _handle(e)

    @router.delete("/tasks/{task_id}")
    async def delete_task(task_id: str):
        try:
            return await service.delete_task(task_id)
        except Exception as e:
            _handle(e)

    @router.post("/tasks/{task_id}/complete")
    async def complete_task(task_id: str):
        try:
            return await service.complete_task(task_id)
        except Exception as e:
            _handle(e)

    @router.post("/tasks/{task_id}/members")
    async def add_members(task_id: str, body: dict[str, Any]):
        try:
            return await service.add_members(
                task_id, body["members"],
                user_id_type=body.get("user_id_type", "open_id"),
            )
        except Exception as e:
            _handle(e)

    # ── Comments ──────────────────────────────────────────────────

    @router.get("/tasks/{task_id}/comments")
    async def list_comments(task_id: str):
        try:
            return await service.list_comments(task_id)
        except Exception as e:
            _handle(e)

    @router.post("/tasks/{task_id}/comments")
    async def add_comment(task_id: str, body: dict[str, Any]):
        try:
            return await service.add_comment(task_id, body["content"])
        except Exception as e:
            _handle(e)

    return router


# ── Module class ────────────────────────────────────────────

class TaskModule(BaseModule):
    @property
    def name(self) -> str:
        return "task"

    def register(self, client: FeishuClient) -> APIRouter:
        self.service = TaskService(client)
        return create_task_router(self.service)

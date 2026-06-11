"""Migrate module router for FastAPI server."""

from fastapi import APIRouter, HTTPException
from feishu_kit.core.client import FeishuClient
from feishu_kit.modules.wiki import WikiService
from feishu_kit.modules.migrate.service import MigrateService
from pydantic import BaseModel
from server.base import BaseModule


class CopyBody(BaseModel):
    source_node_token: str
    target_space_id: str
    target_parent_token: str
    recursive: bool = False


def _handle(exc: Exception):
    raise HTTPException(status_code=502, detail=str(exc))


def create_migrate_router(service: MigrateService) -> APIRouter:
    router = APIRouter()

    @router.get("/capabilities")
    async def get_capabilities():
        try:
            return await service.get_capabilities()
        except Exception as e:
            _handle(e)

    @router.post("/copy")
    async def copy_node(body: CopyBody):
        try:
            result = await service.copy_node(
                body.source_node_token,
                body.target_space_id,
                body.target_parent_token,
            )
            return {"code": 0, "data": result}
        except Exception as e:
            _handle(e)

    @router.post("/copy-tree")
    async def copy_tree(body: CopyBody):
        try:
            result = await service.copy_tree(
                body.source_node_token,
                body.target_space_id,
                body.target_parent_token,
            )
            return {"code": 0, "data": result}
        except Exception as e:
            _handle(e)

    @router.post("/tasks")
    async def start_copy_task(body: CopyBody):
        try:
            task_id = await service.start_copy_task(
                body.source_node_token,
                body.target_space_id,
                body.target_parent_token,
                recursive=body.recursive,
            )
            return {"code": 0, "data": {"task_id": task_id}}
        except Exception as e:
            _handle(e)

    @router.get("/tasks")
    async def list_tasks():
        return {"code": 0, "data": {"tasks": service.list_tasks()}}

    @router.get("/tasks/{task_id}")
    async def get_task(task_id: str):
        task = service.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return {"code": 0, "data": task}

    return router


class MigrateModule(BaseModule):
    @property
    def name(self) -> str:
        return "migrate"

    def register(self, client: FeishuClient) -> APIRouter:
        self.wiki_service = WikiService(client)
        self.migrate_service = MigrateService(self.wiki_service, client)
        return create_migrate_router(self.migrate_service)

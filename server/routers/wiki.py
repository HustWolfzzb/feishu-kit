"""Wiki module router for FastAPI server."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from feishu_kit.core.client import FeishuClient
from feishu_kit.modules.wiki import WikiService
from server.base import BaseModule


# ── Request models ──────────────────────────────────────────

class RenameBody(BaseModel):
    title: str

class MoveBody(BaseModel):
    target_parent_token: str

class CreateBlockBody(BaseModel):
    children: list[dict[str, Any]]
    index: int = -1


# ── Router factory ──────────────────────────────────────────

def _handle(exc: Exception):
    """Unified error handler."""
    raise HTTPException(status_code=502, detail=str(exc))


def create_wiki_router(service: WikiService) -> APIRouter:
    router = APIRouter()

    # Spaces
    @router.get("/spaces")
    async def list_spaces(page_size: int = 20, page_token: str | None = None):
        try:
            return await service.list_spaces(page_size, page_token)
        except Exception as e:
            _handle(e)

    @router.get("/spaces/{space_id}")
    async def get_space(space_id: str):
        try:
            return await service.get_space(space_id)
        except Exception as e:
            _handle(e)

    # Nodes
    @router.get("/spaces/{space_id}/nodes")
    async def list_nodes(
        space_id: str,
        page_size: int = 50,
        page_token: str | None = None,
        parent_node_token: str | None = None,
    ):
        try:
            return await service.list_nodes(space_id, page_size, page_token, parent_node_token)
        except Exception as e:
            _handle(e)

    @router.get("/spaces/{space_id}/nodes/tree")
    async def get_node_tree(space_id: str, max_depth: int = 2):
        try:
            tree = await service.get_node_tree(space_id, max_depth)
            return {"code": 0, "data": {"items": tree}}
        except Exception as e:
            _handle(e)

    @router.get("/nodes/{token}")
    async def get_node(token: str):
        try:
            return await service.get_node(token)
        except Exception as e:
            _handle(e)

    # Members
    @router.get("/spaces/{space_id}/members")
    async def list_members(space_id: str, page_size: int = 20):
        try:
            return await service.list_members(space_id, page_size)
        except Exception as e:
            _handle(e)

    # Document content
    @router.get("/docs/{obj_token}/content")
    async def get_doc_content(obj_token: str):
        try:
            return await service.get_doc_raw_content(obj_token)
        except Exception as e:
            _handle(e)

    @router.get("/docs/{obj_token}/blocks")
    async def get_doc_blocks(obj_token: str, page_size: int = 50, page_token: str | None = None):
        try:
            return await service.get_doc_blocks(obj_token, page_size, page_token)
        except Exception as e:
            _handle(e)

    @router.get("/docs/{obj_token}/blocks/{block_id}")
    async def get_block(obj_token: str, block_id: str):
        try:
            return await service.get_block(obj_token, block_id)
        except Exception as e:
            _handle(e)

    # Document permissions
    @router.get("/docs/{obj_token}/permissions")
    async def get_doc_permissions(obj_token: str, obj_type: str = "docx"):
        try:
            return await service.get_doc_members(obj_token, obj_type)
        except Exception as e:
            _handle(e)

    @router.post("/docs/{obj_token}/permissions")
    async def add_doc_permission(obj_token: str, body: dict[str, Any]):
        try:
            return await service.add_doc_member(
                obj_token, body["member_type"], body["member_id"],
                body["perm"], body.get("obj_type", "docx"),
            )
        except Exception as e:
            _handle(e)

    # Node write operations
    @router.post("/spaces/{space_id}/nodes")
    async def create_node(space_id: str, body: dict[str, Any]):
        try:
            return await service.create_node(
                space_id, body.get("obj_type", "docx"),
                body.get("title", "未命名文档"), body.get("parent_node_token"),
            )
        except Exception as e:
            _handle(e)

    @router.post("/spaces/{space_id}/nodes/{node_token}/rename")
    async def rename_node(space_id: str, node_token: str, body: RenameBody):
        try:
            return await service.rename_node(space_id, node_token, body.title)
        except Exception as e:
            _handle(e)

    @router.post("/spaces/{space_id}/nodes/{node_token}/move")
    async def move_node(space_id: str, node_token: str, body: MoveBody):
        try:
            return await service.move_node(space_id, node_token, body.target_parent_token)
        except Exception as e:
            _handle(e)

    @router.post("/spaces/{space_id}/nodes/move_docs_to_wiki")
    async def move_docs_to_wiki(space_id: str, body: dict[str, Any]):
        try:
            return await service.move_docs_to_wiki(
                space_id, body["parent_wiki_token"],
                body["obj_token"], body.get("obj_type", "doc"),
            )
        except Exception as e:
            _handle(e)

    @router.delete("/spaces/{space_id}/nodes/{node_token}")
    async def delete_node(space_id: str, node_token: str):
        try:
            return await service.delete_node(space_id, node_token)
        except Exception as e:
            _handle(e)

    # Document write operations
    @router.post("/docs")
    async def create_doc(body: dict[str, Any]):
        try:
            return await service.create_doc(body.get("title", "未命名文档"))
        except Exception as e:
            _handle(e)

    @router.post("/docs/{obj_token}/blocks/{block_id}/children")
    async def create_doc_block(obj_token: str, block_id: str, body: CreateBlockBody):
        try:
            return await service.create_doc_block(obj_token, block_id, body.children, body.index)
        except Exception as e:
            _handle(e)

    # Space member operations
    @router.post("/spaces/{space_id}/members")
    async def add_space_member(space_id: str, body: dict[str, Any]):
        try:
            return await service.add_space_member(
                space_id, body["member_type"], body["member_id"],
                body.get("member_role", "member"),
            )
        except Exception as e:
            _handle(e)

    @router.put("/spaces/{space_id}/members")
    async def update_space_member(space_id: str, body: dict[str, Any]):
        try:
            return await service.update_space_member(
                space_id, body["member_type"], body["member_id"], body["member_role"],
            )
        except Exception as e:
            _handle(e)

    @router.delete("/spaces/{space_id}/members/{member_id}")
    async def delete_space_member(space_id: str, member_id: str, body: dict[str, Any]):
        try:
            return await service.delete_space_member(
                space_id, body["member_type"], member_id, body.get("member_role", "member"),
            )
        except Exception as e:
            _handle(e)

    # RAG / Search
    @router.get("/spaces/{space_id}/content")
    async def get_space_full_content(space_id: str, max_nodes: int = 100):
        try:
            items = await service.get_space_full_content(space_id, max_nodes)
            return {"code": 0, "data": {"items": items, "total": len(items)}}
        except Exception as e:
            _handle(e)

    @router.get("/nodes/{node_token}/detail")
    async def get_node_with_content(node_token: str):
        try:
            result = await service.get_node_with_content(node_token)
            return {"code": 0, "data": result}
        except Exception as e:
            _handle(e)

    @router.get("/spaces/{space_id}/search")
    async def search_nodes(space_id: str, keyword: str):
        try:
            matches = await service.search_nodes(space_id, keyword)
            return {"code": 0, "data": {"items": matches, "total": len(matches)}}
        except Exception as e:
            _handle(e)

    # Block-level operations
    @router.delete("/docs/{obj_token}/blocks/{block_id}")
    async def delete_block(obj_token: str, block_id: str, body: dict[str, Any] | None = None):
        try:
            b = body or {}
            return await service.delete_block(
                obj_token, block_id, b.get("start_index", 0), b.get("end_index", 0),
            )
        except Exception as e:
            _handle(e)

    @router.patch("/docs/{obj_token}/blocks/{block_id}")
    async def update_block(obj_token: str, block_id: str, body: dict[str, Any]):
        try:
            return await service.update_block(obj_token, block_id, body)
        except Exception as e:
            _handle(e)

    return router


# ── Module class ────────────────────────────────────────────

class WikiModule(BaseModule):
    @property
    def name(self) -> str:
        return "wiki"

    def register(self, client: FeishuClient) -> APIRouter:
        self.service = WikiService(client)
        return create_wiki_router(self.service)

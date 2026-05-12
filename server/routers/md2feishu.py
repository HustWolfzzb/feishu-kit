"""MD-to-Feishu module router for FastAPI server."""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from feishu_kit.core.client import FeishuClient
from feishu_kit.modules.md2feishu import Md2FeishuService
from server.base import BaseModule


# ── Request models ──────────────────────────────────────────

class PushBody(BaseModel):
    """JSON push request body."""
    markdown: str
    title: str
    space_id: str = "7419131084779126787"
    parent_node_token: str | None = None


class PreviewBody(BaseModel):
    """Preview request body."""
    markdown: str


# ── Router factory ──────────────────────────────────────────

def _handle(exc: Exception):
    """Unified error handler."""
    raise HTTPException(status_code=502, detail=str(exc))


def create_md2feishu_router(service: Md2FeishuService) -> APIRouter:
    router = APIRouter()

    @router.post("/push")
    async def push_markdown(body: PushBody):
        """Push Markdown text to create a formatted document in Feishu Wiki."""
        try:
            return await service.push_markdown(
                markdown=body.markdown,
                title=body.title,
                space_id=body.space_id,
                parent_node_token=body.parent_node_token,
            )
        except Exception as e:
            _handle(e)

    @router.post("/push/file")
    async def push_markdown_file(
        file: UploadFile = File(...),
        title: str = Form(""),
        space_id: str = Form("7419131084779126787"),
        parent_node_token: str = Form(None),
    ):
        """Upload an MD file to create a formatted document in Feishu Wiki."""
        try:
            content = (await file.read()).decode("utf-8")
            doc_title = title or file.filename or "Untitled"
            return await service.push_markdown(
                markdown=content,
                title=doc_title,
                space_id=space_id,
                parent_node_token=parent_node_token if parent_node_token else None,
            )
        except Exception as e:
            _handle(e)

    @router.post("/preview")
    async def preview_blocks(body: PreviewBody):
        """Preview MD parsed into Feishu blocks (without pushing)."""
        try:
            blocks = await service.preview(body.markdown)
            return {"code": 0, "data": {"blocks": blocks, "count": len(blocks)}}
        except Exception as e:
            _handle(e)

    return router


# ── Module class ────────────────────────────────────────────

class Md2FeishuModule(BaseModule):
    @property
    def name(self) -> str:
        return "md2feishu"

    def register(self, client: FeishuClient) -> APIRouter:
        self.service = Md2FeishuService(client)
        return create_md2feishu_router(self.service)

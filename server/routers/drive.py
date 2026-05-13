"""Drive module router for FastAPI server."""

from typing import Any

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from feishu_kit.core.client import FeishuClient
from feishu_kit.modules.drive import DriveService
from pydantic import BaseModel
from server.base import BaseModule

# ── Request models ──────────────────────────────────────────


class CreateFolderBody(BaseModel):
    folder_token: str
    name: str


class AddMemberBody(BaseModel):
    token: str
    obj_type: str = "docx"
    member_type: str
    member_id: str
    perm: str = "view"


# ── Router factory ──────────────────────────────────────────


def _handle(exc: Exception):
    """Unified error handler."""
    raise HTTPException(status_code=502, detail=str(exc))


def create_drive_router(service: DriveService) -> APIRouter:
    router = APIRouter()

    @router.get("/root")
    async def get_root():
        try:
            return await service.get_root_folder()
        except Exception as e:
            _handle(e)

    @router.get("/files")
    async def list_files(folder_token: str = "", page_size: int = 20, order_by: str = "EditedTime"):
        try:
            return await service.list_files(folder_token, page_size, order_by)
        except Exception as e:
            _handle(e)

    @router.get("/files/{file_token}")
    async def get_file(file_token: str, file_type: str = "file"):
        try:
            return await service.get_file(file_token, file_type)
        except Exception as e:
            _handle(e)

    @router.post("/folders")
    async def create_folder(body: CreateFolderBody):
        try:
            return await service.create_folder(body.folder_token, body.name)
        except Exception as e:
            _handle(e)

    @router.delete("/files/{file_token}")
    async def delete_file(file_token: str, file_type: str = "file"):
        try:
            return await service.delete_file(file_token, file_type)
        except Exception as e:
            _handle(e)

    # ── File permissions ──────────────────────────────────────────

    @router.post("/permissions")
    async def list_permissions(body: dict[str, Any]):
        try:
            return await service.list_file_members(body["token"], body.get("type", "docx"))
        except Exception as e:
            _handle(e)

    @router.post("/permissions/add")
    async def add_permission(body: AddMemberBody):
        try:
            return await service.add_file_member(
                body.token,
                body.obj_type,
                body.member_type,
                body.member_id,
                body.perm,
            )
        except Exception as e:
            _handle(e)

    @router.get("/files/{file_token}/download")
    async def download_file(file_token: str, file_type: str = "file"):
        try:
            return await service.download(file_token, file_type)
        except Exception as e:
            _handle(e)

    # ── File upload ───────────────────────────────────────────────

    @router.post("/files/upload")
    async def upload_file(
        folder_token: str = Query(..., description="Target folder token"),
        file: UploadFile = File(..., description="File binary (max 20MB)"),
    ):
        """Upload a local file to Feishu Drive."""
        try:
            data = await file.read()
            if len(data) > 20 * 1024 * 1024:
                raise HTTPException(status_code=400, detail="File exceeds 20MB limit")
            result = await service.upload_file(
                folder_token,
                file.filename,
                data,
            )
            if result.get("code") != 0:
                raise HTTPException(status_code=502, detail=str(result))
            return result
        except HTTPException:
            raise
        except Exception as e:
            _handle(e)

    return router


# ── Module class ────────────────────────────────────────────


class DriveModule(BaseModule):
    @property
    def name(self) -> str:
        return "drive"

    def register(self, client: FeishuClient) -> APIRouter:
        self.service = DriveService(client)
        return create_drive_router(self.service)

"""Contacts module router for FastAPI server."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from feishu_kit.core.client import FeishuClient
from feishu_kit.modules.contacts import ContactsService
from server.base import BaseModule


# ── Request models ──────────────────────────────────────────

class BatchUserIdBody(BaseModel):
    mobiles: list[str] | None = None
    emails: list[str] | None = None


# ── Router factory ──────────────────────────────────────────

def _handle(exc: Exception):
    """Unified error handler."""
    raise HTTPException(status_code=502, detail=str(exc))


def create_contacts_router(service: ContactsService) -> APIRouter:
    router = APIRouter()

    # ── Users ─────────────────────────────────────────────────────

    @router.get("/users/{user_id}")
    async def get_user(user_id: str, user_id_type: str = "open_id"):
        try:
            return await service.get_user(user_id, user_id_type)
        except Exception as e:
            _handle(e)

    @router.get("/users")
    async def list_users(
        department_id: str = "0",
        department_id_type: str = "open_department_id",
        user_id_type: str = "open_id",
        page_size: int = 50,
        page_token: str | None = None,
    ):
        try:
            return await service.list_users(
                department_id, department_id_type, user_id_type, page_size, page_token
            )
        except Exception as e:
            _handle(e)

    @router.post("/users/batch_get_id")
    async def batch_get_user_id(body: BatchUserIdBody):
        try:
            return await service.batch_get_user_id(body.mobiles, body.emails)
        except Exception as e:
            _handle(e)

    # ── Departments ───────────────────────────────────────────────

    @router.get("/departments/{department_id}")
    async def get_department(
        department_id: str,
        department_id_type: str = "open_department_id",
    ):
        try:
            return await service.get_department(department_id, department_id_type)
        except Exception as e:
            _handle(e)

    @router.get("/departments/{department_id}/children")
    async def get_sub_departments(
        department_id: str,
        page_size: int = 20,
        department_id_type: str = "open_department_id",
    ):
        try:
            return await service.get_department_sub_departments(
                department_id, page_size, department_id_type
            )
        except Exception as e:
            _handle(e)

    @router.get("/departments/{department_id}/users")
    async def get_department_users(
        department_id: str,
        user_id_type: str = "open_id",
        department_id_type: str = "open_department_id",
        page_size: int = 50,
    ):
        try:
            return await service.list_users(
                department_id, department_id_type, user_id_type, page_size
            )
        except Exception as e:
            _handle(e)

    # ── Groups ────────────────────────────────────────────────────

    @router.get("/groups/{group_id}/members")
    async def list_group_members(group_id: str, page_size: int = 20):
        try:
            return await service.list_group_members(group_id, page_size)
        except Exception as e:
            _handle(e)

    # ── Roles ─────────────────────────────────────────────────────

    @router.get("/roles")
    async def list_roles():
        try:
            return await service.list_roles()
        except Exception as e:
            _handle(e)

    return router


# ── Module class ────────────────────────────────────────────

class ContactsModule(BaseModule):
    @property
    def name(self) -> str:
        return "contacts"

    def register(self, client: FeishuClient) -> APIRouter:
        self.service = ContactsService(client)
        return create_contacts_router(self.service)

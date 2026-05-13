"""Calendar module router for FastAPI server."""

from typing import Any

from fastapi import APIRouter, HTTPException
from feishu_kit.core.client import FeishuClient
from feishu_kit.modules.calendar import CalendarService
from server.base import BaseModule

# ── Router factory ──────────────────────────────────────────


def _handle(exc: Exception):
    """Unified error handler."""
    raise HTTPException(status_code=502, detail=str(exc))


def create_calendar_router(service: CalendarService) -> APIRouter:
    router = APIRouter()

    @router.get("/calendars")
    async def list_calendars(page_size: int = 20, page_token: str | None = None):
        try:
            return await service.list_calendars(page_size, page_token)
        except Exception as e:
            _handle(e)

    @router.get("/primary")
    async def get_primary():
        try:
            return await service.get_primary()
        except Exception as e:
            _handle(e)

    @router.get("/calendars/{calendar_id}")
    async def get_calendar(calendar_id: str):
        try:
            return await service.get_calendar(calendar_id)
        except Exception as e:
            _handle(e)

    # ── Events ────────────────────────────────────────────────────

    @router.get("/calendars/{calendar_id}/events")
    async def list_events(
        calendar_id: str,
        start_time: str = "",
        end_time: str = "",
        page_size: int = 20,
        page_token: str | None = None,
    ):
        try:
            return await service.list_events(
                calendar_id, start_time, end_time, page_size, page_token
            )
        except Exception as e:
            _handle(e)

    @router.post("/calendars/{calendar_id}/events")
    async def create_event(calendar_id: str, body: dict[str, Any]):
        try:
            return await service.create_event(calendar_id, body)
        except Exception as e:
            _handle(e)

    @router.get("/calendars/{calendar_id}/events/{event_id}")
    async def get_event(calendar_id: str, event_id: str):
        try:
            return await service.get_event(calendar_id, event_id)
        except Exception as e:
            _handle(e)

    @router.patch("/calendars/{calendar_id}/events/{event_id}")
    async def update_event(calendar_id: str, event_id: str, body: dict[str, Any]):
        try:
            return await service.update_event(calendar_id, event_id, body)
        except Exception as e:
            _handle(e)

    @router.delete("/calendars/{calendar_id}/events/{event_id}")
    async def delete_event(calendar_id: str, event_id: str):
        try:
            return await service.delete_event(calendar_id, event_id)
        except Exception as e:
            _handle(e)

    # ── Free/busy ─────────────────────────────────────────────────

    @router.post("/freebusy")
    async def freebusy(body: dict[str, Any]):
        try:
            return await service.freebusy(
                body.get("user_id", ""),
                body["start_time"],
                body["end_time"],
            )
        except Exception as e:
            _handle(e)

    return router


# ── Module class ────────────────────────────────────────────


class CalendarModule(BaseModule):
    @property
    def name(self) -> str:
        return "calendar"

    def register(self, client: FeishuClient) -> APIRouter:
        self.service = CalendarService(client)
        return create_calendar_router(self.service)

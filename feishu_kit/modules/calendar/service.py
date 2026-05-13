"""日历服务 — 封装飞书 Calendar API"""

from pydantic import BaseModel


class EventCreate(BaseModel):
    """创建日程请求体（自动转换时间格式）。"""

    summary: str = ""
    description: str = ""
    start_time: str  # ISO 格式 "2026-04-21T10:00:00+08:00" 或 Unix 秒
    end_time: str
    location: str | None = None


def _to_timestamp(val) -> dict:
    """将各种时间格式转为飞书要求的 {"timestamp": "xxx"} 格式。

    接受:
      - dict: {"timestamp": "1776736800"} — 原样返回
      - int/str 数字: "1776736800" → {"timestamp": "..."}
      - ISO 字符串: "2026-04-21T10:00:00+08:00" → {"timestamp": "..."}
    """
    if isinstance(val, dict):
        return val
    s = str(val)
    if s.isdigit():
        return {"timestamp": s}
    # ISO 8601 → Unix timestamp
    from datetime import datetime

    dt = datetime.fromisoformat(s)
    return {"timestamp": str(int(dt.timestamp()))}


class CalendarService:
    def __init__(self, client):
        self._client = client

    # ── 日历 ────────────────────────────────────────────────────────
    async def list_calendars(self, page_size: int = 50, page_token: str | None = None) -> dict:
        params: dict = {"page_size": str(max(page_size, 50))}
        if page_token:
            params["page_token"] = page_token
        return await self._client.request("GET", "/calendar/v4/calendars", params=params)

    async def get_primary(self) -> dict:
        return await self._client.request("GET", "/calendar/v4/calendars/primary")

    async def get_calendar(self, calendar_id: str) -> dict:
        return await self._client.request("GET", f"/calendar/v4/calendars/{calendar_id}")

    # ── 日程 ────────────────────────────────────────────────────────
    async def list_events(
        self,
        calendar_id: str,
        start_time: str = "",
        end_time: str = "",
        page_size: int = 20,
        page_token: str | None = None,
    ) -> dict:
        params: dict = {"page_size": str(page_size)}
        if start_time:
            ts = _to_timestamp(start_time)
            params["start_time"] = ts["timestamp"]
        if end_time:
            ts = _to_timestamp(end_time)
            params["end_time"] = ts["timestamp"]
        if page_token:
            params["page_token"] = page_token
        return await self._client.request(
            "GET",
            f"/calendar/v4/calendars/{calendar_id}/events",
            params=params,
        )

    async def create_event(self, calendar_id: str, event: dict) -> dict:
        # 飞书要求 start_time/end_time 为 Unix 秒字符串
        body = dict(event)
        if "start_time" in body:
            body["start_time"] = _to_timestamp(str(body["start_time"]))
        if "end_time" in body:
            body["end_time"] = _to_timestamp(str(body["end_time"]))
        return await self._client.request(
            "POST",
            f"/calendar/v4/calendars/{calendar_id}/events",
            json=body,
        )

    async def get_event(self, calendar_id: str, event_id: str) -> dict:
        return await self._client.request(
            "GET",
            f"/calendar/v4/calendars/{calendar_id}/events/{event_id}",
        )

    async def update_event(self, calendar_id: str, event_id: str, event: dict) -> dict:
        body = dict(event)
        if "start_time" in body:
            body["start_time"] = _to_timestamp(str(body["start_time"]))
        if "end_time" in body:
            body["end_time"] = _to_timestamp(str(body["end_time"]))
        return await self._client.request(
            "PATCH",
            f"/calendar/v4/calendars/{calendar_id}/events/{event_id}",
            json=body,
        )

    async def delete_event(self, calendar_id: str, event_id: str) -> dict:
        return await self._client.request(
            "DELETE",
            f"/calendar/v4/calendars/{calendar_id}/events/{event_id}",
        )

    # ── 忙闲查询 ──────────────────────────────────────────────────
    async def freebusy(self, user_id: str, start_time: str, end_time: str) -> dict:
        return await self._client.request(
            "POST",
            "/calendar/v4/freebusy/list",
            json={
                "user_id": user_id,
                "start_time": _to_timestamp(start_time),
                "end_time": _to_timestamp(end_time),
            },
        )

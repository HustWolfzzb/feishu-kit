"""Butler 路由 — 状态查看、调试、和测试端点"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from feishu_kit.modules.butler.store import Store

logger = logging.getLogger(__name__)


def create_router(store: Store, engine=None) -> APIRouter:
    router = APIRouter()

    @router.get("/status")
    async def butler_status():
        return {
            "status": "ok",
            "pending_reminders": len(store.get_pending_reminders()),
            "audit_entries": len(store.get_audit_log(1000)),
        }

    @router.get("/goals/{chat_id}")
    async def get_goal(chat_id: str):
        goal = store.get_active_goal(chat_id)
        if not goal:
            return {"status": "no_active_goal", "chat_id": chat_id}
        return goal

    @router.get("/plan/{goal_id}")
    async def get_plan(goal_id: int):
        plan = store.get_plan_for_goal(goal_id)
        if not plan:
            return {"status": "no_plan", "goal_id": goal_id}
        return plan

    @router.get("/reminders")
    async def list_reminders():
        pending = store.get_pending_reminders()
        upcoming = store.get_upcoming_reminders(within_seconds=86400)
        return {
            "pending": pending,
            "upcoming_24h": upcoming,
        }

    @router.get("/approvals/{chat_id}")
    async def get_approval(chat_id: str):
        approval = store.get_pending_approval(chat_id)
        if not approval:
            return {"status": "no_pending_approval", "chat_id": chat_id}
        return approval

    @router.get("/audit")
    async def get_audit_log(limit: int = 100):
        return {"entries": store.get_audit_log(limit)}

    @router.get("/history/{chat_id}")
    async def get_history(chat_id: str, limit: int = 50):
        return {"chat_id": chat_id, "messages": store.get_conversation_history(chat_id, limit)}

    @router.post("/test/process")
    async def test_process(body: dict):
        """Test endpoint: process a message through the engine without Feishu."""
        if not engine:
            raise HTTPException(501, "Engine not available")
        chat_id = body.get("chat_id", "test_chat")
        open_id = body.get("open_id", "test_user")
        message_id = body.get("message_id", "test_msg")
        user_text = body.get("text", "")
        if not user_text:
            raise HTTPException(400, "text is required")
        reply = await engine.process_message(chat_id, open_id, message_id, user_text)
        return {"reply": reply}

    return router

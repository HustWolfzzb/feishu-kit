"""Messaging module router for FastAPI server."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from feishu_kit.core.client import FeishuClient
from feishu_kit.modules.messaging import MessagingService
from server.base import BaseModule


# ── Request models ──────────────────────────────────────────

class SendMessageBody(BaseModel):
    receive_id: str
    msg_type: str = "text"
    content: str = '{"text":"hello"}'
    receive_id_type: str = "chat_id"


class ReplyMessageBody(BaseModel):
    msg_type: str = "text"
    content: str


class UpdateMessageBody(BaseModel):
    content: str


class CreateChatBody(BaseModel):
    name: str = ""
    description: str = ""
    chat_mode: str = "group"
    chat_type: str = "public"
    user_id_list: list[str] | None = None


class UpdateChatBody(BaseModel):
    name: str | None = None
    description: str | None = None


class MemberIdListBody(BaseModel):
    id_list: list[str]
    id_type: str = "open_id"


# ── Router factory ──────────────────────────────────────────

def _handle(exc: Exception):
    """Unified error handler."""
    raise HTTPException(status_code=502, detail=str(exc))


def create_messaging_router(service: MessagingService) -> APIRouter:
    router = APIRouter()

    # ── Message sending ───────────────────────────────────────────

    @router.get("/test")
    async def test_connection():
        try:
            result = await service.list_chats(page_size=1)
            return {
                "status": "ok",
                "message": "Feishu API connection successful",
                "code": result.get("code"),
            }
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Connection failed: {e}")

    @router.post("/messages")
    async def send_message(body: SendMessageBody):
        try:
            return await service.send_message(
                body.receive_id, body.msg_type, body.content, body.receive_id_type
            )
        except Exception as e:
            _handle(e)

    @router.post("/messages/{message_id}/reply")
    async def reply_message(message_id: str, body: ReplyMessageBody):
        try:
            return await service.reply_message(message_id, body.msg_type, body.content)
        except Exception as e:
            _handle(e)

    @router.get("/messages/{message_id}")
    async def get_message(message_id: str):
        try:
            return await service.get_message(message_id)
        except Exception as e:
            _handle(e)

    @router.delete("/messages/{message_id}")
    async def delete_message(message_id: str):
        try:
            return await service.delete_message(message_id)
        except Exception as e:
            _handle(e)

    @router.patch("/messages/{message_id}")
    async def update_message(message_id: str, body: UpdateMessageBody):
        try:
            return await service.update_message(message_id, body.content)
        except Exception as e:
            _handle(e)

    @router.get("/messages")
    async def list_messages(
        container_id: str, container_id_type: str = "chat", page_size: int = 20,
        page_token: str | None = None,
    ):
        try:
            return await service.list_messages(
                container_id, container_id_type, page_size, page_token
            )
        except Exception as e:
            _handle(e)

    # ── Message reactions ─────────────────────────────────────────

    @router.post("/messages/{message_id}/reactions")
    async def add_reaction(message_id: str, body: dict[str, Any]):
        try:
            return await service.add_reaction(
                message_id, body.get("reaction_type", ""), body.get("emoji", "")
            )
        except Exception as e:
            _handle(e)

    @router.get("/messages/{message_id}/reactions")
    async def list_reactions(message_id: str, page_size: int = 20):
        try:
            return await service.list_reactions(message_id, page_size)
        except Exception as e:
            _handle(e)

    @router.delete("/messages/{message_id}/reactions/{reaction_id}")
    async def delete_reaction(message_id: str, reaction_id: str):
        try:
            return await service.delete_reaction(message_id, reaction_id)
        except Exception as e:
            _handle(e)

    # ── Chat management ───────────────────────────────────────────

    @router.get("/chats")
    async def list_chats(page_size: int = 20, page_token: str | None = None):
        try:
            return await service.list_chats(page_size, page_token)
        except Exception as e:
            _handle(e)

    @router.get("/chats/{chat_id}")
    async def get_chat(chat_id: str):
        try:
            return await service.get_chat_info(chat_id)
        except Exception as e:
            _handle(e)

    @router.post("/chats")
    async def create_chat(body: CreateChatBody):
        try:
            return await service.create_chat(
                body.name, body.description, body.chat_mode,
                body.chat_type, body.user_id_list,
            )
        except Exception as e:
            _handle(e)

    @router.put("/chats/{chat_id}")
    async def update_chat(chat_id: str, body: UpdateChatBody):
        try:
            return await service.update_chat(
                chat_id, name=body.name, description=body.description,
            )
        except Exception as e:
            _handle(e)

    @router.delete("/chats/{chat_id}")
    async def disband_chat(chat_id: str):
        try:
            return await service.disband_chat(chat_id)
        except Exception as e:
            _handle(e)

    # ── Chat members ──────────────────────────────────────────────

    @router.get("/chats/{chat_id}/members")
    async def list_chat_members(
        chat_id: str, member_id_type: str = "open_id", page_size: int = 50,
    ):
        try:
            return await service.list_chat_members(chat_id, member_id_type, page_size)
        except Exception as e:
            _handle(e)

    @router.post("/chats/{chat_id}/members")
    async def add_chat_members(chat_id: str, body: MemberIdListBody):
        try:
            return await service.add_chat_members(chat_id, body.id_list, body.id_type)
        except Exception as e:
            _handle(e)

    @router.delete("/chats/{chat_id}/members")
    async def remove_chat_members(chat_id: str, body: MemberIdListBody):
        try:
            return await service.remove_chat_members(chat_id, body.id_list, body.id_type)
        except Exception as e:
            _handle(e)

    # ── Chat admins ───────────────────────────────────────────────

    @router.post("/chats/{chat_id}/managers")
    async def set_chat_admin(chat_id: str, body: dict[str, Any]):
        try:
            return await service.set_chat_admin(chat_id, body.get("user_id_list", []))
        except Exception as e:
            _handle(e)

    @router.delete("/chats/{chat_id}/managers")
    async def remove_chat_admin(chat_id: str, body: dict[str, Any]):
        try:
            return await service.remove_chat_admin(chat_id, body.get("user_id_list", []))
        except Exception as e:
            _handle(e)

    # ── Pinned messages ───────────────────────────────────────────

    @router.post("/chats/{chat_id}/pins")
    async def pin_message(chat_id: str, body: dict[str, Any]):
        try:
            return await service.pin_message(chat_id, body["message_id"])
        except Exception as e:
            _handle(e)

    @router.delete("/chats/{chat_id}/pins")
    async def unpin_message(chat_id: str, body: dict[str, Any]):
        try:
            return await service.unpin_message(chat_id, body["message_id"])
        except Exception as e:
            _handle(e)

    @router.get("/chats/{chat_id}/pins")
    async def list_pins(chat_id: str):
        try:
            return await service.list_pins(chat_id)
        except Exception as e:
            _handle(e)

    return router


# ── Module class ────────────────────────────────────────────

class MessagingModule(BaseModule):
    @property
    def name(self) -> str:
        return "messaging"

    def register(self, client: FeishuClient) -> APIRouter:
        self.service = MessagingService(client)
        return create_messaging_router(self.service)

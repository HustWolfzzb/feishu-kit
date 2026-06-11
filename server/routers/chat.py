"""Chat module router for FastAPI server."""

from fastapi import APIRouter
from feishu_kit.core.client import FeishuClient
from feishu_kit.modules.chat.service import ChatService
from feishu_kit.modules.chat.router import create_router
from server.base import BaseModule


class ChatModule(BaseModule):
    @property
    def name(self) -> str:
        return "chat"

    def register(self, client: FeishuClient) -> APIRouter:
        self.service = ChatService(client)
        return create_router(self.service)

    async def on_startup(self) -> None:
        """Start WebSocket long-connection (background thread).

        If butler module is loaded, skip WS (butler handles messages).
        """
        import sys
        butler_active = "feishu_kit.modules.butler" in sys.modules
        if butler_active:
            return
        self.service.start_ws()

    async def on_shutdown(self) -> None:
        """Close WebSocket and LLM client."""
        await self.service.close()

"""Chat 模块 — 飞书机器人对话服务（WebSocket 长连接 + LLM + RAG）"""

import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)

from feishu_kit.core.client import FeishuClient
from server.base import BaseModule
from feishu_kit.modules.chat.router import create_router
from feishu_kit.modules.chat.service import ChatService


class ChatModule(BaseModule):
    @property
    def name(self) -> str:
        return "chat"

    def register(self, client: FeishuClient) -> APIRouter:
        self.service = ChatService(client)
        return create_router(self.service)

    async def on_startup(self) -> None:
        """启动 WebSocket 长连接（后台线程）。

        如果 butler 模块已加载，跳过 WS 启动（butler 接管消息处理）。
        """
        # Check if butler module is active — if so, skip WS
        import sys
        butler_active = "feishu_kit.modules.butler" in sys.modules
        if butler_active:
            logger.info("Butler module active — chat WS skipped")
            return
        self.service.start_ws()

    async def on_shutdown(self) -> None:
        """关闭 WebSocket 和 LLM 客户端。"""
        await self.service.close()

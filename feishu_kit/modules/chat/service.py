"""Chat 服务 — LLM 调用 + 会话记忆 + RAG 检索 + 消息回复

支持两种事件接收方式：
1. WebSocket 长连接（默认，无需公网 IP）
2. Webhook HTTP 回调（需要公网地址）
"""

import asyncio
import json
import logging
import re
import threading

import httpx
import lark_oapi as lark

from feishu_kit.core.settings import Settings as settings
from feishu_kit.core.client import FeishuClient

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self, feishu_client: FeishuClient):
        self._client = feishu_client
        self._http: httpx.AsyncClient | None = None
        self._history: dict[str, list[dict]] = {}  # chat_id -> messages
        self._ws_client: lark.ws.Client | None = None
        self._event_loop: asyncio.AbstractEventLoop | None = None

    # ── WebSocket 启动/停止 ─────────────────────────────────────────

    def start_ws(self) -> None:
        """在后台线程中启动 WebSocket 长连接。"""

        def _run_ws():
            # 在新线程中创建新的事件循环
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            self._event_loop = new_loop

            def _message_handler(data: lark.im.v1.P2ImMessageReceiveV1) -> None:
                try:
                    msg = data.event.message
                    sender = data.event.sender
                    event_dict = {
                        "message": {
                            "message_id": msg.message_id,
                            "chat_id": msg.chat_id,
                            "chat_type": msg.chat_type,
                            "message_type": msg.message_type,
                            "content": msg.content,
                        },
                        "sender": {
                            "sender_id": {
                                "open_id": sender.sender_id.open_id,
                            },
                            "sender_type": sender.sender_type,
                        },
                    }
                    # 在 WS 线程的事件循环中调度异步处理
                    asyncio.run_coroutine_threadsafe(
                        self.handle_message_event(event_dict), new_loop
                    )
                except Exception as e:
                    logger.error("WS message handler error: %s", e, exc_info=True)

            handler = (
                lark.EventDispatcherHandler.builder("", "")
                .register_p2_im_message_receive_v1(_message_handler)
                .build()
            )

            # 修补 SDK 模块级别的 loop（它用的是 asyncio.get_event_loop()）
            import lark_oapi.ws.client as ws_mod
            ws_mod.loop = new_loop

            self._ws_client = lark.ws.Client(
                self._client._app_id,
                self._client._app_secret,
                event_handler=handler,
                log_level=lark.LogLevel.INFO,
                auto_reconnect=True,
            )

            self._ws_client.start()

        t = threading.Thread(target=_run_ws, daemon=True)
        t.start()
        logger.info("Feishu WebSocket client starting (background thread)")

    def stop_ws(self) -> None:
        """停止 WebSocket 客户端（daemon 线程会随进程退出）。"""
        self._ws_client = None

    # ── 消息处理（核心） ────────────────────────────────────────────

    async def handle_message_event(self, event: dict) -> None:
        """处理飞书 im.message.receive_v1 事件。"""
        try:
            message = event.get("message", {})
            sender = event.get("sender", {})
            message_id = message.get("message_id", "")
            chat_id = message.get("chat_id", "")
            msg_type = message.get("message_type", "")
            content_str = message.get("content", "{}")
            open_id = sender.get("sender_id", {}).get("open_id", "")

            if not message_id:
                return

            # 仅处理文本消息
            if msg_type != "text":
                await self._reply_text(
                    message_id, "暂不支持此消息类型，请发送文字消息。"
                )
                return

            # 提取用户文本
            try:
                content = json.loads(content_str)
                user_text = content.get("text", "")
            except json.JSONDecodeError:
                user_text = content_str

            # 去掉 @机器人 标签
            user_text = re.sub(r"@_user_\d+\s*", "", user_text).strip()
            if not user_text:
                return

            logger.info(
                "Chat message from %s in %s: %s",
                open_id, chat_id, user_text[:100],
            )

            # RAG 上下文
            rag_context = await self._maybe_get_rag_context(user_text)

            # 构建 LLM 消息
            messages = self._build_messages(chat_id, user_text, rag_context)

            # 调用 LLM
            reply = await self._call_llm(messages)

            # 保存历史
            self._append_history(chat_id, user_text, reply)

            # 回复用户
            await self._reply_text(message_id, reply)
            logger.info("Replied to %s in %s", open_id, chat_id)

        except Exception as e:
            logger.error("handle_message_event failed: %s", e, exc_info=True)
            try:
                msg_id = event.get("message", {}).get("message_id", "")
                if msg_id:
                    await self._reply_text(msg_id, "抱歉，处理消息时出错了，请稍后再试。")
            except Exception:
                pass

    # 兼容 webhook 模式的别名
    async def handle_webhook_event(self, event: dict) -> None:
        """Webhook 模式的事件处理入口（兼容旧接口）。"""
        await self.handle_message_event(event)

    # ── 公开接口 ────────────────────────────────────────────────────

    def get_history(self, chat_id: str) -> list[dict]:
        return self._history.get(chat_id, [])

    def clear_history(self, chat_id: str) -> None:
        self._history.pop(chat_id, None)

    async def test_llm(self) -> str:
        messages = [{"role": "user", "content": "Say 'ok' in one word."}]
        return await self._call_llm(messages)

    async def close(self) -> None:
        self.stop_ws()
        if self._http and not self._http.is_closed:
            await self._http.aclose()

    # ── LLM 调用 ────────────────────────────────────────────────────

    async def _get_http(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(
                base_url=settings.llm_base_url,
                timeout=httpx.Timeout(settings.llm_timeout, connect=10.0),
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            )
        return self._http

    async def _call_llm(self, messages: list[dict]) -> str:
        client = await self._get_http()
        resp = await client.post(
            "/chat/completions",
            headers={"Authorization": f"Bearer {settings.llm_api_key}"},
            json={
                "model": settings.llm_model,
                "messages": messages,
                "max_tokens": settings.llm_max_tokens,
                "temperature": settings.llm_temperature,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    # ── 会话记忆 ────────────────────────────────────────────────────

    def _build_messages(
        self, chat_id: str, user_text: str, rag_context: str = ""
    ) -> list[dict]:
        system_content = settings.chat_system_prompt
        if rag_context:
            system_content += f"\n\n--- 相关知识库内容 ---\n{rag_context}"

        messages = [{"role": "system", "content": system_content}]
        messages.extend(self._history.get(chat_id, []))
        messages.append({"role": "user", "content": user_text})
        return messages

    def _append_history(self, chat_id: str, user_text: str, assistant_text: str) -> None:
        history = self._history.setdefault(chat_id, [])
        history.append({"role": "user", "content": user_text})
        history.append({"role": "assistant", "content": assistant_text})
        max_entries = settings.chat_history_max_turns * 2
        if len(history) > max_entries:
            self._history[chat_id] = history[-max_entries:]

    # ── RAG ─────────────────────────────────────────────────────────

    async def _maybe_get_rag_context(self, user_text: str) -> str:
        space_id = settings.rag_wiki_space_id
        if not space_id:
            return ""

        try:
            from feishu_kit.modules.wiki.service import WikiService
            wiki = WikiService(self._client)
            matches = await wiki.search_nodes(space_id, user_text)
            if not matches:
                return ""

            context_parts = []
            max_len = settings.rag_max_context_length
            for node in matches[:3]:
                node_token = node.get("node_token", "")
                title = node.get("title", "")
                detail = await wiki.get_node_with_content(node_token)
                content = detail.get("content", "")
                chunk = content[:max_len // 3]
                if chunk:
                    context_parts.append(f"标题: {title}\n{chunk}")

            return "\n\n".join(context_parts)[:max_len]
        except Exception as e:
            logger.warning("RAG context retrieval failed: %s", e)
            return ""

    # ── 消息回复 ─────────────────────────────────────────────────────

    async def _reply_text(self, message_id: str, text: str) -> dict:
        from feishu_kit.modules.messaging.service import MessagingService
        messaging = MessagingService(self._client)
        content = json.dumps({"text": text})
        return await messaging.reply_message(message_id, "text", content)

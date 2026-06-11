"""Butler module router for FastAPI server."""

from fastapi import APIRouter
from feishu_kit.core.client import FeishuClient
from feishu_kit.core.settings import Settings as settings
from feishu_kit.modules.butler.router import create_router
from feishu_kit.modules.butler.store import Store
from feishu_kit.modules.butler.engine import ButlerEngine
from server.base import BaseModule


def _handle(exc: Exception):
    from fastapi import HTTPException
    raise HTTPException(status_code=502, detail=str(exc))


class ButlerModule(BaseModule):
    @property
    def name(self) -> str:
        return "butler"

    def register(self, client: FeishuClient) -> APIRouter:
        self.store = Store(settings.butler_db_path)
        self.store.open()
        self._client = client
        self.engine = ButlerEngine(client, self.store)
        return create_router(self.store, self.engine)

    async def on_startup(self) -> None:
        await self.engine.scheduler.start()
        self._start_ws()

    async def on_shutdown(self) -> None:
        self._stop_ws()
        await self.engine.scheduler.stop()
        self.store.close()

    def _start_ws(self) -> None:
        import asyncio, json, logging, re, threading
        import lark_oapi as lark
        from feishu_kit.modules.messaging.service import MessagingService
        logger = logging.getLogger(__name__)
        engine = self.engine

        def _run_ws():
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            self._ws_loop = new_loop

            def _message_handler(data):
                try:
                    msg = data.event.message
                    sender = data.event.sender
                    event_dict = {
                        "message": {
                            "message_id": msg.message_id, "chat_id": msg.chat_id,
                            "chat_type": msg.chat_type, "message_type": msg.message_type,
                            "content": msg.content,
                        },
                        "sender": {
                            "sender_id": {"open_id": sender.sender_id.open_id},
                            "sender_type": sender.sender_type,
                        },
                    }
                    asyncio.run_coroutine_threadsafe(self._handle(event_dict), new_loop)
                except Exception as e:
                    logger.error("WS handler error: %s", e, exc_info=True)

            handler = (
                lark.EventDispatcherHandler.builder("", "")
                .register_p2_im_message_receive_v1(_message_handler)
                .build()
            )
            import lark_oapi.ws.client as ws_mod
            ws_mod.loop = new_loop
            self._ws_client = lark.ws.Client(
                self._client._app_id, self._client._app_secret,
                event_handler=handler, log_level=lark.LogLevel.INFO, auto_reconnect=True,
            )
            self._ws_client.start()

        t = threading.Thread(target=_run_ws, daemon=True)
        t.start()

    def _stop_ws(self) -> None:
        self._ws_client = None

    async def _handle(self, event: dict) -> None:
        import json, re, logging
        from feishu_kit.modules.messaging.service import MessagingService
        logger = logging.getLogger(__name__)
        try:
            message = event.get("message", {})
            sender = event.get("sender", {})
            message_id = message.get("message_id", "")
            chat_id = message.get("chat_id", "")
            msg_type = message.get("message_type", "")
            content_str = message.get("content", "{}")
            open_id = sender.get("sender_id", {}).get("open_id", "")
            if not message_id or msg_type != "text":
                return
            try:
                content = json.loads(content_str)
                user_text = content.get("text", "")
            except json.JSONDecodeError:
                user_text = content_str
            user_text = re.sub(r"@_user_\d+\s*", "", user_text).strip()
            if not user_text:
                return
            reply = await self.engine.process_message(chat_id, open_id, message_id, user_text)
            svc = MessagingService(self._client)
            await svc.reply_message(message_id, "text", json.dumps({"text": reply}))
        except Exception as e:
            logger.error("Butler event handler failed: %s", e, exc_info=True)

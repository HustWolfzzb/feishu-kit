"""Chat 路由 — webhook 端点 + 测试/调试端点"""

import json
import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from feishu_kit.core.settings import Settings as settings

logger = logging.getLogger(__name__)


def create_router(service) -> APIRouter:
    router = APIRouter()

    @router.get("/webhook")
    @router.post("/webhook")
    async def webhook_verification(request: Request):
        """飞书 URL 验证 + 事件回调（统一入口）。"""
        try:
            body = await request.json()
        except Exception:
            return {"status": "webhook endpoint active"}

        # URL 验证（飞书首次配置时发送）
        if body.get("type") == "url_verification":
            token = body.get("token", "")
            if settings.feishu_verification_token and token != settings.feishu_verification_token:
                raise HTTPException(403, "Invalid verification token")
            return {"challenge": body.get("challenge", "")}

        # 加密事件解密
        if "encrypt" in body and settings.feishu_encrypt_key:
            from feishu_kit.modules.chat.crypto import decrypt_feishu_event
            try:
                plaintext = decrypt_feishu_event(
                    settings.feishu_encrypt_key, body["encrypt"]
                )
                body = json.loads(plaintext)
            except Exception as e:
                logger.error("Webhook decrypt failed: %s", e)
                raise HTTPException(400, "Decryption failed")

        # 事件回调
        header = body.get("header", {})
        event_type = header.get("event_type", "")

        if settings.feishu_verification_token:
            if header.get("token") != settings.feishu_verification_token:
                raise HTTPException(403, "Invalid token")

        if event_type == "im.message.receive_v1":
            event = body.get("event", {})
            # 后台处理，立即返回 200
            background_tasks = request.scope.get("background_tasks")
            if background_tasks is None:
                # 如果拿不到 BackgroundTasks，用 asyncio
                import asyncio
                asyncio.create_task(service.handle_webhook_event(event))
            else:
                background_tasks.add_task(service.handle_webhook_event, event)
            return {"code": 0}

        return {"code": 0}

    @router.post("/webhook/event")
    async def webhook_event_post(request: Request, background_tasks: BackgroundTasks):
        """备用端点：飞书 POST 事件回调。"""
        try:
            body = await request.json()
        except Exception:
            return {"code": 0}

        # URL 验证
        if body.get("type") == "url_verification":
            token = body.get("token", "")
            if settings.feishu_verification_token and token != settings.feishu_verification_token:
                raise HTTPException(403, "Invalid verification token")
            return {"challenge": body.get("challenge", "")}

        # 加密解密
        if "encrypt" in body and settings.feishu_encrypt_key:
            from feishu_kit.modules.chat.crypto import decrypt_feishu_event
            try:
                plaintext = decrypt_feishu_event(
                    settings.feishu_encrypt_key, body["encrypt"]
                )
                body = json.loads(plaintext)
            except Exception as e:
                logger.error("Webhook decrypt failed: %s", e)
                raise HTTPException(400, "Decryption failed")

        header = body.get("header", {})
        if settings.feishu_verification_token:
            if header.get("token") != settings.feishu_verification_token:
                raise HTTPException(403, "Invalid token")

        event_type = header.get("event_type", "")
        if event_type == "im.message.receive_v1":
            event = body.get("event", {})
            background_tasks.add_task(service.handle_webhook_event, event)

        return {"code": 0}

    @router.get("/test")
    async def test_llm():
        """测试 LLM 连通性。"""
        try:
            response = await service.test_llm()
            return {"status": "ok", "model": settings.llm_model, "response": response}
        except Exception as e:
            raise HTTPException(502, f"LLM connection failed: {e}")

    @router.get("/history/{chat_id}")
    async def get_history(chat_id: str):
        """查看对话历史。"""
        return {"chat_id": chat_id, "history": service.get_history(chat_id)}

    @router.delete("/history/{chat_id}")
    async def clear_history(chat_id: str):
        """清除对话历史。"""
        service.clear_history(chat_id)
        return {"status": "cleared", "chat_id": chat_id}

    return router

"""
Example 09: Bot Playground — Interactive messaging bot.

This example demonstrates how to build a conversational Feishu bot that:
  1. Receives messages via webhook
  2. Replies with text and interactive cards
  3. Handles card action callbacks

Run:
    export FEISHU_APP_ID="cli_xxx"
    export FEISHU_APP_SECRET="xxx"
    export FEISHU_VERIFICATION_TOKEN="xxx"
    export FEISHU_ENCRYPT_KEY="xxx"
    pip install "feishu-kit[server]"
    python bot.py

Then configure your Feishu app's event subscription URL to:
    http://your-server:8000/webhook
"""

import json
import os

from fastapi import FastAPI, Request
from feishu_kit import FeishuClient
from feishu_kit.modules.messaging import MessagingService

app = FastAPI(title="feishu-kit Bot Playground")
client: FeishuClient | None = None


@app.on_event("startup")
async def startup() -> None:
    global client
    client = FeishuClient(
        os.environ["FEISHU_APP_ID"],
        os.environ["FEISHU_APP_SECRET"],
    )


@app.on_event("shutdown")
async def shutdown() -> None:
    if client:
        await client.close()


# ── Challenge verification (for event subscription setup) ────


@app.post("/webhook")
async def webhook(request: Request):
    body = await request.json()

    # Handle URL verification challenge
    if body.get("type") == "url_verification":
        return {"challenge": body["challenge"]}

    # Handle events
    event = body.get("event", {})
    header = body.get("header", {})
    event_type = header.get("event_type", "")

    if event_type == "im.message.receive_v1":
        await handle_message(event)

    return {"code": 0}


async def handle_message(event: dict) -> None:
    """Handle an incoming message event."""
    msg = event.get("message", {})
    chat_id = msg.get("chat_id", "")
    msg_type = msg.get("message_type", "")
    content = msg.get("content", "{}")
    event.get("sender", {}).get("sender_id", {}).get("user_id", "")

    if not client:
        return

    messaging = MessagingService(client)

    # Parse message content
    if msg_type == "text":
        try:
            text = json.loads(content).get("text", "").strip()
        except (json.JSONDecodeError, KeyError):
            text = ""

        # Simple command handling
        if text.startswith("/hello"):
            await messaging.send_message(
                chat_id=chat_id,
                msg_type="text",
                content=json.dumps({"text": "Hello! I'm a feishu-kit bot. :wave:"}),
            )

        elif text.startswith("/card"):
            card = {
                "config": {"wide_screen_mode": True},
                "header": {
                    "title": {"tag": "plain_text", "content": "feishu-kit Card Demo"},
                    "template": "blue",
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": "This is an **interactive card** built with feishu-kit!",
                        },
                    },
                    {
                        "tag": "action",
                        "actions": [
                            {
                                "tag": "button",
                                "text": {"tag": "plain_text", "content": "Click Me"},
                                "type": "primary",
                                "value": {"action": "clicked"},
                            }
                        ],
                    },
                    {
                        "tag": "hr",
                    },
                    {
                        "tag": "note",
                        "elements": [
                            {
                                "tag": "plain_text",
                                "content": "Powered by feishu-kit",
                            }
                        ],
                    },
                ],
            }
            await messaging.send_message(
                chat_id=chat_id,
                msg_type="interactive",
                content=json.dumps(card),
            )

        elif text.startswith("/help"):
            help_text = (
                "**Available Commands:**\n"
                "- `/hello` — Say hello\n"
                "- `/card` — Show an interactive card\n"
                "- `/help` — Show this help message\n"
                "- Anything else — Echo your message"
            )
            await messaging.send_message(
                chat_id=chat_id,
                msg_type="text",
                content=json.dumps({"text": help_text}),
            )

        elif text:
            # Echo
            await messaging.send_message(
                chat_id=chat_id,
                msg_type="text",
                content=json.dumps({"text": f"You said: {text}"}),
            )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

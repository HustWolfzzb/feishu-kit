# Messaging Tutorial — Messages and Chats

This tutorial covers the `MessagingService` module for sending messages and managing chats.

## Setup

```python
from feishu_kit import FeishuClient
from feishu_kit.modules.messaging import MessagingService

client = FeishuClient(app_id="...", app_secret="...")
msg = MessagingService(client)
```

## 1. Send a Text Message

```python
result = await msg.send_message(
    receive_id_type="chat_id",
    receive_id="oc_xxx",
    msg_type="text",
    content='{"text":"Hello from feishu-kit!"}',
)
message_id = result.get("data", {}).get("message_id")
```

## 2. List Chats

```python
result = await msg.list_chats(page_size=20)
for chat in result.get("data", {}).get("items", []):
    print(f"{chat.get('name', '(DM)')} — id={chat['chat_id']}")
```

## 3. Reply to a Message

```python
await msg.reply_message(
    message_id="om_xxx",
    msg_type="text",
    content='{"text":"Got it!"}',
)
```

## 4. Send Rich Text

```python
rich_content = {
    "zh_cn": {
        "title": "Weekly Report",
        "content": [
            [{"tag": "text", "text": "Status: "}, {"tag": "text", "text": "On track", "style": ["bold"]}],
            [{"tag": "a", "text": "View details", "href": "https://example.com"}],
        ]
    }
}
await msg.send_message(
    receive_id_type="chat_id",
    receive_id="oc_xxx",
    msg_type="post",
    content=json.dumps(rich_content),
)
```

## Cleanup

```python
await client.close()
```

## Next: [Markdown to Feishu](tutorial-md2feishu.md)

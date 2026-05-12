# Getting Started

This guide walks you through setting up feishu-kit and making your first API call in under 10 minutes.

## Prerequisites

- Python 3.11+
- A Feishu account with admin access to create apps

## Step 1: Create a Feishu App

1. Go to [open.feishu.cn/app](https://open.feishu.cn/app)
2. Click **Create Custom App**
3. Note down your **App ID** and **App Secret**
4. Under **Permissions & Scopes**, enable the APIs you need:
   - `wiki:wiki` — Knowledge base read/write
   - `drive:drive` — Cloud drive access
   - `im:message` — Messaging
   - `contact:user.base:readonly` — Contacts
5. Under **Version Management**, publish the app

## Step 2: Install feishu-kit

```bash
pip install feishu-kit
```

For the optional FastAPI server:

```bash
pip install "feishu-kit[server]"
```

## Step 3: Your First Script

Save this as `hello.py`:

```python
import asyncio
from feishu_kit import FeishuClient

async def main():
    client = FeishuClient(
        app_id="your_app_id",
        app_secret="your_app_secret",
    )

    # List all knowledge spaces
    result = await client.request("GET", "/wiki/v2/spaces")
    for space in result.get("data", {}).get("items", []):
        print(f"📚 {space['name']}")

    await client.close()

asyncio.run(main())
```

Run it:

```bash
python hello.py
```

You should see a list of knowledge spaces your app has access to.

## Step 4: Use Environment Variables (Recommended)

Instead of hardcoding credentials, use environment variables:

```bash
export FEISHU_APP_ID="cli_xxx"
export FEISHU_APP_SECRET="xxx"
```

Then in your code:

```python
import os
from feishu_kit import FeishuClient

client = FeishuClient(
    app_id=os.environ["FEISHU_APP_ID"],
    app_secret=os.environ["FEISHU_APP_SECRET"],
)
```

Or use the built-in Settings helper:

```python
from feishu_kit import Settings, FeishuClient

settings = Settings()  # reads from .env or environment
client = FeishuClient(settings.feishu_app_id, settings.feishu_app_secret)
```

## Step 5: Use a Module

feishu-kit provides pre-built service classes for common Feishu APIs:

```python
from feishu_kit import FeishuClient
from feishu_kit.modules.wiki import WikiService

client = FeishuClient(app_id="...", app_secret="...")
wiki = WikiService(client)

# List all nodes in a knowledge space
nodes = await wiki.list_all_nodes("your_space_id")
for node in nodes:
    print(node["title"])

await client.close()
```

## Next Steps

- [Wiki Tutorial](tutorial-wiki.md) — Deep dive into knowledge base operations
- [Drive Tutorial](tutorial-drive.md) — File upload and management
- [Markdown to Feishu](tutorial-md2feishu.md) — Convert Markdown to Feishu documents
- [Server Tutorial](tutorial-server.md) — Build a FastAPI REST API server

# feishu-kit

A modular Python toolkit for [Feishu (Lark) Open Platform](https://open.feishu.cn/) — reusable API wrappers, independent modules, and an optional FastAPI server layer.

Designed as a **course-friendly open-source project** for students and junior developers learning to build Feishu integrations.

## Features

- **FeishuClient** — Automatic token management, connection pooling, upload support
- **ClientPool** — Multi-bot support out of the box
- **7 API modules** — Wiki, Drive, Messaging, Contacts, Calendar, Task, Markdown-to-Feishu
- **Zero FastAPI dependency** in core — use in scripts, Jupyter, CLI, any framework
- **Optional server layer** — FastAPI app factory with auto-discovery module system
- **Course-ready** — Progressive examples from "Hello Feishu" to a full AI Agent

## Quick Start

### 1. Install

```bash
pip install feishu-kit

# Or with FastAPI server support:
pip install "feishu-kit[server]"
```

### 2. Get your credentials

Create a Feishu App at [open.feishu.cn](https://open.feishu.cn/app) and note down your `App ID` and `App Secret`.

### 3. Hello Feishu

```python
import asyncio
from feishu_kit import FeishuClient

async def main():
    client = FeishuClient(app_id="cli_xxx", app_secret="xxx")
    result = await client.request("GET", "/wiki/v2/spaces")
    for space in result.get("data", {}).get("items", []):
        print(f"📚 {space['name']} (id={space['space_id']})")
    await client.close()

asyncio.run(main())
```

### 4. Use a module

```python
from feishu_kit import FeishuClient
from feishu_kit.modules.wiki import WikiService

client = FeishuClient(app_id="cli_xxx", app_secret="xxx")
wiki = WikiService(client)

# List all nodes in a space
nodes = await wiki.list_all_nodes("your_space_id")
for node in nodes:
    print(node["title"])
```

### 5. Multi-bot support

```python
from feishu_kit import ClientPool

pool = ClientPool()
pool.add("default", "cli_app1_id", "cli_app1_secret")
pool.add("bot2", "cli_app2_id", "cli_app2_secret")

wiki1 = WikiService(pool.default)
wiki2 = WikiService(pool.get("bot2"))
```

## Project Structure

```
feishu-kit/
├── feishu_kit/              # Core package (no FastAPI dependency)
│   ├── core/                # FeishuClient, ClientPool, Settings
│   └── modules/             # wiki, drive, messaging, contacts, calendar, task, md2feishu
├── server/                  # Optional FastAPI server layer
│   ├── base.py              # BaseModule abstract class
│   ├── registry.py          # Auto-discovery module registry
│   └── routers/             # Per-module FastAPI routes
├── docs/                    # Tutorials and API reference
├── examples/                # Progressive course examples
└── tests/                   # Unit tests with mock client
```

## Modules

| Module | Description | Key Methods |
|--------|-------------|-------------|
| **wiki** | Knowledge base (spaces, nodes, docs, permissions) | `list_spaces`, `create_node`, `get_doc_blocks`, `search_nodes` |
| **drive** | Cloud drive (files, folders, upload, download) | `upload_file`, `list_files`, `download`, `create_folder` |
| **messaging** | IM (messages, chats, message cards) | `send_message`, `list_chats`, `reply_message` |
| **contacts** | Directory (users, departments, groups) | `list_users`, `list_departments`, `get_user` |
| **calendar** | Calendar events | `list_events`, `create_event` |
| **task** | Task management | `list_tasks`, `create_task` |
| **md2feishu** | Markdown → Feishu document conversion | `push_markdown`, `preview` |

## Documentation

- [Getting Started](docs/getting-started.md) — Setup, credentials, first script
- [Wiki Tutorial](docs/tutorial-wiki.md) — Knowledge base operations
- [Drive Tutorial](docs/tutorial-drive.md) — File management
- [Messaging Tutorial](docs/tutorial-messaging.md) — Messages and chats
- [Markdown to Feishu](docs/tutorial-md2feishu.md) — Convert and push documents
- [Server Tutorial](docs/tutorial-server.md) — Build a FastAPI service

## License

MIT

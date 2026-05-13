# feishu-kit Documentation

<p align="center">
  <pre>
 ███████╗███████╗██╗     ██╗         ██████╗ ██╗  ██╗██╗████████╗
 ██╔════╝██╔════╝██║     ██║         ██╔══██╗██║ ██╔╝██║╚══██╔══╝
 █████╗  █████╗  ██║     ██║         ██████╔╝█████╔╝ ██║   ██║
 ██╔══╝  ██╔══╝  ██║     ██║         ██╔═══╝ ██╔═██╗ ██║   ██║
 ██║     ███████╗███████╗███████╗    ██║     ██║  ██╗██║   ██║
 ╚═╝     ╚══════╝╚══════╝╚══════╝    ╚═╝     ╚═╝  ╚═╝╚═╝   ╚═╝
  </pre>
</p>

A modular, async-first Python toolkit for the Feishu (Lark) Open Platform.

## Features

- :books: **Wiki** — Spaces, nodes, docs, permissions, RAG retrieval
- :floppy_disk: **Drive** — Upload, download, folders, permissions
- :speech_balloon: **Messaging** — Send, reply, chats, reactions, pins
- :busts_in_silhouette: **Contacts** — Users, departments, groups
- :calendar: **Calendar** — Events, calendars, free/busy query
- :white_check_mark: **Task** — Tasks, task lists, members, comments
- :memo: **md2feishu** — Markdown → Feishu DocX with one call
- :rocket: **CLI** — Rich terminal interface (`feishu-kit` command)
- :globe_with_meridians: **FastAPI server** — Optional REST API layer

## Quick Start

```bash
pip install feishu-kit
```

```python
import asyncio
from feishu_kit import FeishuClient

async def main():
    async with FeishuClient(app_id="cli_xxx", app_secret="xxx") as client:
        result = await client.request("GET", "/wiki/v2/spaces")
        for space in result.get("data", {}).get("items", []):
            print(f"📚 {space['name']}")

asyncio.run(main())
```

## Next Steps

- [Getting Started](getting-started.md) — Environment setup and first script
- [CLI Guide](cli-guide.md) — Terminal commands for common operations
- [Wiki Tutorial](tutorial-wiki.md) — Knowledge base operations
- [Course Builder](project-build-course.md) — End-to-end course creation

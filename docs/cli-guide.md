# CLI Guide

After installing feishu-kit, you get a `feishu-kit` command with rich terminal output.

## Setup

```bash
export FEISHU_APP_ID="cli_xxx"
export FEISHU_APP_SECRET="xxx"
```

## Commands

### `feishu-kit version`

Print version with ASCII banner.

```bash
feishu-kit version
```

### `feishu-kit spaces`

List all knowledge spaces in a colorful table.

```bash
feishu-kit spaces
```

### `feishu-kit nodes <space_id>`

List nodes in a space as a tree view.

```bash
feishu-kit nodes 7264xxxxxx
```

### `feishu-kit push <file.md> <space_id>`

Push a Markdown file to Feishu Wiki.

```bash
feishu-kit push README.md 7264xxxxxx --title "My Document"
```

Options:
- `--title, -t` — Document title (defaults to filename without extension)
- `--parent, -p` — Parent node token to nest under

### `feishu-kit inspect <token>`

Pretty-print document content as JSON.

```bash
feishu-kit inspect doccnxxxxxx
```

### `feishu-kit chats`

List all chats the bot belongs to.

```bash
feishu-kit chats
```

## Using as a Python Library

The CLI is built on the same modules you can use directly:

```python
from feishu_kit import FeishuClient
from feishu_kit.modules.wiki import WikiService

async with FeishuClient(app_id="...", app_secret="...") as client:
    wiki = WikiService(client)
    nodes = await wiki.list_all_nodes("space_id")
```

See the [tutorials](tutorial-wiki.md) for more.

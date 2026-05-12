# Markdown to Feishu Tutorial

This tutorial covers the `Md2FeishuService` for converting Markdown to Feishu documents and pushing them to a wiki space.

## Setup

```python
from feishu_kit import FeishuClient
from feishu_kit.modules.wiki import WikiService
from feishu_kit.modules.md2feishu import Md2FeishuService

client = FeishuClient(app_id="...", app_secret="...")
wiki = WikiService(client)
md = Md2FeishuService(wiki)  # WikiService is injected
```

## 1. Preview Conversion (No API Call)

```python
markdown = """
# My Document

This is **bold** and *italic* text.

## Features

- Bullet point 1
- Bullet point 2

```python
print("hello")
```
"""

blocks = md.preview(markdown)
print(f"Generated {len(blocks)} blocks")
# Inspect block types
for b in blocks:
    print(f"  type={b['block_type']}")
```

## Supported Markdown Elements

| Markdown | Feishu Block Type |
|----------|-------------------|
| `# H1` | heading1 (3) |
| `## H2` | heading2 (4) |
| `### H3` | heading3 (5) |
| Paragraph | text (2) |
| `- item` | bullet (12) |
| `1. item` | ordered (13) |
| `` ```code``` `` | code (14) |
| `> quote` | quote |
| `**bold**` | bold text_run |
| `*italic*` | italic text_run |
| Table | table block |

## 2. Push to Wiki

```python
result = await md.push_markdown(
    markdown,
    title="Converted Document",
    space_id="your_space_id",
    parent_node_token="parent_node",  # optional
)

print(f"URL: {result.get('url')}")
print(f"Blocks written: {result.get('blocks_written')}")
```

## 3. Batch Push Multiple Files

```python
import pathlib

docs_dir = pathlib.Path("docs/")
for md_file in sorted(docs_dir.glob("*.md")):
    content = md_file.read_text(encoding="utf-8")
    title = md_file.stem

    result = await md.push_markdown(
        content,
        title=title,
        space_id="space_id",
    )
    print(f"Pushed {title}: {result.get('blocks_written')} blocks")
```

## Cleanup

```python
await client.close()
```

## Next: [Server Tutorial](tutorial-server.md)

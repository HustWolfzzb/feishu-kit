"""Example 05: Markdown to Wiki — Convert Markdown and push to Feishu Wiki.

Usage:
    python examples/05-md-to-wiki.py

Demonstrates:
    - Convert Markdown text to Feishu DocX blocks
    - Create a wiki document and write the converted content
"""
import asyncio
import os

from feishu_kit import FeishuClient
from feishu_kit.modules.wiki import WikiService
from feishu_kit.modules.md2feishu import Md2FeishuService


MARKDOWN_CONTENT = """\
# My Markdown Document

This is a **Markdown** document converted to Feishu format.

## Features

- Support for headings
- Support for **bold** and *italic* text
- Support for bullet lists
- Support for code blocks

## Code Example

```python
from feishu_kit import FeishuClient

client = FeishuClient(app_id="xxx", app_secret="xxx")
result = await client.request("GET", "/wiki/v2/spaces")
```

## Conclusion

This document was created from Markdown using feishu-kit.
"""


async def main():
    client = FeishuClient(
        os.environ["FEISHU_APP_ID"],
        os.environ["FEISHU_APP_SECRET"],
    )

    # md2feishu needs a WikiService injected
    wiki = WikiService(client)
    md_service = Md2FeishuService(wiki)

    SPACE_ID = os.environ.get("WIKI_SPACE_ID", "")

    try:
        # Option 1: Preview blocks without pushing
        print("=== Preview (no API call) ===")
        blocks = md_service.preview(MARKDOWN_CONTENT)
        print(f"  Generated {len(blocks)} blocks\n")

        # Option 2: Push to Wiki
        print("=== Pushing to Wiki ===")
        result = await md_service.push_markdown(
            MARKDOWN_CONTENT,
            title="Markdown Demo",
            space_id=SPACE_ID,
        )
        print(f"  Created: {result.get('url', '(no url)')}")
        print(f"  Blocks written: {result.get('blocks_written', 0)}")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())

"""Example 03: Write Document — Create a document and write content blocks.

Usage:
    python examples/03-write-document.py

Demonstrates:
    - Create a new wiki document
    - Write heading, text, and bullet blocks
    - Read back the document content
"""

import asyncio
import os

from feishu_kit import FeishuClient
from feishu_kit.modules.wiki import WikiService


def text_run(content: str, bold: bool = False) -> dict:
    style = {"bold": True} if bold else {}
    return {"text_run": {"content": content, "text_element_style": style}}


async def main():
    SPACE_ID = os.environ.get("WIKI_SPACE_ID", "")

    async with FeishuClient(
        os.environ["FEISHU_APP_ID"],
        os.environ["FEISHU_APP_SECRET"],
    ) as client:
        wiki = WikiService(client)

        # 1. Create document
        result = await wiki.create_node(SPACE_ID, title="Demo Document")
        node = result.get("data", {}).get("node", {})
        obj_token = node.get("obj_token", "")
        print(f"Created document: obj_token={obj_token}")

        # 2. Write content blocks
        blocks = [
            {
                "block_type": 4,  # heading2
                "heading2": {
                    "elements": [text_run("Hello from feishu-kit!", bold=True)],
                    "style": {},
                },
            },
            {
                "block_type": 2,  # text
                "text": {
                    "elements": [
                        text_run(
                            "This document was created programmatically using the feishu-kit library."
                        )
                    ],
                    "style": {},
                },
            },
            {
                "block_type": 5,  # heading3
                "heading3": {"elements": [text_run("Key Features")], "style": {}},
            },
            {
                "block_type": 12,  # bullet
                "bullet": {"elements": [text_run("Automatic token management")], "style": {}},
            },
            {
                "block_type": 12,
                "bullet": {"elements": [text_run("Connection pooling with httpx")], "style": {}},
            },
            {
                "block_type": 12,
                "bullet": {"elements": [text_run("Modular service architecture")], "style": {}},
            },
        ]

        await wiki.create_doc_block(obj_token, obj_token, blocks)
        print(f"Wrote {len(blocks)} blocks")

        # 3. Read back content
        raw = await wiki.get_doc_raw_content(obj_token)
        content = raw.get("data", {}).get("content", "")
        print(f"\nDocument content ({len(content)} chars):")
        print(content[:500])


if __name__ == "__main__":
    asyncio.run(main())

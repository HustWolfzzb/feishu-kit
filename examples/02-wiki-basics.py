"""Example 02: Wiki Basics — CRUD operations on knowledge space nodes.

Usage:
    python examples/02-wiki-basics.py

Demonstrates:
    - List all nodes in a space
    - Create a new document node
    - Rename a node
    - Move a node
    - Get node tree with hierarchy
"""
import asyncio
import os

from feishu_kit import FeishuClient
from feishu_kit.modules.wiki import WikiService


async def main():
    client = FeishuClient(
        os.environ["FEISHU_APP_ID"],
        os.environ["FEISHU_APP_SECRET"],
    )
    wiki = WikiService(client)
    SPACE_ID = os.environ.get("WIKI_SPACE_ID", "")

    try:
        # 1. List all nodes in the space
        print("=== Listing all nodes ===")
        nodes = await wiki.list_all_nodes(SPACE_ID)
        for n in nodes[:10]:
            print(f"  {n.get('title', '(untitled)')}  node={n.get('node_token', '')}")
        print(f"  ... total {len(nodes)} nodes\n")

        # 2. Create a new document
        print("=== Creating a new node ===")
        result = await wiki.create_node(
            SPACE_ID, obj_type="docx", title="Test Document"
        )
        node_token = result.get("data", {}).get("node", {}).get("node_token", "")
        print(f"  Created node: {node_token}\n")

        # 3. Rename it
        if node_token:
            print("=== Renaming node ===")
            await wiki.rename_node(SPACE_ID, node_token, "My Test Document")
            print(f"  Renamed to: My Test Document\n")

        # 4. Get node tree
        print("=== Node tree (depth=2) ===")
        tree = await wiki.get_node_tree(SPACE_ID, max_depth=2)
        for root in tree[:5]:
            title = root.get("title", "(untitled)")
            children = root.get("children", [])
            print(f"  📁 {title}")
            for child in children[:3]:
                print(f"     └─ {child.get('title', '(untitled)')}")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())

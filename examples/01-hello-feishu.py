"""Example 01: Hello Feishu — List all knowledge spaces.

Usage:
    python examples/01-hello-feishu.py

Requires:
    export FEISHU_APP_ID="cli_xxx"
    export FEISHU_APP_SECRET="xxx"
"""

import asyncio
import os

from feishu_kit import FeishuClient


async def main():
    app_id = os.environ["FEISHU_APP_ID"]
    app_secret = os.environ["FEISHU_APP_SECRET"]

    async with FeishuClient(app_id, app_secret) as client:
        result = await client.request("GET", "/wiki/v2/spaces")
        items = result.get("data", {}).get("items", [])

        if not items:
            print("No knowledge spaces found.")
            return

        print(f"Found {len(items)} knowledge space(s):\n")
        for space in items:
            name = space.get("name", "(untitled)")
            space_id = space.get("space_id", "")
            print(f"  📚 {name}  (id={space_id})")


if __name__ == "__main__":
    asyncio.run(main())

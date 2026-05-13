"""Example 06: Multi-Bot — Use multiple Feishu bots with ClientPool.

Usage:
    python examples/06-multi-bot.py

Demonstrates:
    - Create a ClientPool with multiple bots
    - Use different bots for different operations
"""

import asyncio
import os

from feishu_kit import ClientPool
from feishu_kit.modules.wiki import WikiService


async def main():
    pool = ClientPool()

    # Register bots
    pool.add("default", os.environ["FEISHU_APP_ID"], os.environ["FEISHU_APP_SECRET"])

    # Optional second bot
    bot2_id = os.environ.get("FEISHU_BOT2_APP_ID", "")
    bot2_secret = os.environ.get("FEISHU_BOT2_APP_SECRET", "")
    if bot2_id:
        pool.add("bot2", bot2_id, bot2_secret)

    print(f"Registered bots: {pool.names}\n")

    try:
        # Use default bot
        wiki_default = WikiService(pool.default)
        result = await wiki_default.list_spaces()
        items = result.get("data", {}).get("items", [])
        print(f"Default bot sees {len(items)} spaces")

        # Use bot2 if available
        if pool.names == ["default", "bot2"]:
            wiki_bot2 = WikiService(pool.get("bot2"))
            result2 = await wiki_bot2.list_spaces()
            items2 = result2.get("data", {}).get("items", [])
            print(f"Bot2 sees {len(items2)} spaces")

    finally:
        await pool.close_all()


if __name__ == "__main__":
    asyncio.run(main())

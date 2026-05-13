"""Example 04: Upload File — Upload a file to Drive and move it into Wiki.

Usage:
    python examples/04-upload-file.py

Demonstrates:
    - Upload a file to Feishu Drive
    - Move the file from Drive into a Wiki space
"""

import asyncio
import os

from feishu_kit import FeishuClient
from feishu_kit.modules.drive import DriveService
from feishu_kit.modules.wiki import WikiService


async def main():
    SPACE_ID = os.environ.get("WIKI_SPACE_ID", "")

    async with FeishuClient(
        os.environ["FEISHU_APP_ID"],
        os.environ["FEISHU_APP_SECRET"],
    ) as client:
        drive = DriveService(client)
        wiki = WikiService(client)

        # 1. Create a test file in memory
        file_content = b"Hello from feishu-kit!\nThis is an uploaded text file."
        file_name = "hello-feishu-kit.txt"

        # 2. Upload to Drive root
        print("=== Uploading to Drive ===")
        result = await drive.upload_file("", file_name, file_content)
        file_token = result.get("data", {}).get("file_token", "")
        print(f"  Uploaded: file_token={file_token}")

        if file_token:
            # 3. Move into Wiki
            print("\n=== Moving to Wiki ===")
            move_result = await wiki.move_docs_to_wiki(
                SPACE_ID,
                parent_wiki_token="",
                obj_token=file_token,
                obj_type="file",
            )
            print(f"  Move result: code={move_result.get('code')}")
            if move_result.get("data", {}).get("wiki_token"):
                print(f"  Wiki token: {move_result['data']['wiki_token']}")


if __name__ == "__main__":
    asyncio.run(main())

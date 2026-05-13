"""
Example 08: Web Dashboard — A single-page Feishu knowledge base dashboard.

Run:
    export FEISHU_APP_ID="cli_xxx"
    export FEISHU_APP_SECRET="xxx"
    export WIKI_SPACE_ID="your_space_id"
    pip install "feishu-kit[server]"
    python app.py

Then open http://localhost:8000 in your browser.
"""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from feishu_kit import FeishuClient
from feishu_kit.modules.messaging import MessagingService
from feishu_kit.modules.wiki import WikiService

app = FastAPI(title="feishu-kit Dashboard")
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")

client: FeishuClient | None = None


@app.on_event("startup")
async def startup() -> None:
    global client
    client = FeishuClient(
        os.environ["FEISHU_APP_ID"],
        os.environ["FEISHU_APP_SECRET"],
    )


@app.on_event("shutdown")
async def shutdown() -> None:
    if client:
        await client.close()


@app.get("/", response_class=HTMLResponse)
async def index():
    return (Path(__file__).parent / "static" / "index.html").read_text()


@app.get("/api/spaces")
async def list_spaces():
    result = await client.request("GET", "/wiki/v2/spaces")
    return result.get("data", {}).get("items", [])


@app.get("/api/spaces/{space_id}/nodes")
async def list_nodes(space_id: str):
    wiki = WikiService(client)
    nodes = await wiki.list_all_nodes(space_id)
    return nodes


@app.get("/api/chats")
async def list_chats():
    msg = MessagingService(client)
    result = await msg.list_chats()
    return result.get("data", {}).get("items", [])


@app.get("/api/docs/{token}/content")
async def get_doc_content(token: str):
    wiki = WikiService(client)
    content = await wiki.get_doc_raw_content(token)
    return content


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

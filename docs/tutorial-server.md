# Server Tutorial — Build a FastAPI REST API

This tutorial shows how to use the optional `server` layer to create a REST API that wraps feishu-kit modules.

## Install with Server Support

```bash
pip install "feishu-kit[server]"
```

## Quick Start

```python
# app.py
from feishu_kit import FeishuClient
from server import create_app

client = FeishuClient(
    app_id="cli_xxx",
    app_secret="xxx",
)

app = create_app(client)
```

Run it:

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

Test:

```bash
curl http://localhost:8000/
# {"service":"feishu-kit","version":"0.1.0","modules":["wiki"]}

curl http://localhost:8000/wiki/spaces
# {"code":0,"data":{"items":[...]}}
```

## Multi-Bot Support

```python
from feishu_kit import ClientPool
from server import create_app

pool = ClientPool()
pool.add("default", "cli_app1_id", "cli_app1_secret")
pool.add("bot2", "cli_app2_id", "cli_app2_secret")

app = create_app(pool=pool)
```

## Available Endpoints

When the wiki router is loaded, these endpoints are available:

| Method | Path | Description |
|--------|------|-------------|
| GET | `/wiki/spaces` | List knowledge spaces |
| GET | `/wiki/spaces/{id}` | Get space info |
| GET | `/wiki/spaces/{id}/nodes` | List nodes |
| GET | `/wiki/spaces/{id}/nodes/tree` | Get node tree |
| GET | `/wiki/nodes/{token}` | Get node info |
| POST | `/wiki/spaces/{id}/nodes` | Create node |
| POST | `/wiki/spaces/{id}/nodes/{token}/rename` | Rename node |
| POST | `/wiki/spaces/{id}/nodes/{token}/move` | Move node |
| GET | `/wiki/docs/{token}/content` | Get document text |
| GET | `/wiki/docs/{token}/blocks` | Get document blocks |
| POST | `/wiki/docs/{token}/blocks/{id}/children` | Write blocks |
| GET | `/wiki/spaces/{id}/search?keyword=xxx` | Search nodes |

## Adding Custom Modules

Create a new router file in `server/routers/`:

```python
# server/routers/my_module.py
from fastapi import APIRouter
from feishu_kit.core.client import FeishuClient
from server.base import BaseModule

class MyModule(BaseModule):
    @property
    def name(self) -> str:
        return "my"

    def register(self, client: FeishuClient) -> APIRouter:
        router = APIRouter()

        @router.get("/hello")
        async def hello():
            return {"message": "Hello from my module!"}

        return router
```

It will be auto-discovered and mounted at `/my/`.

## Cleanup

```python
await client.close()
```

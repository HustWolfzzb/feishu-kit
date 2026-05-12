"""Optional FastAPI server layer for feishu-kit."""

import logging

from fastapi import FastAPI

from feishu_kit.core.client import FeishuClient
from feishu_kit.core.pool import ClientPool
from server.registry import ModuleRegistry

logger = logging.getLogger(__name__)


def create_app(
    client: FeishuClient | None = None,
    pool: ClientPool | None = None,
    enabled_modules: list[str] | None = None,
) -> FastAPI:
    """Create a FastAPI application with feishu-kit modules mounted.

    Args:
        client: FeishuClient to use. Required if pool is not provided.
        pool: ClientPool for multi-bot support. If provided, client is ignored
              and pool.default is used.
        enabled_modules: List of module names to load. None = load all.

    Returns:
        Configured FastAPI application.

    Example::

        from feishu_kit import FeishuClient
        from server import create_app

        client = FeishuClient("cli_xxx", "xxx")
        app = create_app(client)
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    app = FastAPI(
        title="feishu-kit Server",
        version="0.1.0",
        description="Feishu Open Platform API server powered by feishu-kit",
    )

    # Resolve client
    if pool is not None:
        active_client = pool.default
        _pool = pool
    elif client is not None:
        active_client = client
        _pool = None
    else:
        raise ValueError("Either client or pool must be provided")

    registry = ModuleRegistry(active_client)

    @app.get("/")
    async def root():
        return {
            "service": "feishu-kit",
            "version": "0.1.0",
            "modules": list(registry.loaded.keys()),
        }

    @app.get("/modules")
    async def list_modules():
        return {
            "loaded": {
                name: {"prefix": mod.prefix, "tags": mod.tags}
                for name, mod in registry.loaded.items()
            }
        }

    # Mount router modules
    registry.mount_all(
        app,
        modules_dir="server/routers",
        enabled=enabled_modules,
        module_fqn_prefix="server.routers",
    )

    @app.on_event("startup")
    async def on_startup():
        for mod in registry.loaded.values():
            await mod.on_startup()

    @app.on_event("shutdown")
    async def on_shutdown():
        for mod in registry.loaded.values():
            await mod.on_shutdown()
        if _pool is not None:
            await _pool.close_all()
        elif client is not None:
            await client.close()

    return app

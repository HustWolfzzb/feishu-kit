"""Module hot-reload — file change watcher and auto-reload."""

import asyncio
import logging
from pathlib import Path

from fastapi import FastAPI

from server.registry import ModuleRegistry

logger = logging.getLogger(__name__)


class ModuleLoader:
    """Watch modules directory for file changes and trigger hot-reload."""

    def __init__(self, registry: ModuleRegistry, app: FastAPI):
        self.registry = registry
        self.app = app
        self._task: asyncio.Task | None = None

    async def start(self, modules_dir: str = "server/routers") -> None:
        try:
            from watchfiles import awatch  # noqa: F401
        except ImportError:
            logger.warning("watchfiles not installed, hot-reload disabled. pip install watchfiles")
            return

        self._modules_dir = modules_dir
        self._task = asyncio.create_task(self._watch(modules_dir))
        logger.info("Hot-reload watcher started: %s", modules_dir)

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _watch(self, modules_dir: str) -> None:
        from watchfiles import awatch

        async for changes in awatch(modules_dir):
            affected: set[str] = set()
            for _change_type, path in changes:
                rel = Path(path).relative_to(modules_dir)
                module_name = rel.parts[0] if len(rel.parts) > 1 else None
                if module_name and module_name in self.registry.loaded:
                    affected.add(module_name)

            for name in affected:
                try:
                    self.registry.remount(self.app, name)
                except Exception as e:
                    logger.error("Hot-reload failed [%s]: %s", name, e)

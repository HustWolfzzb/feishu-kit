"""Module registry — auto-discover, load, and mount server modules."""

import importlib
import logging
import sys
from pathlib import Path

from fastapi import FastAPI

from feishu_kit.core.client import FeishuClient
from server.base import BaseModule

logger = logging.getLogger(__name__)


class ModuleRegistry:
    """Discover and manage server modules.

    Modules are discovered by scanning a directory for subdirectories
    containing ``__init__.py`` with a ``BaseModule`` subclass.
    """

    def __init__(self, client: FeishuClient):
        self._client = client
        self._modules: dict[str, BaseModule] = {}
        self._routers: dict[str, object] = {}

    def discover(self, modules_dir: str = "modules") -> list[str]:
        """Scan directory for module subdirectories."""
        base = Path(modules_dir)
        if not base.exists():
            logger.warning("Modules directory not found: %s", modules_dir)
            return []
        names = []
        for item in sorted(base.iterdir()):
            if item.is_dir() and not item.name.startswith("_") and (item / "__init__.py").exists():
                names.append(item.name)
        return names

    def load(self, name: str, module_fqn: str | None = None) -> BaseModule:
        """Import module, find BaseModule subclass, instantiate and register."""
        fqn = module_fqn or f"modules.{name}"
        mod = importlib.import_module(fqn)

        module_cls = None
        for attr_name in dir(mod):
            attr = getattr(mod, attr_name)
            if isinstance(attr, type) and issubclass(attr, BaseModule) and attr is not BaseModule:
                module_cls = attr
                break

        if module_cls is None:
            raise ValueError(f"No BaseModule subclass found in {fqn}")

        instance = module_cls()
        router = instance.register(self._client)
        self._modules[name] = instance
        self._routers[name] = router
        logger.info("Loaded module: %s", name)
        return instance

    def unload(self, name: str) -> None:
        self._modules.pop(name, None)
        self._routers.pop(name, None)

    def reload(self, name: str, module_fqn: str | None = None) -> BaseModule:
        """Clear import cache and reload a module."""
        fqn = module_fqn or f"modules.{name}"
        to_remove = [k for k in sys.modules if k.startswith(fqn)]
        for k in to_remove:
            del sys.modules[k]
        return self.load(name, module_fqn)

    def mount_all(
        self,
        app: FastAPI,
        modules_dir: str = "modules",
        enabled: list[str] | None = None,
        module_fqn_prefix: str = "modules",
    ) -> None:
        """Discover, filter, load, and mount all modules."""
        discovered = self.discover(modules_dir)
        to_load = discovered if not enabled else [n for n in discovered if n in enabled]
        for name in to_load:
            fqn = f"{module_fqn_prefix}.{name}"
            instance = self.load(name, fqn)
            router = self._routers[name]
            app.include_router(router, prefix=instance.prefix, tags=instance.tags)

    def remount(self, app: FastAPI, name: str, module_fqn: str | None = None) -> None:
        """Hot-reload: remove old routes, reload module, mount new routes."""
        old = self._modules.get(name)
        old_prefix = old.prefix if old else f"/{name}"

        def _route_belongs(route, prefix: str) -> bool:
            if not hasattr(route, "path"):
                return False
            path = route.path
            if path == prefix or path.startswith(prefix + "/"):
                return True
            if hasattr(route, "routes"):
                return True
            return False

        app.routes[:] = [r for r in app.routes if not _route_belongs(r, old_prefix)]

        fqn = module_fqn
        self.reload(name, fqn)
        new_instance = self._modules[name]
        app.include_router(
            self._routers[name],
            prefix=new_instance.prefix,
            tags=new_instance.tags,
        )
        logger.info("Hot-reloaded module: %s", name)

    @property
    def loaded(self) -> dict[str, BaseModule]:
        return dict(self._modules)

    def get(self, name: str) -> BaseModule | None:
        return self._modules.get(name)

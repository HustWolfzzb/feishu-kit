"""Base module for the optional FastAPI server layer."""

from abc import ABC, abstractmethod

from fastapi import APIRouter

from feishu_kit.core.client import FeishuClient


class BaseModule(ABC):
    """Abstract base class for server modules.

    Each module must implement:
    - ``name``: unique identifier (e.g. "wiki", "drive")
    - ``register(client)``: return an ``APIRouter`` with routes

    Example::

        class WikiModule(BaseModule):
            @property
            def name(self) -> str:
                return "wiki"

            def register(self, client: FeishuClient) -> APIRouter:
                service = WikiService(client)
                return create_wiki_router(service)
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique module identifier."""
        ...

    @property
    def prefix(self) -> str:
        """URL prefix, defaults to ``/<name>``."""
        return f"/{self.name}"

    @property
    def tags(self) -> list[str]:
        """OpenAPI tags for documentation grouping."""
        return [self.name]

    @abstractmethod
    def register(self, client: FeishuClient) -> APIRouter:
        """Create and return the module's APIRouter.

        Args:
            client: FeishuClient instance to use for API calls.

        Returns:
            Configured FastAPI APIRouter.
        """
        ...

    async def on_startup(self) -> None:
        """Called after the server starts. Override for initialization logic."""

    async def on_shutdown(self) -> None:
        """Called before the server stops. Override for cleanup logic."""

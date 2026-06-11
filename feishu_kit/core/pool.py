"""Multi-bot client pool."""

import logging

from feishu_kit.core.client import FeishuClient

logger = logging.getLogger(__name__)


class ClientPool:
    """Manage multiple named FeishuClient instances.

    Example::

        pool = ClientPool()
        pool.add("default", "cli_app1_id", "cli_app1_secret")
        pool.add("bot2", "cli_app2_id", "cli_app2_secret")

        client = pool.default
        client2 = pool.get("bot2")
    """

    def __init__(self):
        self._clients: dict[str, FeishuClient] = {}

    def add(self, name: str, app_id: str, app_secret: str) -> FeishuClient:
        """Register a new FeishuClient.

        Args:
            name: Client identifier (e.g. "default", "bot2").
            app_id: Feishu App ID.
            app_secret: Feishu App Secret.

        Returns:
            The created FeishuClient instance.
        """
        client = FeishuClient(app_id, app_secret)
        self._clients[name] = client
        logger.info("Registered bot client: %s (app_id=%s...)", name, app_id[:10])
        return client

    def get(self, name: str = "default") -> FeishuClient:
        """Get a client by name. Raises KeyError if not found."""
        if name in self._clients:
            return self._clients[name]
        raise KeyError(f"Bot client '{name}' not found. Available: {list(self._clients.keys())}")

    @property
    def default(self) -> FeishuClient:
        """Get the default client."""
        return self.get("default")

    @property
    def names(self) -> list[str]:
        """All registered client names."""
        return list(self._clients.keys())

    async def close_all(self) -> None:
        """Close all clients and release connections."""
        for name, client in self._clients.items():
            await client.close()
            logger.info("Closed bot client: %s", name)

    @classmethod
    def from_settings(cls, settings=None) -> "ClientPool":
        """Create a pool populated from a Settings instance.

        Args:
            settings: A Settings instance. If None, creates one from env/.env.

        Returns:
            ClientPool with 'default' (and optionally 'bot2') clients.
        """
        if settings is None:
            from feishu_kit.core.settings import Settings
            settings = Settings()
        pool = cls()
        if settings.feishu_app_id:
            pool.add("default", settings.feishu_app_id, settings.feishu_app_secret)
        if settings.feishu_bot2_app_id:
            pool.add("bot2", settings.feishu_bot2_app_id, settings.feishu_bot2_app_secret)
        return pool

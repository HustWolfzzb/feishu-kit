"""迁移处理器基类 — 按节点类型分发迁移逻辑"""

from abc import ABC, abstractmethod
from typing import Any

from feishu_kit.core.client import FeishuClient
from feishu_kit.modules.wiki.service import WikiService


class BaseHandler(ABC):
    """节点类型迁移处理器的基类契约。"""

    @abstractmethod
    def can_handle(self, obj_type: str) -> bool:
        """是否支持此 obj_type 的迁移。"""
        ...

    @abstractmethod
    async def copy(
        self,
        src_node: dict,
        target_space_id: str,
        target_parent_token: str,
    ) -> dict:
        """迁移单个节点。

        Args:
            src_node: 源节点信息，包含 node_token, obj_token, title, obj_type 等
            target_space_id: 目标知识空间 ID
            target_parent_token: 目标父节点 token

        Returns:
            {"success": bool, "target_node_token": str, "target_obj_token": str,
             "report": dict, "error": str | None}
        """
        ...

    def _get_wiki(self) -> WikiService:
        return self._wiki

    def _get_client(self) -> FeishuClient:
        return self._client

    def __init__(self, wiki: WikiService, client: FeishuClient):
        self._wiki = wiki
        self._client = client

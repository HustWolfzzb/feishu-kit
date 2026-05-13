"""feishu-kit — A modular Python toolkit for Feishu Open Platform."""

__version__ = "0.1.0"

from feishu_kit.core.client import FeishuClient
from feishu_kit.core.pool import ClientPool
from feishu_kit.core.settings import Settings

__all__ = ["ClientPool", "FeishuClient", "Settings"]

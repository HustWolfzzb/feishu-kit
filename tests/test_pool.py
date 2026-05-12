"""Tests for ClientPool."""

import pytest
from feishu_kit.core.pool import ClientPool
from feishu_kit.core.client import FeishuClient


def test_add_and_get():
    pool = ClientPool()
    client = pool.add("default", "cli_a", "secret_a")
    assert isinstance(client, FeishuClient)
    assert pool.get("default") is client


def test_default_property():
    pool = ClientPool()
    pool.add("default", "cli_a", "secret_a")
    assert pool.default is pool.get("default")


def test_get_missing_raises():
    pool = ClientPool()
    with pytest.raises(KeyError, match="not found"):
        pool.get("nonexistent")


def test_multiple_bots():
    pool = ClientPool()
    pool.add("bot1", "cli_a", "secret_a")
    pool.add("bot2", "cli_b", "secret_b")
    assert pool.names == ["bot1", "bot2"]
    assert pool.get("bot1") is not pool.get("bot2")


def test_names():
    pool = ClientPool()
    assert pool.names == []
    pool.add("default", "cli_a", "secret_a")
    assert pool.names == ["default"]


@pytest.mark.asyncio
async def test_close_all():
    pool = ClientPool()
    pool.add("default", "cli_a", "secret_a")
    # Should not raise
    await pool.close_all()

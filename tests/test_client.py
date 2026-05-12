"""Tests for FeishuClient."""

import pytest
from feishu_kit.core.client import FeishuClient


def test_client_requires_credentials():
    """Client should reject empty credentials."""
    with pytest.raises(ValueError, match="app_id and app_secret are required"):
        FeishuClient("", "")

    with pytest.raises(ValueError):
        FeishuClient("cli_xxx", "")

    with pytest.raises(ValueError):
        FeishuClient("", "secret")


def test_client_stores_credentials():
    """Client should store app_id and app_secret."""
    client = FeishuClient("cli_test", "secret_test")
    assert client._app_id == "cli_test"
    assert client._app_secret == "secret_test"

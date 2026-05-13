"""Shared test fixtures."""

import pytest
from feishu_kit.core.client import FeishuClient


class MockFeishuClient(FeishuClient):
    """A FeishuClient that records calls and returns preset responses."""

    def __init__(self):
        # Bypass parent __init__ validation
        self._app_id = "mock_app_id"
        self._app_secret = "mock_app_secret"
        self._responses: dict[str, dict] = {}
        self.calls: list[dict] = []

    def set_response(self, path: str, response: dict):
        """Preset a response for a given API path."""
        self._responses[path] = response

    async def request(self, method, path, *, params=None, json=None) -> dict:
        self.calls.append(
            {
                "method": method,
                "path": path,
                "params": params,
                "json": json,
            }
        )
        return self._responses.get(path, {"code": 0, "data": {}})

    async def upload(self, path, *, file_name, file_data, fields=None, params=None) -> dict:
        self.calls.append(
            {
                "method": "UPLOAD",
                "path": path,
                "file_name": file_name,
                "fields": fields,
            }
        )
        return self._responses.get(path, {"code": 0, "data": {"file_token": "mock_file_token"}})

    async def close(self):
        pass


@pytest.fixture
def mock_client():
    return MockFeishuClient()

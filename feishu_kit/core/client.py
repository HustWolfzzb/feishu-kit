"""Feishu Open API HTTP client with automatic token management."""

import asyncio
import time
import logging

import httpx

logger = logging.getLogger(__name__)

FEISHU_BASE_URL = "https://open.feishu.cn/open-apis"


class FeishuClient:
    """Async Feishu API client with automatic token refresh and connection pooling.

    Args:
        app_id: Feishu App ID.
        app_secret: Feishu App Secret.

    Example::

        client = FeishuClient(app_id="cli_xxx", app_secret="xxx")
        result = await client.request("GET", "/wiki/v2/spaces")
        await client.close()
    """

    def __init__(self, app_id: str, app_secret: str):
        if not app_id or not app_secret:
            raise ValueError("app_id and app_secret are required")
        self._app_id = app_id
        self._app_secret = app_secret
        self._tenant_access_token: str | None = None
        self._token_expires_at: float = 0
        self._token_lock = asyncio.Lock()
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the persistent async HTTP client with connection pooling."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=FEISHU_BASE_URL,
                timeout=httpx.Timeout(30.0, connect=10.0),
                limits=httpx.Limits(
                    max_connections=20,
                    max_keepalive_connections=10,
                    keepalive_expiry=60,
                ),
                headers={"Content-Type": "application/json; charset=utf-8"},
            )
        return self._client

    async def _ensure_token(self) -> None:
        """Refresh tenant_access_token if expired (thread-safe)."""
        if self._tenant_access_token and time.time() < self._token_expires_at:
            return

        async with self._token_lock:
            if self._tenant_access_token and time.time() < self._token_expires_at:
                return

            client = await self._get_client()
            resp = await client.post(
                "/auth/v3/tenant_access_token/internal",
                json={
                    "app_id": self._app_id,
                    "app_secret": self._app_secret,
                },
            )

            if resp.status_code >= 400:
                raise RuntimeError(f"Token request failed: HTTP {resp.status_code}")

            data = resp.json()
            if data.get("code") != 0:
                raise RuntimeError(f"Failed to get token: {data.get('msg')}")

            self._tenant_access_token = data["tenant_access_token"]
            # Refresh 5 minutes before actual expiry
            self._token_expires_at = time.time() + data["expire"] - 300
            logger.info("Refreshed tenant_access_token")

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json: dict | None = None,
    ) -> dict:
        """Send an authenticated request to Feishu Open API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, PATCH).
            path: API path (e.g. "/wiki/v2/spaces").
            params: Query parameters.
            json: JSON body.

        Returns:
            Parsed JSON response.
        """
        await self._ensure_token()

        client = await self._get_client()
        headers = {"Authorization": f"Bearer {self._tenant_access_token}"}

        resp = await client.request(
            method, path, headers=headers, params=params, json=json,
        )

        if resp.status_code >= 400:
            try:
                return resp.json()
            except Exception:
                resp.raise_for_status()

        return resp.json()

    async def upload(
        self,
        path: str,
        *,
        file_name: str,
        file_data: bytes,
        fields: dict[str, str] | None = None,
        params: dict | None = None,
    ) -> dict:
        """Send a multipart/form-data upload request to Feishu.

        Args:
            path: Upload API path.
            file_name: Name of the file.
            file_data: File content as bytes.
            fields: Additional form fields.
            params: Query parameters.
        """
        await self._ensure_token()
        headers = {"Authorization": f"Bearer {self._tenant_access_token}"}

        async with httpx.AsyncClient(
            base_url=FEISHU_BASE_URL,
            timeout=httpx.Timeout(120.0, connect=10.0),
        ) as client:
            resp = await client.request(
                "POST", path,
                headers=headers,
                params=params,
                data=fields or {},
                files={"file": (file_name, file_data)},
            )

            if resp.status_code >= 400:
                try:
                    return resp.json()
                except Exception:
                    resp.raise_for_status()

            return resp.json()

    async def close(self) -> None:
        """Close the persistent HTTP client and release connections."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

"""Feishu Open API HTTP client with automatic token management."""

from __future__ import annotations

import asyncio
import logging
import time

import httpx

from feishu_kit.core.exceptions import APIError, AuthenticationError, RateLimitError

logger = logging.getLogger(__name__)

FEISHU_BASE_URL = "https://open.feishu.cn/open-apis"
MAX_RETRIES = 3


class FeishuClient:
    """Async Feishu API client with automatic token refresh and connection pooling.

    Args:
        app_id: Feishu App ID.
        app_secret: Feishu App Secret.

    Example::

        async with FeishuClient(app_id="cli_xxx", app_secret="xxx") as client:
            result = await client.request("GET", "/wiki/v2/spaces")
    """

    def __init__(self, app_id: str, app_secret: str) -> None:
        if not app_id or not app_secret:
            raise ValueError("app_id and app_secret are required")
        self._app_id = app_id
        self._app_secret = app_secret
        self._tenant_access_token: str | None = None
        self._token_expires_at: float = 0
        self._token_lock = asyncio.Lock()
        self._client: httpx.AsyncClient | None = None

    def __repr__(self) -> str:
        masked = self._app_id[:6] + "..." if len(self._app_id) > 6 else "***"
        return f"FeishuClient(app_id={masked!r})"

    async def __aenter__(self) -> FeishuClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

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
                raise AuthenticationError(f"Token request failed: HTTP {resp.status_code}")

            data = resp.json()
            if data.get("code") != 0:
                raise AuthenticationError(f"Failed to get token: {data.get('msg')}")

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

        Automatically retries on 429 (rate limit) and 5xx errors with
        exponential backoff.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, PATCH).
            path: API path (e.g. "/wiki/v2/spaces").
            params: Query parameters.
            json: JSON body.

        Returns:
            Parsed JSON response.

        Raises:
            AuthenticationError: If the token is invalid.
            RateLimitError: If rate limited after all retries.
            APIError: If the API returns a non-zero code.
        """
        await self._ensure_token()

        client = await self._get_client()
        headers = {"Authorization": f"Bearer {self._tenant_access_token}"}

        last_exception: Exception | None = None

        for attempt in range(MAX_RETRIES):
            resp = await client.request(
                method,
                path,
                headers=headers,
                params=params,
                json=json,
            )

            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 2**attempt))
                logger.warning(
                    "Rate limited on %s %s, retrying in %ds (attempt %d/%d)",
                    method,
                    path,
                    retry_after,
                    attempt + 1,
                    MAX_RETRIES,
                )
                await asyncio.sleep(retry_after)
                last_exception = RateLimitError(retry_after)
                continue

            if resp.status_code >= 500:
                wait = 2**attempt
                logger.warning(
                    "Server error %d on %s %s, retrying in %ds (attempt %d/%d)",
                    resp.status_code,
                    method,
                    path,
                    wait,
                    attempt + 1,
                    MAX_RETRIES,
                )
                await asyncio.sleep(wait)
                last_exception = APIError(resp.status_code, f"HTTP {resp.status_code}")
                continue

            if resp.status_code == 401:
                raise AuthenticationError("Unauthorized — check app_id and app_secret")

            if resp.status_code >= 400:
                try:
                    data = resp.json()
                    raise APIError(data.get("code", resp.status_code), data.get("msg", ""))
                except (ValueError, KeyError):
                    resp.raise_for_status()

            data = resp.json()
            if data.get("code", 0) != 0:
                raise APIError(data["code"], data.get("msg", "Unknown error"))

            return data

        # All retries exhausted
        if last_exception:
            raise last_exception
        raise APIError(-1, "All retries exhausted")

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

        Returns:
            Parsed JSON response.
        """
        await self._ensure_token()
        headers = {"Authorization": f"Bearer {self._tenant_access_token}"}

        async with httpx.AsyncClient(
            base_url=FEISHU_BASE_URL,
            timeout=httpx.Timeout(120.0, connect=10.0),
        ) as client:
            resp = await client.request(
                "POST",
                path,
                headers=headers,
                params=params,
                data=fields or {},
                files={"file": (file_name, file_data)},
            )

            if resp.status_code >= 400:
                try:
                    data = resp.json()
                    raise APIError(data.get("code", resp.status_code), data.get("msg", ""))
                except (ValueError, KeyError):
                    resp.raise_for_status()

            data = resp.json()
            if data.get("code", 0) != 0:
                raise APIError(data["code"], data.get("msg", ""))
            return data

    async def download(self, path: str, *, params: dict | None = None) -> bytes:
        """Download binary content from Feishu (e.g. images, files).

        Returns:
            Raw bytes of the downloaded content.
        """
        await self._ensure_token()
        headers = {"Authorization": f"Bearer {self._tenant_access_token}"}

        client = await self._get_client()
        resp = await client.request("GET", path, headers=headers, params=params)

        if resp.status_code >= 400:
            raise APIError(resp.status_code, f"Download failed: HTTP {resp.status_code}")

        return resp.content

    async def close(self) -> None:
        """Close the persistent HTTP client and release connections."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

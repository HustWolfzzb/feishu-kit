"""Butler LLM client — shared LLM call utilities."""

import httpx

from feishu_kit.core.settings import Settings as settings

_http: httpx.AsyncClient | None = None


async def get_llm_client() -> httpx.AsyncClient:
    global _http
    if _http is None or _http.is_closed:
        _http = httpx.AsyncClient(
            base_url=settings.llm_base_url,
            timeout=httpx.Timeout(settings.llm_timeout, connect=10.0),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )
    return _http


async def call_llm(messages: list[dict], temperature: float | None = None) -> str:
    """Call the configured LLM and return the assistant message content."""
    client = await get_llm_client()
    resp = await client.post(
        "/chat/completions",
        headers={"Authorization": f"Bearer {settings.llm_api_key}"},
        json={
            "model": settings.llm_model,
            "messages": messages,
            "max_tokens": settings.llm_max_tokens,
            "temperature": temperature if temperature is not None else settings.llm_temperature,
        },
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


async def call_llm_json(messages: list[dict], temperature: float = 0.0) -> dict:
    """Call LLM and parse the response as JSON.

    The prompt must instruct the model to return valid JSON.
    Falls back to extracting JSON from markdown code fences.
    """
    import json
    raw = await call_llm(messages, temperature=temperature)
    raw = raw.strip()
    # Strip markdown code fence if present
    if raw.startswith("```"):
        lines = raw.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        raw = "\n".join(lines).strip()
    return json.loads(raw)

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from zero_env_proxy.config import ServiceConfig


@dataclass(frozen=True)
class ProviderResponse:
    status_code: int
    body: dict[str, Any] | bytes
    headers: dict[str, str]
    media_type: str


async def call_mock_provider(
    *,
    method: str,
    path: str,
    headers: dict[str, str],
    query: dict[str, str],
    body: bytes,
) -> ProviderResponse:
    return ProviderResponse(
        status_code=200,
        body={
            "provider": "mockai",
            "path": path,
            "method": method,
            "message": "Zero-Env Proxy mock response: approved caller reached the provider boundary.",
        },
        headers={"x-zero-env-provider": "mock"},
        media_type="application/json",
    )


async def call_http_provider(
    *,
    service: ServiceConfig,
    method: str,
    path: str,
    headers: dict[str, str],
    query: dict[str, str],
    body: bytes,
    api_key: str,
) -> ProviderResponse:
    target_url = f"{service.target_url}/{path.lstrip('/')}"
    safe_headers = {
        key: value
        for key, value in headers.items()
        if key.lower() not in {"host", "authorization", "connection", "transfer-encoding"}
    }
    safe_headers["Authorization"] = f"Bearer {api_key}"
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.request(
            method,
            target_url,
            headers=safe_headers,
            params=query,
            content=body,
        )
    return ProviderResponse(
        status_code=response.status_code,
        body=response.content,
        headers={
            key: value
            for key, value in response.headers.items()
            if key.lower() not in {"connection", "transfer-encoding", "content-length"}
        },
        media_type=response.headers.get("content-type", "application/octet-stream"),
    )

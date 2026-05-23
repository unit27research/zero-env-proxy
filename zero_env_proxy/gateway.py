from __future__ import annotations

from pathlib import Path
from typing import Callable
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response

from zero_env_proxy.config import ZeroEnvConfig
from zero_env_proxy.identity import IdentityError, resolve_caller_from_client_port
from zero_env_proxy.lockfile import LockError, verify_file
from zero_env_proxy.providers import call_http_provider, call_mock_provider


CallerResolver = Callable[[int], Path]


def _relative_to_root(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def create_app(
    *,
    config: ZeroEnvConfig,
    lock_path: str | Path = "zero-env.lock",
    caller_resolver: CallerResolver = resolve_caller_from_client_port,
) -> FastAPI:
    app = FastAPI(title="Zero-Env Proxy")

    @app.api_route("/{service_name}/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    async def gateway(service_name: str, path: str, request: Request):
        service = config.services.get(service_name)
        if service is None:
            raise HTTPException(status_code=404, detail=f"Service not configured: {service_name}")

        if request.client is None:
            raise HTTPException(status_code=403, detail="Access denied: client identity unavailable")

        try:
            caller_path = caller_resolver(request.client.port)
            verify_file(caller_path, lock_path=lock_path)
        except (IdentityError, LockError) as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

        caller_display = _relative_to_root(caller_path, config.root)
        if caller_display not in service.allowed_files:
            raise HTTPException(
                status_code=403,
                detail=f"Caller not allowed for service: {caller_display}",
            )

        body = await request.body()
        headers = dict(request.headers)
        query = {key: value for key, value in request.query_params.items()}

        if service.provider == "mock":
            provider_response = await call_mock_provider(
                method=request.method,
                path=path,
                headers=headers,
                query=query,
                body=body,
            )
            return JSONResponse(
                status_code=provider_response.status_code,
                content=provider_response.body,
                headers=provider_response.headers,
                media_type=provider_response.media_type,
            )

        if service.provider == "http":
            if not service.api_key_env:
                raise HTTPException(status_code=500, detail="HTTP service missing api_key_env")
            api_key = os.environ.get(service.api_key_env)
            if not api_key:
                raise HTTPException(
                    status_code=500,
                    detail=f"Missing required secret env: {service.api_key_env}",
                )
            provider_response = await call_http_provider(
                service=service,
                method=request.method,
                path=path,
                headers=headers,
                query=query,
                body=body,
                api_key=api_key,
            )
            return Response(
                status_code=provider_response.status_code,
                content=provider_response.body,
                headers=provider_response.headers,
                media_type=provider_response.media_type,
            )

        raise HTTPException(status_code=500, detail=f"Unsupported provider: {service.provider}")

    return app

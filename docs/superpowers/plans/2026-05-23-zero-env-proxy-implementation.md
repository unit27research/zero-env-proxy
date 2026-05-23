# Zero-Env Proxy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Zero-Env Proxy as a public Unit27 field-kit repo, then graduate it into an installable CLI without changing the core behavior.

**Architecture:** Implement a small Python package with separate modules for config loading, lockfile enrollment, local caller identity, provider routing, FastAPI gateway behavior, and CLI commands. Phase B proves the behavior with mock-provider demos and tests; Phase C exposes the same internals through the `zero-env` console command and package verification.

**Tech Stack:** Python 3.11+, FastAPI, httpx, PyYAML, psutil, pytest, uvicorn, stdlib argparse/dataclasses/pathlib/hashlib/json.

---

## File Structure

- Create `pyproject.toml`: package metadata, dependencies, pytest config, console script for Phase C.
- Create `.gitignore`: ignore local config, lockfiles, secrets, caches, build outputs.
- Create `README.md`: public claim, quickstart, demo transcript, boundaries, tests.
- Create `zero_env_proxy/__init__.py`: package version.
- Create `zero_env_proxy/config.py`: load and validate YAML config.
- Create `zero_env_proxy/lockfile.py`: enroll files and verify runtime file state.
- Create `zero_env_proxy/identity.py`: resolve caller process from localhost client port.
- Create `zero_env_proxy/providers.py`: mock provider and real HTTP provider behavior.
- Create `zero_env_proxy/gateway.py`: FastAPI app factory and request gateway.
- Create `zero_env_proxy/cli.py`: `init`, `enroll`, `serve`, `demo`, `inspect-lock`.
- Create `examples/zero-env.yaml.example`: safe mock config.
- Create `examples/allowed_agent.py`: expected approved caller.
- Create `examples/blocked_agent.py`: expected rejected caller.
- Create `examples/tamper_demo.py`: helper that changes an enrolled file copy and proves rejection.
- Create `tests/test_config.py`: config validation coverage.
- Create `tests/test_lockfile.py`: enrollment, canonical path, tamper, same-basename rejection.
- Create `tests/test_providers.py`: deterministic mock provider behavior.
- Create `tests/test_gateway.py`: gateway status behavior and auth checks using dependency overrides.
- Create `tests/test_cli.py`: CLI smoke checks for Phase C.
- Create `scripts/verify_wheel.py`: check wheel contains package, examples, and console entry point.

## Phase B Tasks

### Task 1: Package Skeleton And Safe Defaults

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `zero_env_proxy/__init__.py`
- Create: `examples/zero-env.yaml.example`
- Test: `pytest --version`

- [ ] **Step 1: Create package metadata**

Create `pyproject.toml` with this content:

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "zero-env-proxy"
version = "0.1.0"
description = "A small local credential proxy for automation scripts."
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.111",
  "httpx>=0.27",
  "psutil>=5.9",
  "pyyaml>=6.0",
  "uvicorn>=0.30",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "build>=1.2"]

[project.scripts]
zero-env = "zero_env_proxy.cli:main"

[tool.setuptools.packages.find]
where = ["."]
include = ["zero_env_proxy*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

- [ ] **Step 2: Add ignore rules**

Create `.gitignore`:

```gitignore
__pycache__/
.pytest_cache/
.venv/
build/
dist/
*.egg-info/
zero-env.yaml
zero-env.lock
.env
.env.local
*.log
```

- [ ] **Step 3: Add package version**

Create `zero_env_proxy/__init__.py`:

```python
"""Zero-Env Proxy package."""

__version__ = "0.1.0"
```

- [ ] **Step 4: Add mock config example**

Create `examples/zero-env.yaml.example`:

```yaml
proxy:
  host: "127.0.0.1"
  port: 5050

services:
  mockai:
    provider: "mock"
    target_url: "mock://local"
    allowed_files:
      - "examples/allowed_agent.py"
```

- [ ] **Step 5: Run environment smoke check**

Run: `python3 -m pytest --version`

Expected: either pytest version prints, or command fails because pytest is not installed. If pytest is missing, use the bundled Codex Python runtime or install dev dependencies in a local venv before tests.

- [ ] **Step 6: Commit**

Run:

```bash
git add pyproject.toml .gitignore zero_env_proxy/__init__.py examples/zero-env.yaml.example
git commit -m "chore: scaffold zero-env proxy package"
```

### Task 2: Config Loader

**Files:**
- Create: `zero_env_proxy/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write config tests**

Create `tests/test_config.py`:

```python
from pathlib import Path

import pytest

from zero_env_proxy.config import ConfigError, load_config


def test_loads_valid_mock_config(tmp_path: Path):
    config_path = tmp_path / "zero-env.yaml"
    config_path.write_text(
        """
proxy:
  host: "127.0.0.1"
  port: 5050
services:
  mockai:
    provider: "mock"
    target_url: "mock://local"
    allowed_files:
      - "examples/allowed_agent.py"
""".strip(),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.proxy.host == "127.0.0.1"
    assert config.proxy.port == 5050
    assert config.services["mockai"].provider == "mock"
    assert config.services["mockai"].allowed_files == ["examples/allowed_agent.py"]


def test_rejects_service_without_allowed_files(tmp_path: Path):
    config_path = tmp_path / "zero-env.yaml"
    config_path.write_text(
        """
proxy:
  host: "127.0.0.1"
  port: 5050
services:
  mockai:
    provider: "mock"
    target_url: "mock://local"
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="allowed_files"):
        load_config(config_path)
```

- [ ] **Step 2: Run failing tests**

Run: `python3 -m pytest tests/test_config.py -v`

Expected: FAIL because `zero_env_proxy.config` does not exist.

- [ ] **Step 3: Implement config loader**

Create `zero_env_proxy/config.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    """Raised when zero-env configuration is invalid."""


@dataclass(frozen=True)
class ProxyConfig:
    host: str
    port: int


@dataclass(frozen=True)
class ServiceConfig:
    provider: str
    target_url: str
    allowed_files: list[str]
    api_key_env: str | None = None


@dataclass(frozen=True)
class ZeroEnvConfig:
    proxy: ProxyConfig
    services: dict[str, ServiceConfig]
    root: Path


def load_config(path: str | Path = "zero-env.yaml") -> ZeroEnvConfig:
    config_path = Path(path)
    if not config_path.exists():
        raise ConfigError(f"Config file not found: {config_path}")

    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ConfigError("Config root must be a mapping.")

    proxy_raw = raw.get("proxy")
    services_raw = raw.get("services")
    if not isinstance(proxy_raw, dict):
        raise ConfigError("Config must include proxy mapping.")
    if not isinstance(services_raw, dict) or not services_raw:
        raise ConfigError("Config must include at least one service.")

    host = proxy_raw.get("host", "127.0.0.1")
    port = proxy_raw.get("port", 5050)
    if not isinstance(host, str):
        raise ConfigError("proxy.host must be a string.")
    if not isinstance(port, int):
        raise ConfigError("proxy.port must be an integer.")

    services: dict[str, ServiceConfig] = {}
    for name, service_raw in services_raw.items():
        if not isinstance(name, str) or not name:
            raise ConfigError("Service names must be non-empty strings.")
        if not isinstance(service_raw, dict):
            raise ConfigError(f"Service {name} must be a mapping.")
        provider = service_raw.get("provider")
        target_url = service_raw.get("target_url")
        allowed_files = service_raw.get("allowed_files")
        api_key_env = service_raw.get("api_key_env")
        if not isinstance(provider, str) or not provider:
            raise ConfigError(f"Service {name} provider must be a string.")
        if not isinstance(target_url, str) or not target_url:
            raise ConfigError(f"Service {name} target_url must be a string.")
        if not isinstance(allowed_files, list) or not all(isinstance(item, str) for item in allowed_files):
            raise ConfigError(f"Service {name} allowed_files must be a list of strings.")
        if api_key_env is not None and not isinstance(api_key_env, str):
            raise ConfigError(f"Service {name} api_key_env must be a string when provided.")
        services[name] = ServiceConfig(
            provider=provider,
            target_url=target_url.rstrip("/"),
            allowed_files=allowed_files,
            api_key_env=api_key_env,
        )

    return ZeroEnvConfig(
        proxy=ProxyConfig(host=host, port=port),
        services=services,
        root=config_path.resolve().parent,
    )
```

- [ ] **Step 4: Run passing tests**

Run: `python3 -m pytest tests/test_config.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add zero_env_proxy/config.py tests/test_config.py
git commit -m "feat: load zero-env config"
```

### Task 3: Lockfile Enrollment And Verification

**Files:**
- Create: `zero_env_proxy/lockfile.py`
- Create: `tests/test_lockfile.py`

- [ ] **Step 1: Write lockfile tests**

Create `tests/test_lockfile.py`:

```python
from pathlib import Path

import pytest

from zero_env_proxy.lockfile import LockError, enroll_file, load_lockfile, verify_file


def test_enrollment_records_canonical_path_and_hash(tmp_path: Path):
    script = tmp_path / "agent.py"
    script.write_text("print('ok')\n", encoding="utf-8")
    lock_path = tmp_path / "zero-env.lock"

    record = enroll_file(script, lock_path=lock_path, project_root=tmp_path)
    lock = load_lockfile(lock_path)

    assert record.path == str(script.resolve())
    assert record.display_path == "agent.py"
    assert len(record.sha256) == 64
    assert lock.files[str(script.resolve())].sha256 == record.sha256


def test_verify_passes_for_unchanged_file(tmp_path: Path):
    script = tmp_path / "agent.py"
    script.write_text("print('ok')\n", encoding="utf-8")
    lock_path = tmp_path / "zero-env.lock"
    enroll_file(script, lock_path=lock_path, project_root=tmp_path)

    record = verify_file(script, lock_path=lock_path)

    assert record.display_path == "agent.py"


def test_verify_fails_after_content_change(tmp_path: Path):
    script = tmp_path / "agent.py"
    script.write_text("print('ok')\n", encoding="utf-8")
    lock_path = tmp_path / "zero-env.lock"
    enroll_file(script, lock_path=lock_path, project_root=tmp_path)
    script.write_text("print('changed')\n", encoding="utf-8")

    with pytest.raises(LockError, match="hash mismatch"):
        verify_file(script, lock_path=lock_path)


def test_same_basename_different_path_is_rejected(tmp_path: Path):
    allowed_dir = tmp_path / "allowed"
    blocked_dir = tmp_path / "blocked"
    allowed_dir.mkdir()
    blocked_dir.mkdir()
    allowed = allowed_dir / "agent.py"
    blocked = blocked_dir / "agent.py"
    allowed.write_text("print('allowed')\n", encoding="utf-8")
    blocked.write_text("print('allowed')\n", encoding="utf-8")
    lock_path = tmp_path / "zero-env.lock"
    enroll_file(allowed, lock_path=lock_path, project_root=tmp_path)

    with pytest.raises(LockError, match="not enrolled"):
        verify_file(blocked, lock_path=lock_path)
```

- [ ] **Step 2: Run failing tests**

Run: `python3 -m pytest tests/test_lockfile.py -v`

Expected: FAIL because `zero_env_proxy.lockfile` does not exist.

- [ ] **Step 3: Implement lockfile**

Create `zero_env_proxy/lockfile.py`:

```python
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json


class LockError(ValueError):
    """Raised when lockfile enrollment or verification fails."""


@dataclass(frozen=True)
class FileRecord:
    path: str
    display_path: str
    sha256: str
    size: int
    mtime: float
    enrolled_at: str


@dataclass(frozen=True)
class Lockfile:
    version: int
    files: dict[str, FileRecord]


def file_sha256(path: str | Path) -> str:
    target = Path(path)
    digest = hashlib.sha256()
    with target.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_lockfile(lock_path: str | Path = "zero-env.lock") -> Lockfile:
    path = Path(lock_path)
    if not path.exists():
        raise LockError(f"Lockfile not found: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    files = {
        file_path: FileRecord(**record)
        for file_path, record in raw.get("files", {}).items()
    }
    return Lockfile(version=int(raw.get("version", 1)), files=files)


def save_lockfile(lockfile: Lockfile, lock_path: str | Path = "zero-env.lock") -> None:
    path = Path(lock_path)
    payload = {
        "version": lockfile.version,
        "files": {file_path: asdict(record) for file_path, record in lockfile.files.items()},
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def enroll_file(
    file_path: str | Path,
    *,
    lock_path: str | Path = "zero-env.lock",
    project_root: str | Path | None = None,
) -> FileRecord:
    path = Path(file_path).resolve()
    if not path.exists() or not path.is_file():
        raise LockError(f"Cannot enroll missing file: {file_path}")

    root = Path(project_root).resolve() if project_root else Path.cwd().resolve()
    try:
        display_path = path.relative_to(root).as_posix()
    except ValueError:
        display_path = path.name

    stat = path.stat()
    record = FileRecord(
        path=str(path),
        display_path=display_path,
        sha256=file_sha256(path),
        size=stat.st_size,
        mtime=stat.st_mtime,
        enrolled_at=datetime.now(timezone.utc).isoformat(),
    )

    try:
        existing = load_lockfile(lock_path)
        files = dict(existing.files)
    except LockError:
        files = {}
    files[str(path)] = record
    save_lockfile(Lockfile(version=1, files=files), lock_path)
    return record


def verify_file(file_path: str | Path, *, lock_path: str | Path = "zero-env.lock") -> FileRecord:
    path = Path(file_path).resolve()
    lock = load_lockfile(lock_path)
    record = lock.files.get(str(path))
    if record is None:
        raise LockError(f"File not enrolled: {path}")
    if not path.exists():
        raise LockError(f"Enrolled file missing: {path}")
    current_hash = file_sha256(path)
    if current_hash != record.sha256:
        raise LockError(f"File hash mismatch for {record.display_path}")
    return record
```

- [ ] **Step 4: Run passing tests**

Run: `python3 -m pytest tests/test_lockfile.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add zero_env_proxy/lockfile.py tests/test_lockfile.py
git commit -m "feat: add lockfile enrollment"
```

### Task 4: Provider Layer

**Files:**
- Create: `zero_env_proxy/providers.py`
- Create: `tests/test_providers.py`

- [ ] **Step 1: Write provider tests**

Create `tests/test_providers.py`:

```python
import asyncio

from zero_env_proxy.providers import ProviderResponse, call_mock_provider


def test_mock_provider_returns_deterministic_completion():
    response = asyncio.run(
        call_mock_provider(
            method="POST",
            path="v1/chat/completions",
            headers={},
            query={},
            body=b'{"messages":[]}',
        )
    )

    assert isinstance(response, ProviderResponse)
    assert response.status_code == 200
    assert response.media_type == "application/json"
    assert response.body["provider"] == "mockai"
    assert "Zero-Env Proxy mock response" in response.body["message"]
```

- [ ] **Step 2: Run failing tests**

Run: `python3 -m pytest tests/test_providers.py -v`

Expected: FAIL because `zero_env_proxy.providers` does not exist.

- [ ] **Step 3: Implement providers**

Create `zero_env_proxy/providers.py`:

```python
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
```

- [ ] **Step 4: Run passing tests**

Run: `python3 -m pytest tests/test_providers.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add zero_env_proxy/providers.py tests/test_providers.py
git commit -m "feat: add provider routing layer"
```

### Task 5: Identity Resolver

**Files:**
- Create: `zero_env_proxy/identity.py`
- Create: `tests/test_identity.py`

- [ ] **Step 1: Write identity helper tests**

Create `tests/test_identity.py`:

```python
from pathlib import Path

from zero_env_proxy.identity import extract_python_script_path


def test_extract_python_script_path_prefers_py_file(tmp_path: Path):
    script = tmp_path / "agent.py"
    script.write_text("print('ok')\n", encoding="utf-8")

    result = extract_python_script_path(["python", str(script)])

    assert result == script.resolve()


def test_extract_python_script_path_returns_none_without_script():
    assert extract_python_script_path(["python", "-m", "module"]) is None
```

- [ ] **Step 2: Run failing tests**

Run: `python3 -m pytest tests/test_identity.py -v`

Expected: FAIL because `zero_env_proxy.identity` does not exist.

- [ ] **Step 3: Implement identity resolver**

Create `zero_env_proxy/identity.py`:

```python
from __future__ import annotations

from pathlib import Path

import psutil


class IdentityError(ValueError):
    """Raised when the local caller cannot be resolved."""


def extract_python_script_path(cmdline: list[str]) -> Path | None:
    for arg in cmdline:
        if arg.endswith(".py"):
            return Path(arg).resolve()
    return None


def resolve_caller_from_client_port(client_port: int) -> Path:
    for conn in psutil.net_connections(kind="inet"):
        if not conn.raddr or conn.raddr.port != client_port or conn.pid is None:
            continue
        try:
            process = psutil.Process(conn.pid)
            script_path = extract_python_script_path(process.cmdline())
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            continue
        if script_path is not None:
            return script_path
    raise IdentityError(f"Could not resolve caller for client port {client_port}")
```

- [ ] **Step 4: Run passing tests**

Run: `python3 -m pytest tests/test_identity.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add zero_env_proxy/identity.py tests/test_identity.py
git commit -m "feat: resolve local caller identity"
```

### Task 6: FastAPI Gateway

**Files:**
- Create: `zero_env_proxy/gateway.py`
- Create: `tests/test_gateway.py`

- [ ] **Step 1: Write gateway tests**

Create `tests/test_gateway.py`:

```python
from pathlib import Path

from fastapi.testclient import TestClient

from zero_env_proxy.config import ProxyConfig, ServiceConfig, ZeroEnvConfig
from zero_env_proxy.gateway import create_app
from zero_env_proxy.lockfile import enroll_file


def make_config(tmp_path: Path) -> ZeroEnvConfig:
    return ZeroEnvConfig(
        proxy=ProxyConfig(host="127.0.0.1", port=5050),
        services={
            "mockai": ServiceConfig(
                provider="mock",
                target_url="mock://local",
                allowed_files=["examples/allowed_agent.py"],
            )
        },
        root=tmp_path,
    )


def test_unknown_service_returns_404(tmp_path: Path):
    app = create_app(
        config=make_config(tmp_path),
        lock_path=tmp_path / "zero-env.lock",
        caller_resolver=lambda _port: tmp_path / "examples" / "allowed_agent.py",
    )
    client = TestClient(app)

    response = client.get("/missing/v1/test")

    assert response.status_code == 404


def test_allowed_enrolled_caller_reaches_mock_provider(tmp_path: Path):
    script = tmp_path / "examples" / "allowed_agent.py"
    script.parent.mkdir()
    script.write_text("print('allowed')\n", encoding="utf-8")
    lock_path = tmp_path / "zero-env.lock"
    enroll_file(script, lock_path=lock_path, project_root=tmp_path)
    app = create_app(
        config=make_config(tmp_path),
        lock_path=lock_path,
        caller_resolver=lambda _port: script,
    )
    client = TestClient(app)

    response = client.post("/mockai/v1/chat/completions", json={"messages": []})

    assert response.status_code == 200
    assert response.json()["provider"] == "mockai"


def test_blocked_caller_returns_403(tmp_path: Path):
    script = tmp_path / "examples" / "blocked_agent.py"
    script.parent.mkdir()
    script.write_text("print('blocked')\n", encoding="utf-8")
    lock_path = tmp_path / "zero-env.lock"
    enroll_file(script, lock_path=lock_path, project_root=tmp_path)
    app = create_app(
        config=make_config(tmp_path),
        lock_path=lock_path,
        caller_resolver=lambda _port: script,
    )
    client = TestClient(app)

    response = client.post("/mockai/v1/chat/completions", json={"messages": []})

    assert response.status_code == 403
    assert "not allowed" in response.json()["detail"]


def test_tampered_caller_returns_403(tmp_path: Path):
    script = tmp_path / "examples" / "allowed_agent.py"
    script.parent.mkdir()
    script.write_text("print('allowed')\n", encoding="utf-8")
    lock_path = tmp_path / "zero-env.lock"
    enroll_file(script, lock_path=lock_path, project_root=tmp_path)
    script.write_text("print('tampered')\n", encoding="utf-8")
    app = create_app(
        config=make_config(tmp_path),
        lock_path=lock_path,
        caller_resolver=lambda _port: script,
    )
    client = TestClient(app)

    response = client.post("/mockai/v1/chat/completions", json={"messages": []})

    assert response.status_code == 403
    assert "hash mismatch" in response.json()["detail"]
```

- [ ] **Step 2: Run failing tests**

Run: `python3 -m pytest tests/test_gateway.py -v`

Expected: FAIL because `zero_env_proxy.gateway` does not exist.

- [ ] **Step 3: Implement gateway**

Create `zero_env_proxy/gateway.py`:

```python
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
            raise HTTPException(status_code=403, detail=f"Caller not allowed for service: {caller_display}")

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
                raise HTTPException(status_code=500, detail=f"Missing required secret env: {service.api_key_env}")
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
```

- [ ] **Step 4: Run gateway tests**

Run: `python3 -m pytest tests/test_gateway.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add zero_env_proxy/gateway.py tests/test_gateway.py
git commit -m "feat: add governed gateway"
```

### Task 7: CLI And Examples

**Files:**
- Create: `zero_env_proxy/cli.py`
- Create: `examples/allowed_agent.py`
- Create: `examples/blocked_agent.py`
- Create: `examples/tamper_demo.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write CLI smoke tests**

Create `tests/test_cli.py`:

```python
from pathlib import Path

from zero_env_proxy.cli import main


def test_inspect_lock_reports_missing_lock(tmp_path: Path, capsys):
    exit_code = main(["inspect-lock", "--lock", str(tmp_path / "zero-env.lock")])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Lockfile not found" in captured.out
```

- [ ] **Step 2: Run failing CLI tests**

Run: `python3 -m pytest tests/test_cli.py -v`

Expected: FAIL because `zero_env_proxy.cli` does not exist.

- [ ] **Step 3: Implement CLI**

Create `zero_env_proxy/cli.py`:

```python
from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
import sys

import uvicorn

from zero_env_proxy.config import ConfigError, load_config
from zero_env_proxy.gateway import create_app
from zero_env_proxy.lockfile import LockError, enroll_file, load_lockfile


DEFAULT_CONFIG = """proxy:
  host: "127.0.0.1"
  port: 5050

services:
  mockai:
    provider: "mock"
    target_url: "mock://local"
    allowed_files:
      - "examples/allowed_agent.py"
"""


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(prog="zero-env")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init")
    init.add_argument("--target", default="zero-env.yaml")

    enroll = sub.add_parser("enroll")
    enroll.add_argument("path")
    enroll.add_argument("--config", default="zero-env.yaml")
    enroll.add_argument("--lock", default="zero-env.lock")

    serve = sub.add_parser("serve")
    serve.add_argument("--config", default="zero-env.yaml")
    serve.add_argument("--lock", default="zero-env.lock")

    demo = sub.add_parser("demo")
    demo.add_argument("--python", default=sys.executable)

    inspect = sub.add_parser("inspect-lock")
    inspect.add_argument("--lock", default="zero-env.lock")

    return parser


def cmd_init(target: str) -> int:
    destination = Path(target)
    if destination.exists():
        print(f"Refusing to overwrite existing config: {destination}")
        return 1
    destination.write_text(DEFAULT_CONFIG, encoding="utf-8")
    print(f"Created {destination}")
    return 0


def cmd_enroll(path: str, config_path: str, lock_path: str) -> int:
    try:
        config = load_config(config_path)
        record = enroll_file(path, lock_path=lock_path, project_root=config.root)
    except (ConfigError, LockError) as exc:
        print(str(exc))
        return 1
    print(f"Enrolled {record.display_path} [{record.sha256[:12]}]")
    return 0


def cmd_serve(config_path: str, lock_path: str) -> int:
    try:
        config = load_config(config_path)
    except ConfigError as exc:
        print(str(exc))
        return 1
    app = create_app(config=config, lock_path=lock_path)
    uvicorn.run(app, host=config.proxy.host, port=config.proxy.port)
    return 0


def cmd_inspect_lock(lock_path: str) -> int:
    try:
        lock = load_lockfile(lock_path)
    except LockError as exc:
        print(str(exc))
        return 1
    for record in lock.files.values():
        print(f"{record.display_path} {record.sha256[:12]} size={record.size}")
    return 0


def cmd_demo(python_bin: str) -> int:
    print("Zero-Env demo uses two terminals in normal use.")
    print("Run: zero-env init")
    print("Run: zero-env enroll examples/allowed_agent.py")
    print("Run: zero-env serve")
    print("Then run the example agents against http://127.0.0.1:5050/mockai/v1/chat/completions")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "init":
        return cmd_init(args.target)
    if args.command == "enroll":
        return cmd_enroll(args.path, args.config, args.lock)
    if args.command == "serve":
        return cmd_serve(args.config, args.lock)
    if args.command == "demo":
        return cmd_demo(args.python)
    if args.command == "inspect-lock":
        return cmd_inspect_lock(args.lock)
    parser.error("Unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Add example agents**

Create `examples/allowed_agent.py`:

```python
from __future__ import annotations

import json
import urllib.request


def main() -> int:
    payload = json.dumps({"messages": [{"role": "user", "content": "Hello from an approved worker."}]}).encode()
    request = urllib.request.Request(
        "http://127.0.0.1:5050/mockai/v1/chat/completions",
        data=payload,
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        print(response.read().decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Create `examples/blocked_agent.py`:

```python
from examples.allowed_agent import main


if __name__ == "__main__":
    raise SystemExit(main())
```

Create `examples/tamper_demo.py`:

```python
from __future__ import annotations

from pathlib import Path


def main() -> int:
    target = Path("examples/allowed_agent.py")
    original = target.read_text(encoding="utf-8")
    marker = "\n# tampered after enrollment\n"
    if marker not in original:
        target.write_text(original + marker, encoding="utf-8")
        print("Tampered examples/allowed_agent.py. Re-run it to see the proxy reject the changed hash.")
    else:
        print("Tamper marker already present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run CLI tests**

Run: `python3 -m pytest tests/test_cli.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```bash
git add zero_env_proxy/cli.py examples/allowed_agent.py examples/blocked_agent.py examples/tamper_demo.py tests/test_cli.py
git commit -m "feat: add cli and demo agents"
```

### Task 8: README And Phase B Gate

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write README**

Create `README.md`:

```markdown
# Zero-Env Proxy

A small local credential proxy for automation scripts.

Zero-Env Proxy lets approved worker files call configured services through a governed localhost gateway, keeping provider credentials out of the worker script itself.

## Why This Exists

Most secret tooling focuses on storage, rotation, and access to the secret. Zero-Env Proxy focuses on local credential use: allowing an approved automation file to call a service without handing that file the provider credential.

## What This Proves

- A worker script can call a service without containing the real provider key.
- A localhost proxy can enforce file enrollment before forwarding a request.
- A lockfile can detect when an enrolled worker changed after enrollment.
- A small developer utility can make the runtime credential boundary visible and testable.

## What This Does Not Claim

- It is not an org-wide secrets vault.
- It does not provide cryptographic process identity.
- It does not eliminate every local secret in every deployment shape.
- It does not claim enterprise platform scope.

## Quickstart

```bash
python3 -m pip install -e ".[dev]"
zero-env init
zero-env enroll examples/allowed_agent.py
zero-env serve
```

In another terminal:

```bash
python3 examples/allowed_agent.py
python3 examples/blocked_agent.py
python3 examples/tamper_demo.py
python3 examples/allowed_agent.py
```

Expected behavior:

- `allowed_agent.py` reaches the mock provider.
- `blocked_agent.py` receives `403`.
- after `tamper_demo.py`, `allowed_agent.py` receives `403` until re-enrolled.

## Runtime Boundary

Zero-Env Proxy focuses on the runtime boundary after a credential exists: keeping provider keys out of worker scripts while routing approved calls through a local policy gate.

## Tests

```bash
python3 -m pytest -v
```

## Optional Real Provider Mode

The public demo uses `mockai` by default and needs no API key. A real provider can be configured with `provider: "http"` and `api_key_env`, so only the proxy process receives the provider credential.
```

- [ ] **Step 2: Run Phase B tests**

Run: `python3 -m pytest -v`

Expected: PASS.

- [ ] **Step 3: Scan public claims**

Run: `rg -n "proof-of-concept|production-hardened|enterprise-ready|prevents code injection|eliminates all secrets" README.md pyproject.toml`

Expected: no matches except acceptable negative-boundary wording if added deliberately.

- [ ] **Step 4: Commit**

Run:

```bash
git add README.md
git commit -m "docs: explain zero-env proxy boundary"
```

## Phase C Tasks

### Task 9: Installable CLI Verification

**Files:**
- Modify: `pyproject.toml`
- Modify: `zero_env_proxy/cli.py`
- Create: `scripts/verify_wheel.py`

- [ ] **Step 1: Verify console command in editable mode**

Run: `python3 -m pip install -e ".[dev]"`

Expected: package installs and exposes `zero-env`.

- [ ] **Step 2: Verify help command**

Run: `zero-env --help`

Expected: command list includes `init`, `enroll`, `serve`, `demo`, and `inspect-lock`.

- [ ] **Step 3: Add wheel verifier**

Create `scripts/verify_wheel.py`:

```python
from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile
import sys


REQUIRED_SUFFIXES = [
    "zero_env_proxy/__init__.py",
    "zero_env_proxy/cli.py",
    "zero_env_proxy/config.py",
    "zero_env_proxy/gateway.py",
    "zero_env_proxy/identity.py",
    "zero_env_proxy/lockfile.py",
    "zero_env_proxy/providers.py",
    "entry_points.txt",
]


def main(path: str) -> int:
    wheel = Path(path)
    with ZipFile(wheel) as archive:
        names = archive.namelist()
    missing = [suffix for suffix in REQUIRED_SUFFIXES if not any(name.endswith(suffix) for name in names)]
    if missing:
        print("Missing from wheel:")
        for item in missing:
            print(f"- {item}")
        return 1
    print(f"Wheel verified: {wheel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
```

- [ ] **Step 4: Build wheel**

Run: `python3 -m build`

Expected: `dist/zero_env_proxy-0.1.0-py3-none-any.whl` is created.

- [ ] **Step 5: Verify wheel**

Run: `python3 scripts/verify_wheel.py dist/zero_env_proxy-0.1.0-py3-none-any.whl`

Expected: `Wheel verified`.

- [ ] **Step 6: Commit**

Run:

```bash
git add pyproject.toml zero_env_proxy/cli.py scripts/verify_wheel.py
git commit -m "chore: verify installable cli package"
```

### Task 10: Final Gate And Public Shelf Check

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Run full tests**

Run: `python3 -m pytest -v`

Expected: PASS.

- [ ] **Step 2: Run CLI smoke**

Run:

```bash
zero-env --help
zero-env inspect-lock
```

Expected: help prints successfully; inspect-lock returns a clear missing-lock message when no lock exists.

- [ ] **Step 3: Run claim scan**

Run: `rg -n "proof-of-concept|production-hardened|enterprise-ready|prevents code injection|eliminates all secrets|org-wide secrets vault" README.md pyproject.toml zero_env_proxy`

Expected: only allowed negative-boundary mentions of `org-wide secrets vault`; no weak headline framing or inflated platform claims.

- [ ] **Step 4: Add final README status**

Add a short `Status` section to `README.md`:

```markdown
## Status

Zero-Env Proxy is a small public field kit for local automation credential boundaries. The default demo uses a mock provider so the repo can be cloned, tested, and reviewed without private keys.
```

- [ ] **Step 5: Commit**

Run:

```bash
git add README.md
git commit -m "docs: add public field-kit status"
```

## Self-Review Checklist

- Spec coverage: Phase B and Phase C both have task coverage.
- Unit27 gate: README, tests, public claim scan, and mock demo are explicit tasks.
- Karpathy gate: clone-run-test behavior, CLI commands, modular code, and wheel verification are explicit tasks.
- No private Desk context is required by the planned repo.
- No real secret belongs in source control.
- The worker remains the zero-env party in the main story; optional real-provider mode keeps credentials at the proxy boundary.

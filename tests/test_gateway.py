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

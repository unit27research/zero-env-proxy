from pathlib import Path

import psutil
import pytest

import zero_env_proxy.identity as identity
from zero_env_proxy.identity import extract_python_script_path


def test_extract_python_script_path_prefers_py_file(tmp_path: Path):
    script = tmp_path / "agent.py"
    script.write_text("print('ok')\n", encoding="utf-8")

    result = extract_python_script_path(["python", str(script)])

    assert result == script.resolve()


def test_extract_python_script_path_returns_none_without_script():
    assert extract_python_script_path(["python", "-m", "module"]) is None


def test_resolve_caller_converts_net_connections_access_denied(monkeypatch):
    def deny_process_iter(attrs=None):
        raise psutil.AccessDenied(pid=123)

    monkeypatch.setattr(identity.psutil, "process_iter", deny_process_iter)

    with pytest.raises(identity.IdentityError, match="Could not inspect network connections"):
        identity.resolve_caller_from_client_port(5050)


def test_resolve_caller_matches_client_local_port(monkeypatch, tmp_path: Path):
    script = tmp_path / "agent.py"
    script.write_text("print('ok')\n", encoding="utf-8")

    class Addr:
        def __init__(self, port: int):
            self.port = port

    class Conn:
        laddr = Addr(49307)
        raddr = Addr(5050)

    class Proc:
        pid = 99

        def net_connections(self, kind: str):
            return [Conn()]

        def cmdline(self):
            return ["python", str(script)]

    monkeypatch.setattr(identity.psutil, "process_iter", lambda attrs=None: [Proc()])

    assert identity.resolve_caller_from_client_port(49307) == script.resolve()

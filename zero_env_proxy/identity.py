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

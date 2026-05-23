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
    try:
        processes = list(psutil.process_iter(["pid"]))
    except psutil.AccessDenied as exc:
        raise IdentityError("Could not inspect network connections for caller identity") from exc

    for process in processes:
        try:
            connections = process.net_connections(kind="inet")
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            continue
        for conn in connections:
            if not conn.laddr or conn.laddr.port != client_port:
                continue
            try:
                script_path = extract_python_script_path(process.cmdline())
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                continue
            if script_path is not None:
                return script_path
    raise IdentityError(f"Could not resolve caller for client port {client_port}")

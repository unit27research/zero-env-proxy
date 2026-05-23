from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

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
        if not isinstance(allowed_files, list) or not all(
            isinstance(item, str) for item in allowed_files
        ):
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

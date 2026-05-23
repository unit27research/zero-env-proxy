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

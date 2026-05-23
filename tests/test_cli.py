from pathlib import Path

from zero_env_proxy.cli import main


def test_inspect_lock_reports_missing_lock(tmp_path: Path, capsys):
    exit_code = main(["inspect-lock", "--lock", str(tmp_path / "zero-env.lock")])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Lockfile not found" in captured.out

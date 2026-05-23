from pathlib import Path

from zero_env_proxy.cli import main


def test_inspect_lock_reports_missing_lock(tmp_path: Path, capsys):
    exit_code = main(["inspect-lock", "--lock", str(tmp_path / "zero-env.lock")])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Lockfile not found" in captured.out


def test_demo_runs_allowed_blocked_and_tampered_checks(capsys):
    exit_code = main(["demo"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "PASS allowed worker reached mock provider" in captured.out
    assert "PASS blocked worker received 403" in captured.out
    assert "PASS tampered worker received 403" in captured.out

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

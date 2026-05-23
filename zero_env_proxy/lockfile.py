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
        "files": {
            file_path: asdict(record)
            for file_path, record in lockfile.files.items()
        },
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

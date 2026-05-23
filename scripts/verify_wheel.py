from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile
import sys


REQUIRED_SUFFIXES = [
    "zero_env_proxy/__init__.py",
    "zero_env_proxy/cli.py",
    "zero_env_proxy/config.py",
    "zero_env_proxy/gateway.py",
    "zero_env_proxy/identity.py",
    "zero_env_proxy/lockfile.py",
    "zero_env_proxy/providers.py",
    "entry_points.txt",
]


def main(path: str) -> int:
    wheel = Path(path)
    with ZipFile(wheel) as archive:
        names = archive.namelist()
    missing = [
        suffix
        for suffix in REQUIRED_SUFFIXES
        if not any(name.endswith(suffix) for name in names)
    ]
    if missing:
        print("Missing from wheel:")
        for item in missing:
            print(f"- {item}")
        return 1
    print(f"Wheel verified: {wheel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))

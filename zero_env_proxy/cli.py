from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
import sys

import uvicorn

from zero_env_proxy.config import ConfigError, load_config
from zero_env_proxy.gateway import create_app
from zero_env_proxy.lockfile import LockError, enroll_file, load_lockfile


DEFAULT_CONFIG = """proxy:
  host: "127.0.0.1"
  port: 5050

services:
  mockai:
    provider: "mock"
    target_url: "mock://local"
    allowed_files:
      - "examples/allowed_agent.py"
"""


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(prog="zero-env")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init")
    init.add_argument("--target", default="zero-env.yaml")

    enroll = sub.add_parser("enroll")
    enroll.add_argument("path")
    enroll.add_argument("--config", default="zero-env.yaml")
    enroll.add_argument("--lock", default="zero-env.lock")

    serve = sub.add_parser("serve")
    serve.add_argument("--config", default="zero-env.yaml")
    serve.add_argument("--lock", default="zero-env.lock")

    demo = sub.add_parser("demo")
    demo.add_argument("--python", default=sys.executable)

    inspect = sub.add_parser("inspect-lock")
    inspect.add_argument("--lock", default="zero-env.lock")

    return parser


def cmd_init(target: str) -> int:
    destination = Path(target)
    if destination.exists():
        print(f"Refusing to overwrite existing config: {destination}")
        return 1
    destination.write_text(DEFAULT_CONFIG, encoding="utf-8")
    print(f"Created {destination}")
    return 0


def cmd_enroll(path: str, config_path: str, lock_path: str) -> int:
    try:
        config = load_config(config_path)
        record = enroll_file(path, lock_path=lock_path, project_root=config.root)
    except (ConfigError, LockError) as exc:
        print(str(exc))
        return 1
    print(f"Enrolled {record.display_path} [{record.sha256[:12]}]")
    return 0


def cmd_serve(config_path: str, lock_path: str) -> int:
    try:
        config = load_config(config_path)
    except ConfigError as exc:
        print(str(exc))
        return 1
    app = create_app(config=config, lock_path=lock_path)
    uvicorn.run(app, host=config.proxy.host, port=config.proxy.port)
    return 0


def cmd_inspect_lock(lock_path: str) -> int:
    try:
        lock = load_lockfile(lock_path)
    except LockError as exc:
        print(str(exc))
        return 1
    for record in lock.files.values():
        print(f"{record.display_path} {record.sha256[:12]} size={record.size}")
    return 0


def cmd_demo(python_bin: str) -> int:
    print("Zero-Env demo uses two terminals in normal use.")
    print("Run: zero-env init")
    print("Run: zero-env enroll examples/allowed_agent.py")
    print("Run: zero-env serve")
    print("Then run the example agents against http://127.0.0.1:5050/mockai/v1/chat/completions")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "init":
        return cmd_init(args.target)
    if args.command == "enroll":
        return cmd_enroll(args.path, args.config, args.lock)
    if args.command == "serve":
        return cmd_serve(args.config, args.lock)
    if args.command == "demo":
        return cmd_demo(args.python)
    if args.command == "inspect-lock":
        return cmd_inspect_lock(args.lock)
    parser.error("Unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

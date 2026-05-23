from __future__ import annotations

from pathlib import Path


def main() -> int:
    target = Path("examples/allowed_agent.py")
    original = target.read_text(encoding="utf-8")
    marker = "\n# tampered after enrollment\n"
    if marker not in original:
        target.write_text(original + marker, encoding="utf-8")
        print("Tampered examples/allowed_agent.py. Re-run it to see the proxy reject the changed hash.")
    else:
        print("Tamper marker already present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

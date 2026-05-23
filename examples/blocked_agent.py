from __future__ import annotations

import json
import urllib.request


def main() -> int:
    payload = json.dumps(
        {"messages": [{"role": "user", "content": "Hello from an unapproved worker."}]}
    ).encode()
    request = urllib.request.Request(
        "http://127.0.0.1:5050/mockai/v1/chat/completions",
        data=payload,
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        print(response.read().decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

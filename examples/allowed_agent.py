from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
import urllib.request


def print_http_error(label: str, error: HTTPError) -> None:
    detail = error.reason
    if error.fp is not None:
        try:
            payload = json.loads(error.fp.read().decode())
            detail = payload.get("detail", detail)
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
    print(f"{label}: {error.code} {detail}")


def main() -> int:
    payload = json.dumps(
        {"messages": [{"role": "user", "content": "Hello from an approved worker."}]}
    ).encode()
    request = urllib.request.Request(
        "http://127.0.0.1:5050/mockai/v1/chat/completions",
        data=payload,
        headers={"content-type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            print(response.read().decode())
        return 0
    except HTTPError as exc:
        print_http_error("DENIED", exc)
        return 1
    except URLError as exc:
        print(f"FAILED: {exc.reason}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

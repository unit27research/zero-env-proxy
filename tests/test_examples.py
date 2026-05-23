from __future__ import annotations

from io import BytesIO
from urllib.error import HTTPError

import examples.blocked_agent as blocked_agent


def test_blocked_agent_prints_clean_http_error(monkeypatch, capsys):
    error = HTTPError(
        url="http://127.0.0.1:5050/mockai/v1/chat/completions",
        code=403,
        msg="Forbidden",
        hdrs={},
        fp=BytesIO(b'{"detail":"Caller not allowed for service: examples/blocked_agent.py"}'),
    )
    monkeypatch.setattr(blocked_agent.urllib.request, "urlopen", lambda request, timeout: (_ for _ in ()).throw(error))

    exit_code = blocked_agent.main()

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "BLOCKED: 403 Caller not allowed for service: examples/blocked_agent.py" in captured.out
    assert "Traceback" not in captured.err

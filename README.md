# Zero-Env Proxy

A small local credential proxy for automation scripts.

Zero-Env Proxy lets approved worker files call configured services through a governed localhost gateway, keeping provider credentials out of the worker script itself.

## Release Status

`SOURCE_STATUS: PUBLIC_PACKAGE`
`ACCESS_STATUS: CLEARED_FOR_EXTERNAL_USE`
`UNIT27_POSITION: ADJACENT_RUNTIME_BOUNDARY_UTILITY`

This repository is a released Unit27 public utility: visible, inspectable, and intended for orientation, testing, and practical use. Controlled protocol materials remain outside this source package.

It answers one narrow question:

> Can a local automation worker call a provider without receiving the provider credential directly?

## Why This Exists

Most secret tooling focuses on storage, rotation, and access to the secret. Zero-Env Proxy focuses on local credential use: allowing an approved automation file to call a service without handing that file the provider credential.

## What This Proves

- A worker script can call a service without containing the real provider key.
- A localhost proxy can enforce file enrollment before forwarding a request.
- A lockfile can detect when an enrolled worker changed after enrollment.
- A small developer utility can make the runtime credential boundary visible and testable.

## What This Does Not Claim

- It is not an org-wide secrets vault.
- It does not provide cryptographic process identity.
- It does not eliminate every local secret in every deployment shape.
- It does not claim enterprise platform scope.

## Quickstart

```bash
python3 -m pip install -e ".[dev]"
zero-env demo
```

For the manual two-terminal route:

```bash
zero-env init
zero-env enroll examples/allowed_agent.py
zero-env serve
```

In another terminal:

```bash
python3 examples/allowed_agent.py
python3 examples/blocked_agent.py
python3 examples/tamper_demo.py
python3 examples/allowed_agent.py
```

Expected behavior:

- `allowed_agent.py` reaches the mock provider.
- `blocked_agent.py` receives `403`.
- after `tamper_demo.py`, `allowed_agent.py` receives `403` until re-enrolled.

## Runtime Boundary

Zero-Env Proxy focuses on the runtime boundary after a credential exists: keeping provider keys out of worker scripts while routing approved calls through a local policy gate.

## Where It Fits

Zero-Env Proxy is not part of the Unit27 Field Kit Suite operating sequence. It sits beside that chain as an adjacent runtime-boundary utility for local automation work.

Use it when the work already has a credential but the worker file should remain credential-blind.

## Status

Zero-Env Proxy is a small public utility for local automation credential boundaries. The default demo uses a mock provider so the repo can be cloned, tested, and reviewed without private keys.

## Architecture

```text
worker script -> localhost proxy -> configured provider
                 |
                 +-- service allowlist
                 +-- canonical file enrollment
                 +-- hash verification
                 +-- credential injection
```

## Command Reference

```bash
zero-env init
zero-env enroll examples/allowed_agent.py
zero-env serve
zero-env inspect-lock
zero-env demo
```

## Demo Transcript

```text
$ zero-env demo
PASS allowed worker reached mock provider
PASS blocked worker received 403
PASS tampered worker received 403
```

Manual route:

```text
$ zero-env enroll examples/allowed_agent.py
Enrolled examples/allowed_agent.py [short-hash]

$ python3 examples/allowed_agent.py
{"provider":"mockai", ...}

$ python3 examples/blocked_agent.py
BLOCKED: 403 Caller not allowed for service: examples/blocked_agent.py

$ python3 examples/tamper_demo.py
Tampered examples/allowed_agent.py. Re-run it to see the proxy reject the changed hash.

$ python3 examples/allowed_agent.py
DENIED: 403 File hash mismatch for examples/allowed_agent.py
```

## Tests

```bash
python3 -m pytest -v
```

## Optional Real Provider Mode

The public demo uses `mockai` by default and needs no API key. A real provider can be configured with `provider: "http"` and `api_key_env`, so only the proxy process receives the provider credential.

# Zero-Env Proxy Design

Date: 2026-05-23
Status: Draft awaiting user review
Target repo: `zero-env-proxy`
Public name: Zero-Env Proxy

## Purpose

Zero-Env Proxy is a public Unit27-style proof build: a small local developer utility that demonstrates credential isolation and runtime allowlisting for automation scripts.

It is not a production security product. Its purpose is to show real building ability in a shareable artifact: backend routing, FastAPI design, local process inspection, file integrity tracking, testable demos, clear boundaries, and honest documentation.

## Public Claim

Allowed claim:

> Zero-Env Proxy is a small local credential proxy for automation scripts. It lets approved worker files call configured services through a governed localhost gateway, keeping provider credentials out of the worker script itself.

Boundary language:

> Most secret tooling focuses on storage, rotation, and access to the secret. Zero-Env Proxy focuses on local credential use: allowing an approved automation file to call a service without handing that file the provider credential.

Secondary boundary:

> Zero-Env Proxy is not an org-wide secrets vault. It focuses on the runtime boundary after a credential exists: keeping provider keys out of worker scripts while routing approved calls through a local policy gate.

Blocked claims:

- Production security system.
- Complete secret elimination.
- Cryptographic process identity.
- Code-injection prevention.
- Enterprise-ready credential platform.

## Phase Strategy

### Phase B: Public Field-Kit Build

Phase B is the first deliverable. It should be cloneable, runnable, testable, and understandable in under five minutes.

Completion rule:

> A reviewer can clone the repo, run the mock demo, see allowed, blocked, and tampered behavior, and understand what the project proves without needing private Desk context or a real API key.

### Phase C: Installable CLI Tool

Phase C comes after Phase B works. It keeps the same internals but exposes a cleaner command surface:

```bash
zero-env init
zero-env enroll examples/allowed_agent.py
zero-env serve
zero-env demo
zero-env inspect-lock
```

The Phase B code should already be organized like a package so Phase C is a packaging and UX graduation, not a rewrite.

## Architecture

```text
zero-env-proxy/
├── README.md
├── pyproject.toml
├── .gitignore
├── zero_env_proxy/
│   ├── __init__.py
│   ├── cli.py
│   ├── config.py
│   ├── gateway.py
│   ├── identity.py
│   ├── lockfile.py
│   └── providers.py
├── examples/
│   ├── zero-env.yaml.example
│   ├── allowed_agent.py
│   ├── blocked_agent.py
│   └── tamper_demo.py
└── tests/
    ├── test_config.py
    ├── test_gateway.py
    ├── test_identity.py
    └── test_lockfile.py
```

## Components

### Config

`config.py` loads and validates `zero-env.yaml`.

The public repo ships `examples/zero-env.yaml.example`, not a real credential file.

For demos, the default provider is mock-only:

```yaml
proxy:
  host: "127.0.0.1"
  port: 5050

services:
  mockai:
    provider: "mock"
    target_url: "mock://local"
    allowed_files:
      - "examples/allowed_agent.py"
```

Optional real-provider mode can be documented, but it must read secrets from an ignored local source such as `.env.local`, shell environment, or platform keychain. No real key belongs in YAML.

### Lockfile

`lockfile.py` owns enrollment and verification.

The lockfile is not generated automatically on server boot. It is generated intentionally through enrollment.

Each enrolled file record includes:

- canonical absolute path
- relative display path
- SHA-256 hash
- file size
- modified timestamp
- enrolled timestamp

Verification fails if:

- the caller path is absent from the lockfile
- the current hash differs
- the file no longer exists
- the lockfile is missing
- the resolved path differs from the enrolled canonical path

### Identity

`identity.py` resolves the local process connecting to the proxy.

Phase B can keep the `psutil` client-port lookup, but it must return a canonical script path, not only a basename.

The code should treat this identity method as a local proof mechanism, not a cryptographic trust anchor. The README must say that explicitly.

### Gateway

`gateway.py` exposes the FastAPI route:

```text
/{service_name}/{path:path}
```

Responsibilities:

- reject unknown services
- resolve caller identity
- verify caller against the lockfile
- enforce service allowlist
- inject provider credential only inside the proxy
- forward method, query params, body, and safe headers
- preserve upstream status code and response media type when possible

### Providers

`providers.py` separates mock behavior from real HTTP forwarding.

Mock provider mode returns deterministic JSON so tests and demos run without network access or API keys.

Real provider mode uses `httpx` and is optional for the public proof.

### CLI

Phase B may expose basic commands through `python -m zero_env_proxy.cli`.

Phase C promotes them to the installed `zero-env` command.

Target commands:

- `init`: create local config from example
- `enroll <path>`: add or refresh a script in the lockfile
- `serve`: run the proxy
- `demo`: run the allowed, blocked, and tampered examples
- `inspect-lock`: print enrolled files and short hashes

## Security Gap Handling

### Real keys in YAML

Original gap: the pasted spec stored the provider API key directly in `zero-env.yaml`.

Resolution: public config uses mock mode. Real provider mode references an external local secret source and keeps secret files ignored by git.

### Basename spoofing

Original gap: `allowed_files` checked only `my_automation_agent.py`.

Resolution: enrollment stores canonical absolute paths. Runtime verification compares resolved paths, not only filenames.

### Auto-blessing tampered files

Original gap: the lockfile was generated on proxy boot.

Resolution: lockfile generation moves to explicit enrollment. Server boot refuses to run protected routes without an existing lockfile.

### Path confusion

Original gap: hashing used the caller filename instead of the resolved process path.

Resolution: hashing uses the canonical enrolled path and compares it with the resolved runtime caller path.

### Brittle process identity

Original gap: `psutil.net_connections()` plus client port is useful but not a hardened identity model.

Resolution: keep it for local proof purposes, document the trust boundary, and write tests around expected local behavior. Do not claim stronger identity than the mechanism provides.

### Proxy response correctness

Original gap: response streaming did not preserve upstream status codes and headers cleanly.

Resolution: gateway returns status code and media type from upstream where possible. Hop-by-hop headers are stripped.

## Demo Flow

The public demo should show:

1. Initialize config.
2. Enroll `examples/allowed_agent.py`.
3. Start the proxy in mock mode.
4. Run allowed agent and receive a mock completion.
5. Run blocked agent and receive `403`.
6. Modify or use the tamper demo and receive a tamper failure.
7. Inspect the lockfile and see the recorded proof metadata.

The README should include a short terminal transcript of this flow.

## Tests

Required Phase B tests:

- config loads valid mock config
- config rejects missing service fields
- enrollment writes canonical path and hash
- verification passes for unchanged enrolled file
- verification fails after content change
- verification fails for same basename in a different path
- unknown service returns 404
- blocked caller returns 403
- tampered caller returns 403
- mock provider returns deterministic JSON
- gateway preserves response status behavior for mock errors

Required Phase C tests:

- package installs in editable mode
- `zero-env --help` works
- `zero-env init` creates expected local files
- `zero-env enroll` writes lockfile
- `zero-env demo` exits successfully
- wheel includes package files and examples needed for demo

## Unit27 Test

Zero-Env Proxy passes the Unit27 test only if:

- It fills a real operational gap: automation scripts should not directly handle raw provider credentials.
- It has a narrow public claim and does not inflate into a platform story.
- It ships proof artifacts: tests, demo transcript, example config, and lockfile behavior.
- It is shareable without private Desk, job-search, or client context.
- It has clear negative boundaries in the README.
- It is small enough to inspect and credible enough to discuss.
- It fits the public field-kit shelf better than a private product demo.

Failure condition:

> If the repo needs private explanation to make sense, or if its value depends on calling it production security, it fails Unit27.

## Karpathy Test

For this project, the Karpathy test means the repo must work well in the AI-assisted coding world: intent-first, runnable, inspectable, and empirically verifiable.

Zero-Env Proxy passes the Karpathy test only if:

- A coding agent or human reviewer can infer the project purpose from the README quickly.
- The demo can be run from commands, not by manually stitching files together.
- The test suite verifies the core behavior instead of trusting the narrative.
- The code is modular enough for an agent to modify one part without loading the whole system.
- Errors are concrete enough to paste back into an agent loop and fix.
- The repo includes realistic examples, not only toy prose.
- The project can be iterated through measurable checks: tests, demo exit codes, and expected terminal output.

Failure condition:

> If it is only impressive as a pasted prompt/spec and not as a clone-run-test artifact, it fails Karpathy.

## README Requirements

The README must include:

- short project description
- quickstart mock demo
- what this proves
- what this does not claim
- threat boundary
- architecture
- command reference
- demo transcript
- tests
- optional real-provider setup

## Release Gate

Phase B is releasable when:

- tests pass
- mock demo works
- README claim boundary is clear
- no real secrets exist in the repo
- same-basename spoof test fails correctly
- tamper demo fails correctly
- public-facing README and package metadata frame the project as a real small developer utility focused on runtime credential use, not as an org-wide vault or enterprise platform
- public-facing README and package metadata avoid overclaiming phrases such as production security, enterprise-ready, prevents code injection, or eliminates all secrets, except when explicitly naming blocked claims

Phase C is releasable when:

- Phase B remains green
- CLI commands work through installed package entry points
- wheel verification passes
- README quickstart uses `zero-env` commands instead of module paths

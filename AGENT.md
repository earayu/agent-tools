# Agent Workflow

Read this file before doing project work with `agent-tools`.

## Purpose

This repository defines reusable tooling and workflows for development agents.
Use it to avoid ad-hoc commands for repeated operations.

## Operating Rules

- Prefer just recipes over hand-written command sequences.
- Prefer scripts in `scripts/` over direct GitHub API calls.
- Prefer local repository state over remote API reads.
- Cache read-only remote calls with a clear TTL.
- Keep command output concise unless a human asks for full logs.
- Put repeatable process knowledge in `.agent/skills/`.
- Do not store secrets, tokens, raw issue bodies, or full CI logs in cache.

## Common Commands

```bash
just --list
just gh-rate-limit
just gh-ci-runs <workflow.yml> "" 5
just gh-ci-run <actions-run-id>
just gh-pr <pull-request-number>
just gh-file <repo-file> origin/main
```

## Adding Tools

Add new tools under a scenario directory:

```text
scripts/github/
scripts/project/
scripts/test/
scripts/deploy/
scripts/debug/
```

For each new workflow:

- add a stable just recipe
- document it in `README.md`
- add or update a skill under `.agent/skills/` if agents need procedural rules
- make the default output short enough to paste into chat

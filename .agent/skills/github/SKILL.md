---
name: github-agent-tools
description: Use agent-tools GitHub wrappers for frequent GitHub operations before generating direct gh commands.
---

# GitHub Agent Tools

Use this skill when an agent needs GitHub context for a project that has
`agent-tools` installed.

## Rules

- Use `just gh-rate-limit` instead of direct `gh api rate_limit`.
- Use `just gh-ci-run <id>` instead of repeated `gh run view`.
- Use `just gh-ci-runs` instead of repeated workflow list polling.
- Use `just gh-pr <number>` before generating custom PR metadata queries.
- Use `just gh-file <path>` before `gh api repos/.../contents/...`.
- Use `--json` on `scripts/github/agent-gh.py` only when the next tool needs
  structured data.

## Escalation

Direct `gh` commands are still acceptable when:

- the wrapper does not cover the operation
- a write operation is required
- full logs are explicitly needed
- the wrapper returns stale data and `--refresh` does not resolve it

When a direct command becomes common, add it to `agent-tools` instead of
copying it between agents.

# Design

`agent-tools` is an agent-facing workflow layer for development projects.

## Problem

Agents often solve recurring development operations by generating new shell
commands every time. This causes several problems:

- repeated GitHub API calls for the same PR, run, file, or rate bucket
- noisy CI logs entering model context
- unstable parsing of command output
- inconsistent merge, rebase, release, and review procedures
- duplicated prompt instructions across projects

## Direction

The project combines:

- configuration for the target project
- `AGENT.md` as the high-level agent workflow entrypoint
- `.agent/skills/` as reusable procedural memory
- `justfile` as a stable command surface
- `scripts/` as implementation details grouped by scenario

## Why Just Plus Scripts

Just recipes are easy for humans and agents to discover through `just --list`.
They provide cleaner arguments than Makefile variables and avoid Makefile
footguns such as `.PHONY`, tab sensitivity, and shell quoting surprises. Python
scripts are better for structured data, caching, JSON, and error handling. The
justfile should stay thin and stable; scripts can evolve underneath it.

## GitHub v0

The first implementation focuses on read-heavy GitHub operations:

- rate limit inspection
- Actions run polling
- recent Actions run lists
- PR context summaries
- repository file reads

All read-heavy commands should support local caching. Write operations such as
comments, reviews, merges, dispatches, and status updates should stay explicit
and uncached.

## Extension Rules

- Add new scenario tools under `scripts/<scenario>/`.
- Add stable just recipes for common commands.
- Add skills when a workflow depends on judgment, sequencing, or safety rules.
- Keep default output short.
- Provide `--json` for automation.
- Never cache secrets or full raw logs by default.

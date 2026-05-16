# Agent Workflow

Read this file before doing project work with `agent-tools`.

## Purpose

This repository defines reusable tooling and workflows for development agents.
Use it to avoid ad-hoc commands for repeated operations.

## First steps in any project

1. Read `agent-tools.yaml` — project name, repo, default branch,
   workdir, commit identity, GitHub policy.
2. Read the skills in `.agent/skills/` — they are decision recipes,
   not docs. Follow them; do not re-derive flows.
3. Use existing `just` recipes before hand-crafting GitHub / CI commands
   (`just --list`). If a recipe does not exist yet, follow the relevant
   skill and add the recipe after the workflow becomes frequent.

## Operating Rules

- Prefer just recipes over hand-written command sequences.
- Prefer scripts in `scripts/` over direct GitHub API calls.
- Prefer local repository state over remote API reads.
- Cache read-only remote calls with a clear TTL.
- Keep command output concise unless a human asks for full logs.
- Put repeatable process knowledge in `.agent/skills/`.
- Do not store secrets, tokens, raw issue bodies, or full CI logs in cache.

## Current command loop

```sh
just --list               # discover supported recipes
just gh-rate-limit        # check shared GitHub API budget
just gh-pr <number>       # inspect PR context through the cached wrapper
just gh-ci-runs           # inspect recent CI runs through the cached wrapper
just gh-ci-run <run-id>   # inspect one CI run through the cached wrapper
```

## Target development loop

The following recipes are the intended next layer. They are not implemented
yet; follow `.agent/skills/dev-flow` manually until the recipes exist.

```sh
just sync                 # fetch + checkout fresh default branch
git checkout -b <branch>  # one change = one branch = one PR
# ... make changes ...
just verify               # local lint / type-check / tests, if defined
just commit "<message>"   # identity + trailer + owner line injected
just pr-new               # push + open PR (templated body)
# CI runs → on red, follow .agent/skills/ci-triage
just pr-merge <n>         # squash + delete-branch when green
```

## Hard rules (enforced via config + skills)

- Commit messages: heredoc only for multi-line / non-ASCII / backticks.
- PR body first line = `identity.pr_owner_line` when set.
- Branch must be caught up with the default branch before merge.
- Never `git config --global`; never push from `main`; never blind
  loop-retry CI (see `.agent/skills/ci-triage`).
- When you i18n a user-facing string, grep contract/snapshot tests
  for the raw string before merging.

## Skills index

- `.agent/skills/github/` — use the GitHub wrappers before raw `gh`.
- `.agent/skills/dev-flow/` — commit identity, branch hygiene, PR/merge
  mechanics, recovery from commit-on-wrong-branch.
- `.agent/skills/ci-triage/` — red-CI decision tree: signal-only log
  fetch, infra-vs-code classification, escalate-don't-loop.

If you hit a flow problem the skills don't cover, fix it HERE (extend
a skill) so the next agent inherits it — the toolbox accumulates the
team's operational memory instead of every agent re-learning by
burning tokens.

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

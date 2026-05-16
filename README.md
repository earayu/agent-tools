# agent-tools

`agent-tools` is a reusable toolbox and workflow definition layer for software
development agents.

It is meant to combine two useful patterns:

- long-lived project memory and workflow guidance (`AGENT.md`, `.agent/skills/`)
- stable command wrappers for frequent operations (`justfile`, `scripts/`)

The goal is to stop agents from repeatedly inventing noisy shell commands for
common work. Stable tools save tokens, reduce GitHub API usage, and make agent
behavior easier to debug.

## Project Layout

```text
agent-tools/
  agent-tools.yaml              # project configuration
  AGENT.md                      # workflow entrypoint for agents
  justfile                      # stable command surface
  .agent/skills/                # reusable agent skills and recipes
    github/SKILL.md
  scripts/
    github/agent-gh.py          # cached GitHub command wrappers
  docs/
    design.md                   # project direction and extension rules
```

## Configure

Edit `agent-tools.yaml` for the project agents are working on:

```yaml
project:
  name: aperag-enterprise
  workdir: /Users/earayu/GitHub/apecloud/aperag-enterprise
github:
  repo: apecloud/aperag-enterprise
  default_branch: main
cache:
  dir: .agent-tools-cache
```

Every command can also be overridden through environment variables such as
`REPO=owner/name`, `WORKDIR=/path/to/repo`, and `CONFIG=/path/to/config.yaml`.

## GitHub Operations

Run bootstrap once to install/check local dependencies:

```bash
sh scripts/project/bootstrap.sh
```

Use just recipes for common read-heavy GitHub operations:

```bash
just gh-rate-limit
just gh-ci-runs release-image.yml "" 5
just gh-ci-run 25954207863
just gh-pr 708
just gh-file .github/workflows/release-image.yml origin/main
```

Direct Python entrypoint:

```bash
scripts/github/agent-gh.py ci-runs --workflow release-image.yml --limit 5
scripts/github/agent-gh.py pr 708 --json
```

The GitHub wrapper:

- uses short TTL caches for read-only GitHub calls
- prefers local `git show` before the GitHub Contents API
- returns concise summaries by default
- supports `--json` where structured output is useful
- never caches write operations

## First Backlog

- CI run polling cache and summary
- PR context cache and summary
- GitHub rate bucket summary
- repository file reads through local git first, Contents API second
- failed CI log extraction into a short root-cause summary
- merge/rebase/release recipes as agent skills

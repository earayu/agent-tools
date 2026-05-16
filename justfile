set positional-arguments
set quiet

config := env_var_or_default("CONFIG", "agent-tools.yaml")
python := env_var_or_default("PYTHON", "python3")

# Show available commands.
help:
    just --list

# Bootstrap local dependencies and validate project configuration.
bootstrap:
    sh scripts/project/bootstrap.sh

# Install the toolbox (AGENT.md + .agent/skills) into a target project.
init target mode="copy":
    {{python}} scripts/project/init.py --config {{config}} --target "{{target}}" --mode "{{mode}}"

# Install into a target project, overwriting existing files.
init-force target mode="copy":
    {{python}} scripts/project/init.py --config {{config}} --target "{{target}}" --mode "{{mode}}" --force

# Show GitHub rate buckets.
gh-rate-limit:
    {{python}} scripts/github/agent-gh.py --config {{config}} rate-limit

# Alias for gh-rate-limit.
gh-rate:
    just gh-rate-limit

# Show one GitHub Actions run.
gh-ci-run run:
    {{python}} scripts/github/agent-gh.py --config {{config}} ci-run "{{run}}"

# List recent GitHub Actions runs.
gh-ci-runs workflow="" branch="" limit="5":
    {{python}} scripts/github/agent-gh.py --config {{config}} ci-runs {{ if workflow != "" { "--workflow " + quote(workflow) } else { "" } }} {{ if branch != "" { "--branch " + quote(branch) } else { "" } }} --limit "{{limit}}"

# Show cached PR context.
gh-pr pr:
    {{python}} scripts/github/agent-gh.py --config {{config}} pr "{{pr}}"

# Read a repository file, preferring local git.
gh-file path ref="origin/main":
    {{python}} scripts/github/agent-gh.py --config {{config}} file "{{path}}" --ref "{{ref}}"

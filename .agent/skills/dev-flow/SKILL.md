---
name: dev-flow-commit-merge
description: Follow this before any commit, PR, or merge. Covers commit identity, branch hygiene, and merge mechanics so agents stop re-deriving the flow and wasting tokens.
---

# Dev Flow: commit, branch, merge

Use this skill whenever you are about to commit, open a PR, or merge.

## Commit identity (never hand-craft)

Shared boxes often have no git identity → bare `git commit` fails with
`Author identity unknown`. Do **not** `git config --global`. Identity
comes from `agent-tools.yaml` (`identity.*`). Prefer the wrapped recipe;
if invoking git directly as a fallback:

```sh
git -c user.name="$IDENTITY_NAME" -c user.email="$IDENTITY_EMAIL" commit -F - <<'EOF'
<subject>

<body>

<pr_owner_line from config, if set>

<commit_trailer from config, if set>
EOF
```

- Multi-line / non-ASCII / backticks in the message → ALWAYS heredoc
  (`-F -`). Never `-m "..."` with backticks — the shell mangles it
  into a truncated commit.
- PR body first line MUST be `identity.pr_owner_line` when set.

## Branch hygiene (check BEFORE every commit)

```sh
git branch --show-current
```

Real incident: a commit landed on local `main` because the agent
assumed it was on the feature branch. Recovery:

```sh
git branch -f <feature-branch> <commit-sha>   # or: git cherry-pick <sha>
git checkout <feature-branch>
git branch -f main origin/main                # un-pollute local main
```

Remote `main` is only polluted if you `git push` from `main` — never
push from `main`.

## PR + merge

- One change = one branch = one PR.
- Before merge, the branch MUST be caught up with the default branch:
  `git merge-base --is-ancestor origin/<default> HEAD`. If behind,
  `git merge origin/<default>` first — a stale branch either blocks
  merge or drags an out-of-date tree (and can mask CI matrix drift).
- Merge per `github.merge` config: squash + delete-branch +
  verify the returned merge-commit oid. Honor `require_green`.
- Only the work owner reports merge status; don't echo others' merges.

---
name: ci-triage
description: Decision tree for a red CI run. Use BEFORE retrying — blind re-runs burn the shared GitHub rate limit and hide real bugs.
---

# CI Failure Triage

Use this skill whenever a PR's CI goes red.

## 1. Get the signal, not the whole log

Never dump a full failed-run log into context (10-50KB+). Use the
wrapper's key-line extraction (`github.ci.failed_log_signal_patterns`,
capped by `failed_log_max_lines`). Pull the raw log only when a human
explicitly asks.

## 2. Classify the failure

| Symptom | Class | Action |
|---|---|---|
| `psycopg2 ... Connection refused` / `port 5432` / "Apply migrations" | runner infra (postgres OOM/contention) | Do NOT loop-retry. Escalate / wait off-peak / evidence-based admin override. |
| kube-apiserver readiness 500 / kube-proxy CrashLoop / node not-ready | runner infra (kind cluster) | Same. |
| `test_openapi_route_coverage_matrix... AssertionError: N == M` | matrix drift | `git merge origin/<default>` into branch (brings updated matrix). Proven fix. |
| `Type error` / `tsc` / `Would reformat` / ruff | real code | Fix precisely. Don't retry. |
| compose/kind smoke ✅ but lint-and-unit ❌ on an FE-only PR | code clean → infra | Treat the red as infra; pursue the infra path. |

## 3. Don't double-trigger

If a monitor/PM script or another agent is already auto-rerunning, do
NOT also push an empty commit or `gh run rerun`. Coordinate so exactly
one owner pulls the trigger. Empty-commit retrigger re-runs ALL checks
→ waste + runner contention.

## 4. Persistent failure = escalate, not loop

≥3 failures of the same check across reruns is NOT a transient flake.
Pull the real log, name the root cause, escalate (SRE / off-peak
retry / evidence-based admin override) instead of an infinite loop.

## 5. i18n / contract sync gotcha

When you i18n a user-facing string (raw → `t('...')`), grep
contract/snapshot tests for the raw string before merging — they may
assert on it and turn main red after merge.

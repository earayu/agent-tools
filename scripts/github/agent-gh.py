#!/usr/bin/env python3
"""Cached GitHub operations for development agents."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


PR_FIELDS = [
    "number",
    "title",
    "state",
    "isDraft",
    "url",
    "author",
    "baseRefName",
    "headRefName",
    "headRefOid",
    "mergeStateStatus",
    "reviewDecision",
    "updatedAt",
    "files",
    "comments",
    "reviews",
    "statusCheckRollup",
]

RUN_FIELDS = [
    "status",
    "conclusion",
    "name",
    "displayTitle",
    "event",
    "headBranch",
    "headSha",
    "createdAt",
    "updatedAt",
    "url",
    "jobs",
]

RUN_LIST_FIELDS = [
    "databaseId",
    "status",
    "conclusion",
    "name",
    "displayTitle",
    "headBranch",
    "headSha",
    "createdAt",
    "updatedAt",
    "url",
]


def run(cmd: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def parse_scalar(raw: str) -> str:
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def read_simple_yaml(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current: dict[str, Any] | None = None
    if not path.exists():
        return data

    for raw_line in path.read_text().splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if not line.startswith(" ") and line.endswith(":"):
            key = line[:-1].strip()
            current = {}
            data[key] = current
            continue
        if line.startswith("  ") and ":" in line and current is not None:
            key, value = line.strip().split(":", 1)
            current[key.strip()] = parse_scalar(value)
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = parse_scalar(value)
    return data


def find_repo_root(start: Path) -> Path | None:
    result = run(["git", "rev-parse", "--show-toplevel"], cwd=start, check=False)
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip())


def repo_from_remote(root: Path) -> str | None:
    result = run(["git", "remote", "get-url", "origin"], cwd=root, check=False)
    if result.returncode != 0:
        return None
    remote = result.stdout.strip()
    if remote.startswith("git@"):
        _, rest = remote.split(":", 1)
        return rest.removesuffix(".git")
    parsed = urlparse(remote)
    path = parsed.path.strip("/")
    return path.removesuffix(".git") if path else None


def resolve_context(args: argparse.Namespace) -> dict[str, Any]:
    config_path = Path(args.config or os.environ.get("CONFIG", "agent-tools.yaml")).expanduser()
    config = read_simple_yaml(config_path)

    project = config.get("project") or {}
    github = config.get("github") or {}
    cache = config.get("cache") or {}

    workdir_raw = args.workdir or os.environ.get("WORKDIR") or project.get("workdir") or "."
    workdir = Path(workdir_raw).expanduser()
    if not workdir.is_absolute():
        workdir = (config_path.parent / workdir).resolve()

    repo_root = find_repo_root(workdir)
    repo = args.repo or os.environ.get("REPO") or github.get("repo")
    if not repo and repo_root:
        repo = repo_from_remote(repo_root)
    if not repo:
        raise SystemExit("GitHub repo is required. Set github.repo, REPO, or --repo.")

    default_branch = args.default_branch or os.environ.get("DEFAULT_BRANCH") or github.get("default_branch") or "main"
    cache_dir_raw = os.environ.get("AGENT_TOOLS_CACHE_DIR") or cache.get("dir") or ".agent-tools-cache"
    cache_dir = Path(str(cache_dir_raw)).expanduser()
    if not cache_dir.is_absolute():
        cache_dir = (config_path.parent / cache_dir).resolve()
    cache_dir = cache_dir / "github"
    cache_dir.mkdir(parents=True, exist_ok=True)

    return {
        "config_path": config_path,
        "workdir": workdir,
        "repo_root": repo_root,
        "repo": str(repo),
        "default_branch": str(default_branch),
        "cache_dir": cache_dir,
    }


def cache_key(parts: list[str]) -> str:
    return hashlib.sha256("\0".join(parts).encode()).hexdigest()


def read_cache(path: Path, ttl: int, refresh: bool) -> Any | None:
    if refresh or ttl <= 0 or not path.exists():
        return None
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if time.time() - float(payload.get("created_at", 0)) > ttl:
        return None
    return payload.get("data")


def write_cache(path: Path, data: Any) -> None:
    payload = {"created_at": time.time(), "data": data}
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    tmp.replace(path)


def cached_json(args: argparse.Namespace, ctx: dict[str, Any], key_parts: list[str], command: list[str]) -> Any:
    path = ctx["cache_dir"] / f"{cache_key(key_parts)}.json"
    cached = read_cache(path, args.ttl, args.refresh)
    if cached is not None:
        return cached

    result = run(command, cwd=ctx["repo_root"] or ctx["workdir"])
    data = json.loads(result.stdout)
    write_cache(path, data)
    return data


def print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))


def print_rate_summary(data: dict[str, Any]) -> None:
    for name in ("core", "graphql", "search", "code_search"):
        bucket = data.get(name) or {}
        reset = bucket.get("reset")
        reset_text = time.strftime("%Y-%m-%d %H:%M:%S %Z", time.localtime(reset)) if reset else "unknown"
        print(
            f"{name}: used={bucket.get('used')} remaining={bucket.get('remaining')} "
            f"limit={bucket.get('limit')} reset={reset_text}"
        )


def print_run_summary(data: dict[str, Any]) -> None:
    jobs = data.get("jobs") or []
    failed = [
        job.get("name")
        for job in jobs
        if job.get("conclusion") not in (None, "success", "skipped")
    ]
    print(f"run: {data.get('name') or data.get('displayTitle')}")
    print(f"status: {data.get('status')} conclusion: {data.get('conclusion')}")
    print(f"branch: {data.get('headBranch')} sha: {str(data.get('headSha') or '')[:12]}")
    print(f"updated: {data.get('updatedAt')}")
    if failed:
        print("failed_jobs:")
        for name in failed:
            print(f"- {name}")
    print(f"url: {data.get('url')}")


def print_runs_summary(items: list[dict[str, Any]]) -> None:
    for item in items:
        sha = str(item.get("headSha") or "")[:12]
        print(
            f"{item.get('databaseId')} {item.get('status')}/{item.get('conclusion')} "
            f"{item.get('headBranch')} {sha} {item.get('updatedAt')} {item.get('url')}"
        )


def print_pr_summary(data: dict[str, Any]) -> None:
    files = data.get("files") or []
    comments = data.get("comments") or []
    reviews = data.get("reviews") or []
    checks = data.get("statusCheckRollup") or []
    failing_checks = [
        item.get("name") or item.get("context")
        for item in checks
        if item.get("conclusion") not in (None, "SUCCESS", "success", "SKIPPED", "skipped")
    ]

    print(f"pr: #{data.get('number')} {data.get('title')}")
    print(f"state: {data.get('state')} draft: {data.get('isDraft')} review: {data.get('reviewDecision')}")
    print(f"branch: {data.get('headRefName')} -> {data.get('baseRefName')}")
    print(f"head: {str(data.get('headRefOid') or '')[:12]} merge: {data.get('mergeStateStatus')}")
    print(f"files: {len(files)} comments: {len(comments)} reviews: {len(reviews)} checks: {len(checks)}")
    if failing_checks:
        print("non_success_checks:")
        for name in failing_checks:
            print(f"- {name}")
    print(f"url: {data.get('url')}")


def command_rate_limit(args: argparse.Namespace, ctx: dict[str, Any]) -> None:
    data = cached_json(
        args,
        ctx,
        ["rate-limit", ctx["repo"]],
        [
            "gh",
            "api",
            "rate_limit",
            "--jq",
            "{core:.resources.core, search:.resources.search, graphql:.resources.graphql, code_search:.resources.code_search}",
        ],
    )
    print_json(data) if args.json else print_rate_summary(data)


def command_ci_run(args: argparse.Namespace, ctx: dict[str, Any]) -> None:
    data = cached_json(
        args,
        ctx,
        ["ci-run", ctx["repo"], args.run_id, ",".join(RUN_FIELDS)],
        ["gh", "run", "view", args.run_id, "--repo", ctx["repo"], "--json", ",".join(RUN_FIELDS)],
    )
    print_json(data) if args.json else print_run_summary(data)


def command_ci_runs(args: argparse.Namespace, ctx: dict[str, Any]) -> None:
    command = [
        "gh",
        "run",
        "list",
        "--repo",
        ctx["repo"],
        "--limit",
        str(args.limit),
        "--json",
        ",".join(RUN_LIST_FIELDS),
    ]
    key_parts = ["ci-runs", ctx["repo"], str(args.limit), ",".join(RUN_LIST_FIELDS)]
    if args.workflow:
        command.extend(["--workflow", args.workflow])
        key_parts.extend(["workflow", args.workflow])
    if args.branch:
        command.extend(["--branch", args.branch])
        key_parts.extend(["branch", args.branch])

    data = cached_json(args, ctx, key_parts, command)
    print_json(data) if args.json else print_runs_summary(data)


def command_pr(args: argparse.Namespace, ctx: dict[str, Any]) -> None:
    data = cached_json(
        args,
        ctx,
        ["pr", ctx["repo"], args.pr, ",".join(PR_FIELDS)],
        ["gh", "pr", "view", args.pr, "--repo", ctx["repo"], "--json", ",".join(PR_FIELDS)],
    )
    print_json(data) if args.json else print_pr_summary(data)


def command_file(args: argparse.Namespace, ctx: dict[str, Any]) -> None:
    ref = args.ref or f"origin/{ctx['default_branch']}"
    repo_root = ctx["repo_root"]
    if repo_root:
        git_result = run(["git", "show", f"{ref}:{args.path}"], cwd=repo_root, check=False)
        if git_result.returncode == 0:
            print(git_result.stdout, end="")
            return

    key_parts = ["file", ctx["repo"], ref, args.path]
    path = ctx["cache_dir"] / f"{cache_key(key_parts)}.json"
    cached = read_cache(path, args.ttl, args.refresh)
    if cached is None:
        result = run(
            ["gh", "api", "--method", "GET", f"repos/{ctx['repo']}/contents/{args.path}", "-F", f"ref={ref}"],
            cwd=repo_root or ctx["workdir"],
        )
        response = json.loads(result.stdout)
        content = response.get("content")
        if not content:
            raise SystemExit(f"GitHub Contents API returned no content for {args.path}@{ref}")
        cached = base64.b64decode(content).decode()
        write_cache(path, cached)
    print(cached, end="" if cached.endswith("\n") else "\n")


def add_cached_flags(parser: argparse.ArgumentParser, ttl: int) -> None:
    parser.add_argument("--ttl", type=int, default=ttl)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--json", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cached GitHub operations for development agents.")
    parser.add_argument("--config", default=os.environ.get("CONFIG", "agent-tools.yaml"))
    parser.add_argument("--repo", help="GitHub repo, for example apecloud/aperag-enterprise.")
    parser.add_argument("--workdir", help="Target project workdir.")
    parser.add_argument("--default-branch")

    subparsers = parser.add_subparsers(dest="command", required=True)

    rate_limit = subparsers.add_parser("rate-limit", help="Show GitHub rate buckets.")
    add_cached_flags(rate_limit, 10)
    rate_limit.set_defaults(func=command_rate_limit)

    ci_run = subparsers.add_parser("ci-run", help="Show one Actions run with cache.")
    ci_run.add_argument("run_id")
    add_cached_flags(ci_run, 15)
    ci_run.set_defaults(func=command_ci_run)

    ci_runs = subparsers.add_parser("ci-runs", help="List recent Actions runs with cache.")
    ci_runs.add_argument("--workflow")
    ci_runs.add_argument("--branch")
    ci_runs.add_argument("--limit", type=int, default=5)
    add_cached_flags(ci_runs, 30)
    ci_runs.set_defaults(func=command_ci_runs)

    pr = subparsers.add_parser("pr", help="Show PR context with cache.")
    pr.add_argument("pr")
    add_cached_flags(pr, 60)
    pr.set_defaults(func=command_pr)

    file_cmd = subparsers.add_parser("file", help="Read a repo file, preferring local git.")
    file_cmd.add_argument("path")
    file_cmd.add_argument("--ref")
    file_cmd.add_argument("--ttl", type=int, default=600)
    file_cmd.add_argument("--refresh", action="store_true")
    file_cmd.set_defaults(func=command_file)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    ctx = resolve_context(args)
    try:
        args.func(args, ctx)
    except subprocess.CalledProcessError as exc:
        if exc.stdout:
            print(exc.stdout, file=sys.stderr, end="")
        if exc.stderr:
            print(exc.stderr, file=sys.stderr, end="")
        return exc.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


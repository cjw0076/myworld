#!/usr/bin/env python3
"""File-backed AIOS sprint loop runner.

The runner keeps persistence outside provider CLIs. A sprint file is the queue;
Codex, Claude, or another provider is a bounded worker tick. When no unchecked
task remains, the runner stops.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "aios.sprint_loop.v1"
TASK_RE = re.compile(r"^(?P<prefix>\s*-\s+\[(?P<mark>[ xX])\]\s+)(?P<body>.+?)\s*$")
SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}"),
    re.compile(r"BEGIN (?:RSA |OPENSSH |EC |)PRIVATE KEY"),
    re.compile(r"(?i)\b(password|secret|token)\s*=\s*\S+"),
)


@dataclass(frozen=True)
class SprintTask:
    index: int
    line_no: int
    done: bool
    text: str


@dataclass(frozen=True)
class SprintFile:
    path: Path
    meta: dict[str, str]
    lines: list[str]
    tasks: list[SprintTask]


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def validate_text(label: str, value: str) -> None:
    for pattern in SECRET_PATTERNS:
        if pattern.search(value):
            raise SystemExit(f"{label} contains secret-like content")


def parse_sprint(path: Path) -> SprintFile:
    if not path.exists():
        raise SystemExit(f"sprint file not found: {path}")
    lines = path.read_text(encoding="utf-8").splitlines()
    meta: dict[str, str] = {}
    cursor = 0
    if lines and lines[0].strip() == "---":
        cursor = 1
        while cursor < len(lines) and lines[cursor].strip() != "---":
            key, sep, value = lines[cursor].partition(":")
            if sep:
                meta[key.strip()] = value.strip().strip('"')
            cursor += 1
    tasks: list[SprintTask] = []
    for line_no, line in enumerate(lines):
        match = TASK_RE.match(line)
        if not match:
            continue
        tasks.append(
            SprintTask(
                index=len(tasks),
                line_no=line_no,
                done=match.group("mark").lower() == "x",
                text=match.group("body").strip(),
            )
        )
    return SprintFile(path=path, meta=meta, lines=lines, tasks=tasks)


def pending_tasks(sprint: SprintFile) -> list[SprintTask]:
    return [task for task in sprint.tasks if not task.done]


def next_task(sprint: SprintFile) -> SprintTask | None:
    pending = pending_tasks(sprint)
    return pending[0] if pending else None


def repo_path(root: Path, sprint: SprintFile, override: str | None) -> Path:
    raw = override or sprint.meta.get("repo_path") or "."
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = root / path
    return path.resolve()


def provider_prompt(sprint: SprintFile, task: SprintTask) -> str:
    goal = sprint.meta.get("goal", "AIOS sprint")
    repo = sprint.meta.get("repo", "unknown")
    verification = sprint.meta.get("verification", "run the repo's narrowest meaningful verification")
    prompt = f"""AIOS sprint worker tick.

Sprint file: {sprint.path.as_posix()}
Repo: {repo}
Goal: {goal}

Take exactly this next unchecked task:
- {task.text}

Rules:
- Read the sprint file and repo-local agent instructions first.
- Preserve existing user/agent changes.
- Implement only the bounded task unless the sprint file explicitly asks for a small batch.
- Run verification: {verification}.
- Update the sprint file by marking completed work with [x] and appending a short receipt.
- If blocked, leave the task unchecked and append a blocker note.
- Stop after this tick. Do not start an infinite loop.
"""
    validate_text("provider prompt", prompt)
    return prompt


def default_provider_command(provider: str, repo: Path, prompt: str) -> list[str]:
    if provider == "codex":
        return ["codex", "exec", "--cd", repo.as_posix(), "--sandbox", "workspace-write", prompt]
    if provider == "claude":
        permission_mode = os.environ.get("AIOS_CLAUDE_PERMISSION_MODE", "default")
        return ["claude", "--print", prompt, "--permission-mode", permission_mode, "--add-dir", repo.as_posix()]
    if provider == "local":
        return [sys.executable, "-c", "print('local provider placeholder: no execution binding configured')"]
    raise SystemExit(f"unsupported provider: {provider}")


def format_command(command: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in command)


def mark_task_complete(sprint: SprintFile, task: SprintTask, receipt_path: Path) -> None:
    lines = list(sprint.lines)
    line = lines[task.line_no]
    lines[task.line_no] = TASK_RE.sub(lambda match: f"{match.group('prefix').replace('[ ]', '[x]')}{match.group('body')}", line)
    lines.extend(
        [
            "",
            "## AIOS Sprint Receipt",
            "",
            f"- completed_at: {now_iso()}",
            f"- task: {task.text}",
            f"- receipt: {receipt_path.as_posix()}",
        ]
    )
    sprint.path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_receipt(root: Path, sprint: SprintFile, payload: dict[str, Any]) -> Path:
    repo = sprint.meta.get("repo", "unknown")
    safe_repo = re.sub(r"[^A-Za-z0-9_.-]+", "-", repo)
    receipt_dir = root / ".aios" / "sprint_runs" / safe_repo
    receipt_dir.mkdir(parents=True, exist_ok=True)
    stamp = now_iso().replace(":", "").replace("-", "").split("+")[0]
    path = receipt_dir / f"{stamp}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def status_payload(root: Path, sprint: SprintFile) -> dict[str, Any]:
    pending = pending_tasks(sprint)
    task = pending[0] if pending else None
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "continue" if task else "stop",
        "generated_at": now_iso(),
        "root": root.as_posix(),
        "sprint_file": sprint.path.as_posix(),
        "repo": sprint.meta.get("repo"),
        "goal": sprint.meta.get("goal"),
        "total_tasks": len(sprint.tasks),
        "pending_tasks": len(pending),
        "next_task": task.text if task else None,
    }


def command_status(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root).resolve()
    sprint = parse_sprint(Path(args.sprint_file).resolve())
    return status_payload(root, sprint)


def command_init(args: argparse.Namespace) -> dict[str, Any]:
    path = Path(args.sprint_file).resolve()
    if path.exists() and not args.force:
        raise SystemExit(f"sprint file already exists: {path}")
    validate_text("goal", args.goal)
    tasks = args.task or []
    for task in tasks:
        validate_text("task", task)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "---",
        "schema_version: aios.sprint_file.v1",
        f"repo: {args.repo}",
        f"repo_path: {args.repo_path}",
        f"provider: {args.provider}",
        f"goal: {args.goal}",
        f"verification: {args.verification}",
        "---",
        "",
        f"# {args.goal}",
        "",
        "## Queue",
        "",
        *[f"- [ ] {task}" for task in tasks],
        "",
        "## Receipts",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "created",
        "sprint_file": path.as_posix(),
        "task_count": len(tasks),
    }


def command_tick(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root).resolve()
    sprint = parse_sprint(Path(args.sprint_file).resolve())
    task = next_task(sprint)
    if not task:
        return {**status_payload(root, sprint), "tick_executed": False, "reason": "no_pending_tasks"}

    repo = repo_path(root, sprint, args.repo_path)
    provider = args.provider or sprint.meta.get("provider") or "codex"
    prompt = provider_prompt(sprint, task)
    command = args.provider_command if args.provider_command else default_provider_command(provider, repo, prompt)
    started_at = now_iso()
    raw: subprocess.CompletedProcess[str] | None = None
    timed_out = False
    if args.execute:
        try:
            raw = subprocess.run(command, cwd=repo, text=True, capture_output=True, timeout=args.timeout, check=False)
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            raw = subprocess.CompletedProcess(command, 124, stdout=exc.stdout or "", stderr=exc.stderr or "")

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": "dry_run" if not args.execute else ("passed" if raw and raw.returncode == 0 and not timed_out else "failed"),
        "generated_at": now_iso(),
        "started_at": started_at,
        "root": root.as_posix(),
        "sprint_file": sprint.path.as_posix(),
        "repo": sprint.meta.get("repo"),
        "repo_path": repo.as_posix(),
        "provider": provider,
        "task": task.text,
        "command": command,
        "command_display": format_command(command),
        "tick_executed": bool(args.execute),
        "timed_out": timed_out,
        "returncode": raw.returncode if raw else None,
        "stdout_tail": (raw.stdout if raw else "")[-2000:],
        "stderr_tail": (raw.stderr if raw else "")[-2000:],
    }
    receipt_path = write_receipt(root, sprint, payload)
    payload["receipt"] = receipt_path.as_posix()
    receipt_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.execute and args.mark_complete_on_success and raw and raw.returncode == 0 and not timed_out:
        mark_task_complete(sprint, task, receipt_path)
        payload["marked_complete"] = True
    else:
        payload["marked_complete"] = False
    return payload


def command_run(args: argparse.Namespace) -> dict[str, Any]:
    if args.max_ticks <= 0:
        raise SystemExit("--max-ticks must be >= 1")
    ticks = []
    for _ in range(args.max_ticks):
        tick = command_tick(args)
        ticks.append(tick)
        if tick.get("status") in {"stop", "failed"} or tick.get("reason") == "no_pending_tasks":
            break
        if not args.mark_complete_on_success:
            break
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "passed" if all(tick.get("status") in {"passed", "dry_run", "stop"} for tick in ticks) else "failed",
        "generated_at": now_iso(),
        "ticks": ticks,
    }


def emit(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{payload.get('schema_version')} status={payload.get('status')}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="AIOS root")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="create a sprint file")
    init.add_argument("--sprint-file", required=True)
    init.add_argument("--repo", required=True)
    init.add_argument("--repo-path", required=True)
    init.add_argument("--provider", default="codex", choices=["codex", "claude", "local"])
    init.add_argument("--goal", required=True)
    init.add_argument("--verification", default="typecheck/build plus relevant smoke checks")
    init.add_argument("--task", action="append")
    init.add_argument("--force", action="store_true")
    init.add_argument("--json", action="store_true")
    init.set_defaults(func=command_init)

    status = sub.add_parser("status", help="show sprint file status")
    status.add_argument("--sprint-file", required=True)
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=command_status)

    tick = sub.add_parser("tick", help="run or preview one provider tick")
    tick.add_argument("--sprint-file", required=True)
    tick.add_argument("--repo-path")
    tick.add_argument("--provider", choices=["codex", "claude", "local"])
    tick.add_argument("--provider-command", nargs=argparse.REMAINDER)
    tick.add_argument("--execute", action="store_true")
    tick.add_argument("--mark-complete-on-success", action="store_true")
    tick.add_argument("--timeout", type=int, default=900)
    tick.add_argument("--json", action="store_true")
    tick.set_defaults(func=command_tick)

    run = sub.add_parser("run", help="run bounded sprint ticks")
    run.add_argument("--sprint-file", required=True)
    run.add_argument("--repo-path")
    run.add_argument("--provider", choices=["codex", "claude", "local"])
    run.add_argument("--provider-command", nargs=argparse.REMAINDER)
    run.add_argument("--execute", action="store_true")
    run.add_argument("--mark-complete-on-success", action="store_true")
    run.add_argument("--timeout", type=int, default=900)
    run.add_argument("--max-ticks", type=int, default=1)
    run.add_argument("--json", action="store_true")
    run.set_defaults(func=command_run)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    payload = args.func(args)
    emit(payload, getattr(args, "json", False))
    return 0 if payload.get("status") in {"created", "continue", "stop", "dry_run", "passed"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

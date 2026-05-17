#!/usr/bin/env python3
"""Evaluate AIOS Gate Chair answer quality against the internal baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "aios.gate_chair_eval.v1"
PRIVATE_RE = re.compile(r"(\\.env|secret|credential|token|api key|pin|q1q1e3e3|AIza[0-9A-Za-z_-]+|sk-[A-Za-z0-9_-]+)", re.IGNORECASE)
DEFAULT_PROMPTS = [
    "너는 누구니?",
    "나에 대한 기억은?",
    "AIOS에는 gate 역할의 Agent가 있나? 아니면 시스템 답변밖에 못하나?",
    "provider 실패 기억은?",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def stable_id(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def canonical_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(data) + "\n", encoding="utf-8")


def redact(value: Any, *, limit: int = 900) -> str:
    text = str(value or "")
    text = PRIVATE_RE.sub("[REDACTED_PRIVATE]", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit].rstrip()


def rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def quality_checks(prompt: str, payload: dict[str, Any]) -> dict[str, bool]:
    response = str(payload.get("response") or "")
    chair = payload.get("gate_chair_status") if isinstance(payload.get("gate_chair_status"), dict) else {}
    lower_prompt = prompt.lower()
    checks = {
        "answer_nonempty": bool(response.strip()),
        "not_raw_system_receipt": "I routed this as a lightweight conversation turn" not in response
        and "Session preparation status" not in response,
        "chair_status_success_or_not_needed": chair.get("status") in {"success", "not_attempted"} or payload.get("provider_turn") is not None,
    }
    if "기억" in prompt or "memory" in lower_prompt:
        checks["memory_question_mentions_memory"] = "MemoryOS" in response or "기억" in response or "mem_" in response
    if "gate" in lower_prompt or "agent" in lower_prompt or "시스템 답변" in prompt:
        checks["architecture_discloses_runtime"] = "Gate Chair runtime 상태" in response or "internal_evidence_synthesizer" in response
    if "실패" in prompt or "failure" in lower_prompt or "provider" in lower_prompt:
        checks["negative_evidence_not_hidden"] = "negative evidence" in response or "실패" in response or "provider" in response
    return checks


def run_chat(
    root: Path,
    script: Path,
    prompt: str,
    conversation: str,
    *,
    force_internal: bool,
    runtime_override: str | None = None,
) -> dict[str, Any]:
    env = os.environ.copy()
    if force_internal:
        env["AIOS_GATE_CHAIR_FORCE_INTERNAL"] = "1"
    else:
        env.pop("AIOS_GATE_CHAIR_FORCE_INTERNAL", None)
    if runtime_override:
        env["AIOS_GATE_CHAIR_RUNTIME_PATH"] = runtime_override
    result = subprocess.run(
        [
            sys.executable,
            script.as_posix(),
            "--root",
            root.as_posix(),
            "--conversation",
            conversation,
            "--message",
            prompt,
            "--json",
        ],
        cwd=script.parents[1],
        text=True,
        capture_output=True,
        env=env,
        check=False,
        timeout=int(os.environ.get("AIOS_GATE_CHAIR_EVAL_TIMEOUT", "90")),
    )
    if result.returncode != 0:
        return {
            "ok": False,
            "status": "chat_failed",
            "return_code": result.returncode,
            "stderr_preview": redact(result.stderr, limit=600),
            "stdout_preview": redact(result.stdout, limit=600),
        }
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"ok": False, "status": "json_parse_failed", "stdout_preview": redact(result.stdout, limit=600)}
    return payload if isinstance(payload, dict) else {"ok": False, "status": "json_not_object"}


def candidate_runtime_path(root: Path) -> str | None:
    path = root / ".aios" / "gate" / "founder" / "chair_candidate_runtime.json"
    if path.exists():
        return ".aios/gate/founder/chair_candidate_runtime.json"
    return None


def eval_mode(root: Path, script: Path, prompts: list[str], mode: str, eval_id: str, *, runtime_override: str | None = None) -> dict[str, Any]:
    force_internal = mode == "internal"
    runs: list[dict[str, Any]] = []
    for index, prompt in enumerate(prompts, start=1):
        conversation = f"gate-chair-eval-{eval_id}-{mode}-{index}"
        payload = run_chat(root, script, prompt, conversation, force_internal=force_internal, runtime_override=runtime_override)
        checks = quality_checks(prompt, payload) if payload.get("schema_version") == "aios.chat.turn.v1" else {"chat_payload_ok": False}
        passed = sum(1 for value in checks.values() if value)
        total = len(checks) or 1
        runs.append(
            {
                "prompt_id": f"p{index}",
                "prompt_preview": redact(prompt, limit=220),
                "conversation_id": conversation,
                "ok": payload.get("schema_version") == "aios.chat.turn.v1",
                "chosen_substrate": payload.get("chosen_substrate"),
                "route_reason": payload.get("route_reason"),
                "gate_chair_status": payload.get("gate_chair_status"),
                "response_preview": redact(payload.get("response"), limit=900),
                "artifact_paths": payload.get("artifact_paths") if isinstance(payload.get("artifact_paths"), dict) else {},
                "checks": checks,
                "score": round(passed / total, 4),
            }
        )
    avg = round(sum(float(row["score"]) for row in runs) / max(1, len(runs)), 4)
    runtime_modes = sorted(
        {
            str((row.get("gate_chair_status") or {}).get("mode") or "not_attempted")
            for row in runs
            if isinstance(row.get("gate_chair_status"), dict)
        }
    )
    runtime_models = sorted(
        {
            str((row.get("gate_chair_status") or {}).get("model") or "unknown")
            for row in runs
            if isinstance(row.get("gate_chair_status"), dict)
        }
    )
    return {
        "mode": mode,
        "force_internal": force_internal,
        "runtime_override": runtime_override,
        "average_score": avg,
        "runtime_modes": runtime_modes,
        "runtime_models": runtime_models,
        "runs": runs,
    }


def current_runtime_is_external(current: dict[str, Any] | None) -> bool:
    if not current:
        return False
    modes = {str(mode) for mode in current.get("runtime_modes") or []}
    return bool(modes - {"internal_evidence_synthesizer", "not_attempted", "unknown"})


def build_report(root: Path, *, prompts: list[str], mode: str) -> dict[str, Any]:
    script = Path(__file__).resolve().with_name("aios_chat.py")
    eval_id = stable_id(now_iso() + ":" + "|".join(prompts))
    modes = ["internal", "current"] if mode == "both" else [mode]
    candidate_path = candidate_runtime_path(root)
    mode_reports = [
        eval_mode(root, script, prompts, item, eval_id, runtime_override=candidate_path if item == "current" else None)
        for item in modes
    ]
    scores = {item["mode"]: item["average_score"] for item in mode_reports}
    if len(scores) == 2 and scores["current"] > scores["internal"]:
        verdict = "current_runtime_better_than_internal"
    elif len(scores) == 2 and scores["current"] < scores["internal"]:
        verdict = "current_runtime_worse_than_internal"
    elif len(scores) == 2:
        verdict = "tie_or_no_external_delta"
    else:
        verdict = "single_mode_observed"
    by_mode = {item["mode"]: item for item in mode_reports}
    current = by_mode.get("current")
    internal = by_mode.get("internal")
    external_current = current_runtime_is_external(current)
    promotion_ready = bool(
        current
        and internal
        and external_current
        and float(scores.get("current", 0.0)) > float(scores.get("internal", 0.0))
    )
    if not external_current and current:
        readiness_reason = "current Chair uses the internal deterministic runtime; no provider-grade runtime delta exists."
    elif not promotion_ready and current and internal:
        readiness_reason = "current Chair did not beat the internal baseline."
    elif promotion_ready:
        readiness_reason = "current Chair beat the internal baseline with a non-internal runtime."
    else:
        readiness_reason = "single-mode eval cannot decide promotion readiness."
    report = {
        "schema_version": SCHEMA_VERSION,
        "eval_id": eval_id,
        "created_at": now_iso(),
        "root": root.as_posix(),
        "prompt_count": len(prompts),
        "modes": mode_reports,
        "scores": scores,
        "verdict": verdict,
        "promotion_ready": promotion_ready,
        "readiness_reason": readiness_reason,
        "current_runtime_external": external_current,
        "current_runtime_modes": (current or {}).get("runtime_modes") or [],
        "candidate_runtime_path": candidate_path,
        "next": "Attach a real Chair runtime only if it beats the internal baseline on conversational usefulness and evidence discipline.",
    }
    report_path = root / ".aios" / "evals" / "gate_chair" / eval_id / "report.json"
    write_json(report_path, {**report, "report_path": rel(report_path, root)})
    return {**report, "report_path": rel(report_path, root)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--mode", choices=["both", "internal", "current"], default="both")
    parser.add_argument("--prompt", action="append", dest="prompts", help="override/add an eval prompt; can be repeated")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    prompts = args.prompts or DEFAULT_PROMPTS
    report = build_report(root, prompts=prompts, mode=args.mode)
    if args.json:
        print(canonical_json(report))
    else:
        print(f"report={report['report_path']}")
        print(f"verdict={report['verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

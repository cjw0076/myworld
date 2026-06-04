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

try:
    import aios_local_app
except ModuleNotFoundError:  # imported as scripts.aios_gate_chair_eval in tests
    from scripts import aios_local_app  # type: ignore


SCHEMA_VERSION = "aios.gate_chair_eval.v1"
MATRIX_SCHEMA_VERSION = "aios.gate_chair_candidate_matrix.v1"
MEMORY_DRAFT_SCHEMA = "aios.chat.memory_drafts.v1"
PRIVATE_RE = re.compile(r"(\\.env|secret|credential|token|api key|pin|q1q1e3e3|AIza[0-9A-Za-z_-]+|sk-[A-Za-z0-9_-]+)", re.IGNORECASE)
DEFAULT_PROMPTS = [
    "너는 누구니?",
    "나에 대한 기억은?",
    "AIOS에는 gate 역할의 Agent가 있나? 아니면 시스템 답변밖에 못하나?",
    "provider 실패 기억은?",
]
DEFAULT_MATRIX_CANDIDATES = ["ollama", "claude", "codex", "gemini"]
DEFAULT_CANDIDATE_MODELS = {
    "ollama": "qwen2.5:7b",
    "claude": "claude-opus-4-6",
    "codex": "",
    "gemini": "",
}


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
        checks["architecture_discloses_runtime"] = any(
            token in response
            for token in (
                "Gate Chair runtime 상태",
                "Gate Chair runtime",
                "chair_runtime.json",
                "chair_candidate_runtime.json",
                "internal_evidence_synthesizer",
            )
        )
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


def candidate_config_ref(root: Path) -> str:
    path = root / ".aios" / "gate" / "founder" / "chair_candidate_runtime.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return ".aios/gate/founder/chair_candidate_runtime.json"


def write_candidate_config(root: Path, mode: str) -> str:
    ref = candidate_config_ref(root)
    model = DEFAULT_CANDIDATE_MODELS.get(mode, "")
    write_json(
        root / ref,
        {
            "schema_version": "aios.gate.chair_runtime.v1",
            "status": "candidate",
            "mode": mode,
            "model": model,
            "reason": "temporary candidate matrix evaluation",
            "updated_at": now_iso(),
        },
    )
    return ref


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


def failed_runs(report: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for mode in report.get("modes") or []:
        if not isinstance(mode, dict):
            continue
        for run in mode.get("runs") or []:
            if not isinstance(run, dict):
                continue
            chair = run.get("gate_chair_status") if isinstance(run.get("gate_chair_status"), dict) else {}
            status = str(chair.get("status") or "")
            if run.get("ok") is False or (status and status not in {"success", "not_attempted"}):
                rows.append({"mode": mode, "run": run, "chair": chair, "status": status or str(run.get("status") or "chat_failed")})
    return rows


def mode_failure_count(mode_report: dict[str, Any] | None) -> int:
    if not mode_report:
        return 0
    rows = []
    for run in mode_report.get("runs") or []:
        if isinstance(run, dict) and chair_run_failed(run):
            rows.append(run)
    return len(rows)


def write_failure_memory_draft(root: Path, report: dict[str, Any], report_ref: str) -> str | None:
    failures = failed_runs(report)
    if not failures:
        return None
    eval_id = str(report.get("eval_id") or stable_id(now_iso()))
    lines: list[str] = []
    refs: list[str] = [report_ref]
    for item in failures[:8]:
        run = item["run"]
        chair = item["chair"]
        provider = str(chair.get("mode") or item["mode"].get("mode") or "gate_chair")
        model = str(chair.get("model") or "unknown")
        prompt = str(run.get("prompt_preview") or "unknown prompt")
        status = str(item["status"] or "failed")
        lines.append(f"- {status}: {provider} model={model} on `{prompt}`")
        artifacts = run.get("artifact_paths") if isinstance(run.get("artifact_paths"), dict) else {}
        gate_turns = artifacts.get("gate_chair_turns")
        if isinstance(gate_turns, str) and gate_turns:
            refs.append(gate_turns)
    draft = {
        "type": "negative_evidence_signal",
        "origin": "aios_gate_chair_eval",
        "status": "draft",
        "project": "AIOS",
        "confidence": 0.7,
        "conversation_id": f"gate-chair-eval-{eval_id}-failures",
        "content": "Gate Chair eval projected negative provider/runtime evidence for review:\n" + "\n".join(lines),
        "raw_refs": list(dict.fromkeys(refs)),
        "provenance": {
            "source": "aios_gate_chair_eval",
            "eval_id": eval_id,
            "report_ref": report_ref,
            "created_at": now_iso(),
        },
    }
    path = root / ".aios" / "chat" / f"gate-chair-eval-{eval_id}-failures" / "memory_drafts.json"
    write_json(path, {"schema_version": MEMORY_DRAFT_SCHEMA, "memory_drafts": [draft]})
    return rel(path, root)


def request_failure_memory_review(root: Path, memory_draft_ref: str) -> dict[str, Any]:
    status, payload = aios_local_app.build_memory_draft_review_response(
        root,
        {"source_artifact": memory_draft_ref, "draft_id": "0", "confirm": True},
    )
    if status != 200 or not payload.get("ok"):
        return {
            "status": "failed",
            "http_status": status,
            "reason": payload.get("reason") or "memory_review_request_failed",
        }
    receipt = payload.get("receipt") if isinstance(payload.get("receipt"), dict) else {}
    return {
        "status": "sent_to_memoryOS_inbox",
        "request_id": receipt.get("request_id"),
        "packet": (receipt.get("artifact_paths") or {}).get("packet") if isinstance(receipt.get("artifact_paths"), dict) else None,
        "return_to": (receipt.get("artifact_paths") or {}).get("return_to") if isinstance(receipt.get("artifact_paths"), dict) else None,
    }


def build_report(root: Path, *, prompts: list[str], mode: str, request_memory_review: bool = False) -> dict[str, Any]:
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
    current_failure_count = mode_failure_count(current)
    promotion_ready = bool(
        current
        and internal
        and external_current
        and current_failure_count == 0
        and float(scores.get("current", 0.0)) >= float(scores.get("internal", 0.0))
    )
    if not external_current and current:
        readiness_reason = "current Chair uses the internal deterministic runtime; no provider-grade runtime delta exists."
    elif not promotion_ready and current and internal:
        if current_failure_count:
            readiness_reason = "current Chair had provider/runtime failures; keep it as a candidate until failures are reviewed."
        else:
            readiness_reason = "current Chair fell below the internal baseline."
    elif promotion_ready:
        if float(scores.get("current", 0.0)) > float(scores.get("internal", 0.0)):
            readiness_reason = "current Chair beat the internal baseline with a non-internal runtime."
        else:
            readiness_reason = "current Chair matched the internal baseline with a non-internal runtime and no failures; it is eligible for operator-confirmed conversational activation."
    else:
        readiness_reason = "single-mode eval cannot decide promotion readiness."
    report_path = root / ".aios" / "evals" / "gate_chair" / eval_id / "report.json"
    report_ref = rel(report_path, root)
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
        "current_failure_count": current_failure_count,
        "current_runtime_modes": (current or {}).get("runtime_modes") or [],
        "candidate_runtime_path": candidate_path,
        "next": "Attach a real Chair runtime only when it matches or beats the internal baseline with no provider/runtime failures and operator-confirmed activation.",
        "artifact_paths": {},
    }
    memory_draft_ref = write_failure_memory_draft(root, {**report, "report_path": report_ref}, report_ref)
    if memory_draft_ref:
        report["artifact_paths"]["memory_drafts"] = memory_draft_ref
        report["memory_draft_candidate"] = {
            "status": "draft",
            "source": "gate_chair_eval_failures",
            "path": memory_draft_ref,
            "next_action": "request_memoryos_review_before_acceptance",
        }
        if request_memory_review:
            review = request_failure_memory_review(root, memory_draft_ref)
            report["memory_review_request"] = review
            if review.get("packet"):
                report["artifact_paths"]["memory_review_packet"] = review["packet"]
    write_json(report_path, {**report, "report_path": report_ref})
    return {**report, "report_path": report_ref}


def chair_run_failed(run: dict[str, Any]) -> bool:
    chair = run.get("gate_chair_status") if isinstance(run.get("gate_chair_status"), dict) else {}
    status = str(chair.get("status") or "")
    return run.get("ok") is False or bool(status and status not in {"success", "not_attempted"})


def candidate_external(mode_report: dict[str, Any]) -> bool:
    modes = {str(mode) for mode in mode_report.get("runtime_modes") or []}
    return bool(modes - {"internal_evidence_synthesizer", "not_attempted", "unknown"})


def summarize_candidate(mode: str, report: dict[str, Any], baseline_score: float) -> dict[str, Any]:
    mode_report = (report.get("modes") or [{}])[0]
    runs = [run for run in mode_report.get("runs") or [] if isinstance(run, dict)]
    failures = [run for run in runs if chair_run_failed(run)]
    score = float(mode_report.get("average_score") or 0.0)
    external = candidate_external(mode_report)
    return {
        "mode": mode,
        "model": DEFAULT_CANDIDATE_MODELS.get(mode, ""),
        "average_score": score,
        "baseline_delta": round(score - baseline_score, 4),
        "external_runtime_observed": external,
        "failure_count": len(failures),
        "runtime_modes": mode_report.get("runtime_modes") or [],
        "runtime_models": mode_report.get("runtime_models") or [],
        "report_path": report.get("report_path"),
        "memory_draft_candidate": report.get("memory_draft_candidate"),
        "promotion_eligible": bool(external and not failures and score >= baseline_score),
    }


def build_candidate_matrix(
    root: Path,
    *,
    prompts: list[str],
    candidates: list[str] | None = None,
    request_memory_review: bool = False,
) -> dict[str, Any]:
    requested = candidates or DEFAULT_MATRIX_CANDIDATES
    candidate_path = root / ".aios" / "gate" / "founder" / "chair_candidate_runtime.json"
    had_candidate = candidate_path.exists()
    previous_candidate = candidate_path.read_text(encoding="utf-8") if had_candidate else ""
    matrix_id = stable_id(now_iso() + ":matrix:" + "|".join(prompts) + ":" + "|".join(requested))
    baseline = build_report(root, prompts=prompts, mode="internal")
    baseline_score = float(((baseline.get("modes") or [{}])[0]).get("average_score") or 0.0)
    candidate_summaries: list[dict[str, Any]] = []
    try:
        for mode in requested:
            if mode not in DEFAULT_MATRIX_CANDIDATES:
                candidate_summaries.append(
                    {
                        "mode": mode,
                        "status": "skipped",
                        "reason": "unsupported_candidate_mode",
                        "promotion_eligible": False,
                    }
                )
                continue
            write_candidate_config(root, mode)
            report = build_report(
                root,
                prompts=prompts,
                mode="current",
                request_memory_review=request_memory_review,
            )
            candidate_summaries.append(summarize_candidate(mode, report, baseline_score))
    finally:
        if had_candidate:
            candidate_path.parent.mkdir(parents=True, exist_ok=True)
            candidate_path.write_text(previous_candidate, encoding="utf-8")
        else:
            try:
                candidate_path.unlink()
            except FileNotFoundError:
                pass

    eligible = [item for item in candidate_summaries if item.get("promotion_eligible")]
    best = max(
        candidate_summaries,
        key=lambda item: (bool(item.get("promotion_eligible")), float(item.get("average_score") or 0.0), -int(item.get("failure_count") or 0)),
        default=None,
    )
    recommendation = "hold_all_candidates"
    if eligible:
        recommendation = f"candidate_ready:{eligible[0].get('mode')}"
    report_path = root / ".aios" / "evals" / "gate_chair_matrix" / matrix_id / "report.json"
    report_ref = rel(report_path, root)
    report = {
        "schema_version": MATRIX_SCHEMA_VERSION,
        "matrix_id": matrix_id,
        "created_at": now_iso(),
        "prompt_count": len(prompts),
        "baseline": {
            "mode": "internal",
            "average_score": baseline_score,
            "report_path": baseline.get("report_path"),
        },
        "candidates": candidate_summaries,
        "best_candidate": best,
        "promotion_ready": bool(eligible),
        "recommendation": recommendation,
        "request_memory_review": request_memory_review,
        "restored_candidate_runtime": True,
        "report_path": report_ref,
    }
    write_json(report_path, report)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--mode", choices=["both", "internal", "current"], default="both")
    parser.add_argument("--prompt", action="append", dest="prompts", help="override/add an eval prompt; can be repeated")
    parser.add_argument("--candidate-matrix", action="store_true", help="evaluate provider Chair candidates without activating them")
    parser.add_argument("--candidate", action="append", dest="candidates", help="candidate mode for --candidate-matrix; may repeat")
    parser.add_argument("--request-memory-review", action="store_true", help="send generated failure memory draft to MemoryOS inbox")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    prompts = args.prompts or DEFAULT_PROMPTS
    if args.candidate_matrix:
        report = build_candidate_matrix(
            root,
            prompts=prompts,
            candidates=args.candidates,
            request_memory_review=args.request_memory_review,
        )
    else:
        report = build_report(root, prompts=prompts, mode=args.mode, request_memory_review=args.request_memory_review)
    if args.json:
        print(canonical_json(report))
    else:
        print(f"report={report['report_path']}")
        print(f"verdict={report['verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

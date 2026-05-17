#!/usr/bin/env python3
"""AIOS chat turn router.

The router is the mandatory front door for chat turns. It records the user
message, builds an AIOS plan-only invocation, chooses a substrate, writes cost
and memory-draft artifacts, then returns a user-safe response envelope.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aios_invoke
try:
    import aios_few_shot_injector
except ModuleNotFoundError:  # imported as scripts.aios_chat_router in tests
    from scripts import aios_few_shot_injector  # type: ignore


SCHEMA_VERSION = "aios.chat.turn.v1"
COST_SCHEMA = "aios.chat.cost.v1"
MESSAGE_SCHEMA = "aios.chat.message.v1"
MEMORY_DRAFT_SCHEMA = "aios.chat.memory_drafts.v1"
GATE_SCHEMA = "aios.chat.gate_decision.v1"
CHAIR_RUNTIME_SCHEMA = "aios.gate.chair_runtime.v1"
CHAIR_RUNTIME_MODES = {"internal_evidence_synthesizer", "ollama", "claude", "codex", "gemini"}
PROVIDER_CHAIR_MODES = {"claude", "codex", "gemini"}
MAX_MESSAGE_CHARS = 8000
OVERRIDES = {
    "@claude": "claude",
    "@codex": "codex",
    "@local": "local_llm",
    "@ollama": "ollama_qwen",
    "@gemini": "gemini",
}
LOCAL_SUBSTRATES = {"local_llm", "ollama_qwen"}
NON_EXECUTING_SUBSTRATES = {
    "hive_flow",
    "aios_gate",
    "gate_clarification",
    "capability_route_required",
    "gate_answer",
}
PROVIDER_ALIASES = {
    "ollama_qwen": ("ollama_qwen", "ollama", "local_llm", "local llm", "local model", "cheap local", "cheap model"),
    "local_llm": ("local_llm", "local llm", "local model", "cheap local", "cheap model"),
    "claude": ("claude", "anthropic"),
    "codex": ("codex", "openai codex"),
    "gemini": ("gemini", "google gemini"),
}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def canonical_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(data) + "\n", encoding="utf-8")


def append_jsonl(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(data, ensure_ascii=False, sort_keys=True) + "\n")


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if isinstance(row, dict):
                rows.append(row)
    except (OSError, json.JSONDecodeError):
        return []
    return rows


def stable_id(value: str) -> str:
    return aios_invoke.stable_hash(value)[:16]


def slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()
    return slug[:64] or "chat"


def conversation_dir(root: Path, conversation_id: str) -> Path:
    base = (root / ".aios" / "chat").resolve()
    candidate = (base / slugify(conversation_id)).resolve()
    try:
        candidate.relative_to(base)
    except ValueError as exc:
        raise SystemExit(f"conversation output must stay under {base}") from exc
    return candidate


def strip_override(message: str) -> tuple[str | None, str]:
    stripped = message.strip()
    first, _, rest = stripped.partition(" ")
    substrate = OVERRIDES.get(first.lower())
    if substrate:
        return substrate, rest.strip()
    return None, stripped


def estimate_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4)


def classify_intent(message: str) -> str:
    lower = message.lower()
    if any(
        word in lower
        for word in (
            "implement",
            "refactor",
            "contract",
            "sprint",
            "dispatch",
            "build",
            "fix",
            "작업",
            "개선",
            "구현",
            "만들",
            "고쳐",
            "수정",
            "진행해",
            "진행하자",
            "진행시켜",
        )
    ):
        return "multi_step"
    if wants_current_info(message):
        return "current_info"
    if len(message) <= 160 or any(word in lower for word in ("summarize", "explain", "status", "what is", "어떤", "요약")):
        return "cheap_single_turn"
    return "single_turn"


def wants_current_info(message: str) -> bool:
    lower = message.lower()
    compact = re.sub(r"\s+", "", lower)
    return any(
        token in lower
        for token in (
            "weather",
            "today's weather",
            "current weather",
            "latest",
            "current",
            "right now",
            "stock price",
            "exchange rate",
            "오늘 날씨",
            "현재 날씨",
            "최신",
            "지금",
            "주가",
            "환율",
        )
    ) or any(token in compact for token in ("오늘날씨", "현재날씨", "지금날씨"))


def weather_location(message: str) -> str | None:
    lower = message.lower()
    known = {
        "seoul": "Seoul",
        "서울": "Seoul",
        "san francisco": "San Francisco",
        "sf": "San Francisco",
        "new york": "New York",
        "뉴욕": "New York",
        "los angeles": "Los Angeles",
        "la": "Los Angeles",
        "tokyo": "Tokyo",
        "도쿄": "Tokyo",
    }
    for token, location in known.items():
        if token in lower:
            return location
    return None


def wants_provider_gate(message: str) -> bool:
    lower = message.lower()
    return (
        ("chatbot" in lower or "provider" in lower or "provided" in lower or "cli" in lower)
        and ("aios" in lower or "gate" in lower or "agent" in lower or "연결" in lower or "역할" in lower)
    ) or ("gate 역할" in lower) or ("codex(cli)" in lower)


def build_gate_decision(message: str, override: str | None) -> dict[str, Any]:
    if wants_current_info(message):
        location = weather_location(message) if ("weather" in message.lower() or "날씨" in message.lower()) else None
        missing_location = ("weather" in message.lower() or "날씨" in message.lower()) and not location
        return {
            "schema_version": GATE_SCHEMA,
            "gate_role": "aios_gate_agent",
            "decision": "clarify_location" if missing_location else "require_current_info_route",
            "input_class": "current_info",
            "route": "CapabilityOS.current_info",
            "required_capabilities": ["cap_web_research_route", "weather_or_current_info_adapter"],
            "missing_inputs": ["location"] if missing_location else [],
            "location": location,
            "provider_execution": "held",
            "reason": "Current facts must not be hallucinated by a cheap local turn.",
            "operator_override": override,
        }
    if wants_provider_gate(message) and not wants_action(message):
        return {
            "schema_version": GATE_SCHEMA,
            "gate_role": "aios_gate_agent",
            "decision": "answer_architecture",
            "input_class": "aios_architecture",
            "route": "Gate -> MemoryOS -> CapabilityOS -> GenesisOS/Hive -> provider substrate",
            "required_capabilities": ["provider_registry", "capability_route", "memory_context", "hive_execution_when_needed"],
            "missing_inputs": [],
            "provider_execution": "not_required",
            "reason": "The user is asking about AIOS gateway architecture, not asking a provider to execute work.",
            "operator_override": override,
        }
    return {
        "schema_version": GATE_SCHEMA,
        "gate_role": "aios_gate_agent",
        "decision": "route_normally",
        "input_class": classify_intent(message),
        "route": "standard_chat_router",
        "required_capabilities": [],
        "missing_inputs": [],
        "provider_execution": "allowed_by_router",
        "reason": "No special gate hold is required.",
        "operator_override": override,
    }


def load_gate_pack(root: Path, user: str = "founder") -> dict[str, Any] | None:
    payload = read_json(root / ".aios" / "gate" / user / "gate_pack.json")
    if not isinstance(payload, dict) or payload.get("schema_version") != "aios.gate.pack.v1":
        return None
    if payload.get("status") != "active":
        return None
    return payload


def load_gate_chair_runtime_config(root: Path, user: str = "founder") -> dict[str, Any] | None:
    override = os.environ.get("AIOS_GATE_CHAIR_RUNTIME_PATH", "").strip()
    path = root / ".aios" / "gate" / user / "chair_runtime.json"
    allow_candidate = False
    if override:
        candidate = (root / override).resolve()
        gate_root = (root / ".aios" / "gate").resolve()
        try:
            candidate.relative_to(gate_root)
        except ValueError:
            return None
        path = candidate
        allow_candidate = True
    payload = read_json(path)
    if not isinstance(payload, dict) or payload.get("schema_version") != CHAIR_RUNTIME_SCHEMA:
        return None
    if payload.get("status") != "active" and not (allow_candidate and payload.get("status") == "candidate"):
        return None
    mode = str(payload.get("mode") or "")
    if mode not in CHAIR_RUNTIME_MODES:
        return None
    return payload


def gate_pack_projection(pack: dict[str, Any] | None) -> dict[str, Any] | None:
    if not pack:
        return None
    rules = pack.get("rules") if isinstance(pack.get("rules"), dict) else {}
    examples = pack.get("examples") if isinstance(pack.get("examples"), list) else []
    return {
        "pack_id": pack.get("id"),
        "generated_at": pack.get("generated_at"),
        "source_pair_count": pack.get("source_pair_count", 0),
        "accepted_memory_hint_count": pack.get("accepted_memory_hint_count", 0),
        "rules_applied": [key for key, value in rules.items() if value is True and key != "finetune_ready"],
        "example_ids": [str(row.get("id")) for row in examples[:3] if isinstance(row, dict) and row.get("id")],
        "finetune_ready": bool(rules.get("finetune_ready")),
    }


def build_invocation(root: Path, message: str, conversation_id: str) -> dict[str, Any]:
    write = f".aios/invocations/chat-{stable_id(conversation_id + ':' + message)}"
    args = argparse.Namespace(goal=message, write=write, contract_id=None, plan_only=True, execute=False)
    try:
        return aios_invoke.build_invocation(root, args)
    except SystemExit as exc:
        return {
            "schema_version": "aios.invocation_receipt.v1",
            "overall_status": "failed",
            "role_statuses": {},
            "artifact_paths": {},
            "stop_conditions_triggered": ["invocation_failed"],
            "error": str(exc),
        }


def load_capability_payload(root: Path, invocation: dict[str, Any]) -> dict[str, Any]:
    rel = (invocation.get("artifact_paths") or {}).get("capability")
    payload = read_json(root / rel) if isinstance(rel, str) else None
    return payload if isinstance(payload, dict) else {}


def load_genesis_payload(root: Path, invocation: dict[str, Any]) -> dict[str, Any]:
    rel = (invocation.get("artifact_paths") or {}).get("genesis")
    payload = read_json(root / rel) if isinstance(rel, str) else None
    return payload if isinstance(payload, dict) else {}


def genesis_friction_projection(payload: dict[str, Any]) -> dict[str, Any] | None:
    branches = [branch for branch in payload.get("branches") or [] if isinstance(branch, dict)]
    if not branches:
        return None
    frictions: list[dict[str, Any]] = []
    for branch in branches:
        what = str(branch.get("what_it_breaks") or "").strip()
        why = str(branch.get("why_it_might_matter") or "").strip()
        premise = str(branch.get("premise") or "").strip()
        seed = str(branch.get("contract_seed") or "").strip()
        if not any((what, why, premise, seed)):
            continue
        frictions.append(
            {
                "branch_id": branch.get("branch_id"),
                "type": branch.get("type"),
                "discomfort": what or premise,
                "need": why or seed,
                "contract_seed": seed,
            }
        )
    if not frictions:
        return None
    return {
        "schema_version": "aios.chat.genesis_friction.v1",
        "authority": payload.get("authority", "speculative_only"),
        "source_goal": payload.get("goal"),
        "frictions": frictions[:3],
        "branch_count": len(branches),
    }


def provider_candidates_from_capability(payload: dict[str, Any]) -> list[str]:
    candidates: list[str] = []
    text = json.dumps(payload, ensure_ascii=False).lower()
    if "ollama" in text or "local" in text:
        candidates.append("ollama_qwen")
    if "claude" in text:
        candidates.append("claude")
    if "codex" in text:
        candidates.append("codex")
    if "gemini" in text:
        candidates.append("gemini")
    return candidates


def bad_provider_signals(memory: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    signals: dict[str, list[dict[str, Any]]] = {}
    for item in memory.get("negative_evidence") or []:
        if not isinstance(item, dict):
            continue
        haystack = " ".join(
            str(value).lower()
            for value in (
                item.get("id"),
                item.get("type"),
                item.get("content"),
                item.get("failure_class"),
                " ".join(str(ref) for ref in item.get("raw_refs") or []),
            )
        )
        for provider, aliases in PROVIDER_ALIASES.items():
            if any(alias in haystack for alias in aliases):
                signals.setdefault(provider, []).append(
                    {
                        "id": item.get("id"),
                        "type": item.get("type"),
                        "failure_class": item.get("failure_class"),
                        "content": sanitize_provider_text(str(item.get("content") or ""), max_lines=1, max_chars=180),
                    }
                )
    return signals


def provider_is_penalized(provider: str, signals: dict[str, list[dict[str, Any]]]) -> bool:
    if provider in signals:
        return True
    if provider in LOCAL_SUBSTRATES:
        return any(local in signals for local in LOCAL_SUBSTRATES)
    return False


def route_audit_from_negative(memory: dict[str, Any], skipped: list[str] | None = None) -> dict[str, Any] | None:
    signals = bad_provider_signals(memory)
    if not signals and not skipped:
        return None
    return {
        "schema_version": "aios.chat.capability_route_audit.v1",
        "negative_evidence_source": memory.get("negative_evidence_source"),
        "bad_provider_signals": signals,
        "skipped_provider_candidates": skipped or [],
    }


def choose_substrate(
    message: str,
    override: str | None,
    capability_payload: dict[str, Any],
    gate: dict[str, Any],
    memory: dict[str, Any] | None = None,
) -> tuple[str, str, str, dict[str, Any] | None]:
    intent = str(gate.get("input_class") or classify_intent(message))
    if override:
        return override, intent, "operator_override", None
    if gate.get("decision") == "clarify_location":
        return "gate_clarification", intent, "gate_requires_input", None
    if gate.get("decision") == "require_current_info_route":
        return "capability_route_required", intent, "requires_current_external_source", None
    if gate.get("decision") == "answer_architecture":
        return "aios_gate", intent, "gate_answer", None
    if intent == "multi_step":
        return "hive_flow", intent, "multi_step_orchestration", None
    memory = memory or {}
    skipped: list[str] = []
    for candidate in provider_candidates_from_capability(capability_payload):
        if provider_is_penalized(candidate, bad_provider_signals(memory)):
            skipped.append(candidate)
            continue
        if candidate in LOCAL_SUBSTRATES:
            return candidate, intent, "capability_cost_tier", route_audit_from_negative(memory, skipped)
        if skipped:
            return candidate, intent, "negative_evidence_avoids_bad_provider", route_audit_from_negative(memory, skipped)
    if intent == "cheap_single_turn":
        return "local_llm", intent, "cheap_local_first", route_audit_from_negative(memory, skipped)
    return "local_llm", intent, "default_local_first", route_audit_from_negative(memory, skipped)


def memory_context(root: Path, message: str) -> dict[str, Any]:
    memory_root = root / "memoryOS"
    if not (memory_root / "memoryos" / "cli.py").exists():
        return {"status": "unavailable", "reason": "memoryos_cli_missing"}
    command = [
        sys.executable,
        "-m",
        "memoryos.cli",
        "--root",
        ".",
        "context",
        "build",
        "--task",
        message,
        "--for",
        "hive",
        "--project",
        "AIOS",
        "--json",
    ]
    try:
        result = subprocess.run(command, cwd=memory_root, text=True, capture_output=True, timeout=20, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"status": "unavailable", "reason": str(exc)}
    if result.returncode != 0:
        return {"status": "unavailable", "reason": (result.stderr or result.stdout)[-500:]}
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"status": "unavailable", "reason": "json_parse_failed"}
    if not isinstance(payload, dict):
        return {"status": "unavailable", "reason": "json_not_object"}
    selected_memories: list[dict[str, Any]] = []
    for key in ("decisions", "constraints", "open_questions", "recent_actions", "other"):
        for item in payload.get(key) or []:
            if not isinstance(item, dict) or not item.get("id"):
                continue
            selected_memories.append(
                {
                    "id": str(item.get("id")),
                    "type": str(item.get("type") or key),
                    "content": sanitize_provider_text(str(item.get("content") or ""), max_lines=2, max_chars=360),
                    "confidence": item.get("confidence"),
                    "raw_refs": [str(ref) for ref in (item.get("raw_refs") or [])[:3]],
                }
            )
    selected = [item["id"] for item in selected_memories]
    negative = [item for item in selected_memories if is_negative_evidence_memory(item)]
    negative_source = "memoryos" if negative else None
    if wants_negative_evidence_question(message) and not negative:
        negative = local_negative_evidence(root)
        negative_source = "aios_receipts" if negative else None
    return {
        "status": "available",
        "trace_id": payload.get("trace_id") or payload.get("retrieval_trace_id"),
        "selected_memory_ids": selected,
        "selected_memories": selected_memories[:10],
        "negative_evidence": negative[:5],
        "context_items": len(selected),
        "negative_evidence_count": len(negative),
        "negative_evidence_source": negative_source,
    }


def wants_status(message: str) -> bool:
    lower = message.lower()
    return any(token in lower for token in ("status", "현재", "상태", "진행", "progress", "what happened"))


def wants_memory_question(message: str) -> bool:
    lower = message.lower()
    compact = re.sub(r"\s+", "", lower)
    return any(
        token in lower
        for token in (
            "memory",
            "remember",
            "memories",
            "about me",
            "what do you know about me",
            "기억",
            "나에 대한",
            "나를",
            "내가",
            "founder",
        )
    ) or any(token in compact for token in ("나에대한기억", "나를기억", "내기억", "나에대해"))


def wants_negative_evidence_question(message: str) -> bool:
    lower = message.lower()
    compact = re.sub(r"\s+", "", lower)
    return any(
        token in lower
        for token in (
            "negative evidence",
            "failure memory",
            "failed provider",
            "provider failure",
            "bad route",
            "bad tool",
            "blocked",
            "blocker",
            "rate limit",
            "pin",
            "access denied",
            "실패",
            "막힌",
            "막혔",
            "블록",
            "거절",
            "나쁜 도구",
            "안된",
            "안 된",
        )
    ) or any(token in compact for token in ("실패기억", "막힌것", "안된것", "나쁜도구"))


def wants_genesis_friction_question(message: str) -> bool:
    lower = message.lower()
    compact = re.sub(r"\s+", "", lower)
    return any(
        token in lower
        for token in (
            "genesis",
            "friction",
            "discomfort",
            "unstated need",
            "hidden need",
            "assumption",
            "branch",
            "불편",
            "불편함",
            "필요성",
            "숨은 필요",
            "가정",
            "세계선",
            "다른 관점",
        )
    ) or any(token in compact for token in ("불편함", "필요성", "숨은필요", "다른관점"))


def is_negative_evidence_memory(item: dict[str, Any]) -> bool:
    kind = str(item.get("type") or "").lower()
    content = str(item.get("content") or "").lower()
    refs = " ".join(str(ref).lower() for ref in item.get("raw_refs") or [])
    negative_types = {
        "failure_memory",
        "negative_evidence",
        "provider_failure",
        "rejected_ingest",
        "privacy_hold",
        "stale_memory",
        "bad_route",
        "bad_tool",
    }
    if kind in negative_types:
        return True
    haystack = f"{kind} {content} {refs}"
    return any(
        token in haystack
        for token in (
            "failure",
            "failed",
            "blocked",
            "backpressure",
            "rate limit",
            "access denied",
            "pin_required",
            "pin required",
            "provider_access_denied",
            "provider_backpressure",
            "rejected",
            "privacy hold",
            "stale",
            "bad tool",
            "bad route",
            "실패",
            "막힘",
            "거절",
        )
    )


def local_negative_evidence(root: Path, limit: int = 5) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(category: str, content: str, ref: Path | str, confidence: float = 0.66) -> None:
        if len(rows) >= limit:
            return
        key = f"{category}:{content}:{ref}"
        if key in seen:
            return
        seen.add(key)
        ref_text = relative(ref, root) if isinstance(ref, Path) else str(ref)
        rows.append(
            {
                "id": f"neg_{stable_id(key)}",
                "type": "failure_memory",
                "content": sanitize_provider_text(content, max_lines=2, max_chars=360),
                "confidence": confidence,
                "raw_refs": [ref_text],
                "source": "aios_receipt_fallback",
                "failure_class": category,
            }
        )

    outbox = root / ".aios" / "outbox"
    if outbox.exists():
        result_files = sorted(outbox.glob("*/*.result.json"), key=lambda path: path.stat().st_mtime, reverse=True)
        for path in result_files[:120]:
            payload = read_json(path)
            if not isinstance(payload, dict):
                continue
            categories: list[str] = []
            for key in ("final_failure_category", "failure_category"):
                value = payload.get(key)
                if value and str(value) not in {"none", "success"}:
                    categories.append(str(value))
            for attempt in payload.get("agent_attempts") or []:
                if isinstance(attempt, dict) and attempt.get("failure_category") and str(attempt.get("failure_category")) not in {"none", "success"}:
                    categories.append(str(attempt.get("failure_category")))
            for stop in payload.get("stop_conditions_triggered") or []:
                if str(stop) in {"provider_backpressure", "provider_access_denied", "pin_required_noninteractive", "pending_concurrent_work"}:
                    categories.append(str(stop))
            for category in dict.fromkeys(categories):
                repo = payload.get("target_repo") or path.parent.name
                dispatch = payload.get("dispatch_id") or path.stem
                status = payload.get("status") or "unknown"
                add(
                    category,
                    f"{repo} dispatch {dispatch} recorded {category} with status={status}; route fallback, credential handling, or verifier before accepting similar work.",
                    path,
                    0.74,
                )
            if len(rows) >= limit:
                return rows

    for path in sorted((root / ".aios" / "logs").glob("*.attempts.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)[:80]:
        for row in read_jsonl(path):
            category = str(row.get("failure_category") or "")
            if category and category not in {"none", "success"}:
                agent = row.get("agent") or "provider"
                add(category, f"{agent} attempt recorded {category}; use this as negative provider-route evidence.", path, 0.68)
            if len(rows) >= limit:
                return rows

    for path in (root / ".aios" / "state" / "child_watchers.jsonl", root / ".aios" / "state" / "aios_pingpong.jsonl"):
        for row in reversed(read_jsonl(path)[-120:]):
            status = str(row.get("status") or "")
            if status in {"provider_access_denied", "provider_backpressure", "pin_required_noninteractive"}:
                repo = row.get("repo") or row.get("agent") or "provider"
                event = row.get("event") or "event"
                add(status, f"{repo} {event} recorded {status}; future routes should fallback or request credential handling.", path, 0.62)
            if len(rows) >= limit:
                return rows

    return rows


def sanitize_provider_text(text: str, *, max_lines: int = 80, max_chars: int = 8000) -> str:
    lines = [line.rstrip() for line in str(text).splitlines() if line.strip() or line == ""]
    clipped = "\n".join(lines[:max_lines])
    if len(clipped) > max_chars:
        return clipped[:max_chars] + " ..."
    return clipped


def strip_terminal_punctuation(value: Any) -> str:
    return str(value or "").strip().rstrip(".!?。！？")


def _provider_prompt_payload(message: str, injection: dict[str, Any], memory: dict[str, Any], gate: dict[str, Any]) -> str:
    prefix = [
        "AIOS control-plane chat turn. Answer the user query naturally and directly.",
        "Do not output raw private tokens, keys, or secrets.",
        f"Gate decision: {gate.get('decision', 'route_normally')}.",
        f"Message intent: {gate.get('input_class', 'unknown')}.",
    ]
    if injection.get("injected_prompt"):
        prefix.append(f"Recent patterns: {', '.join((injection.get('patterns_injected') or []) ) or 'none'}")
    if memory.get("status") == "available":
        prefix.append(f"MemoryOS trace: {memory.get('trace_id') or 'none'}")
        if memory.get("context_items"):
            prefix.append(f"Selected memory ids: {', '.join((memory.get('selected_memory_ids') or [])[:8])}")
        memories = [item for item in (memory.get("selected_memories") or []) if isinstance(item, dict)]
        if memories:
            prefix.append("Selected memory excerpts:")
            for item in memories[:5]:
                prefix.append(f"- {item.get('id')}: {item.get('content')}")
        negative = [item for item in (memory.get("negative_evidence") or []) if isinstance(item, dict)]
        if negative:
            prefix.append("Negative evidence excerpts:")
            for item in negative[:3]:
                prefix.append(f"- {item.get('id')}: {item.get('content')}")
    return "\n".join(prefix) + "\n\nUser message:\n" + message


def gate_chair_prompt(message: str, base_response: str, memory: dict[str, Any], gate: dict[str, Any], genesis: dict[str, Any] | None = None) -> str:
    payload = {
        "role": "AIOS Gate Chair",
        "instruction": (
            "Answer naturally as the AIOS conversation gate. Use only the provided "
            "MemoryOS/CapabilityOS/GenesisOS/Gate evidence. Do not invent private "
            "facts, secrets, current facts, or execution results. Keep the answer concise."
        ),
        "user_message": message,
        "deterministic_fallback": base_response,
        "gate_decision": {
            "decision": gate.get("decision"),
            "input_class": gate.get("input_class"),
            "route": gate.get("route"),
            "capability_route_audit": gate.get("capability_route_audit"),
            "genesis_friction": gate.get("genesis_friction"),
        },
        "memory_context": {
            "trace_id": memory.get("trace_id"),
            "selected_memories": memory.get("selected_memories") or [],
            "negative_evidence": memory.get("negative_evidence") or [],
            "negative_evidence_source": memory.get("negative_evidence_source"),
        },
        "genesis_context": genesis or {},
    }
    return canonical_json(payload)


def gate_chair_allowed(root: Path, message: str, gate: dict[str, Any], memory: dict[str, Any]) -> bool:
    if gate.get("decision") in {"clarify_location", "require_current_info_route"}:
        return False
    explicit = os.environ.get("AIOS_GATE_CHAIR_ENABLED", "").strip().lower()
    if explicit in {"0", "false", "no", "off"}:
        return False
    forced = os.environ.get("AIOS_GATE_CHAIR_FORCE_INTERNAL", "").strip().lower()
    config = load_gate_chair_runtime_config(root)
    if forced in {"1", "true", "yes", "on"}:
        enabled = True
    elif config:
        enabled = True
    elif os.environ.get("AIOS_GATE_AGENT_COMMAND", "").strip():
        enabled = True
    elif explicit in {"1", "true", "yes", "on"}:
        enabled = True
    else:
        enabled = bool(gate.get("gate_pack"))
    if not enabled:
        return False
    return (
        wants_memory_question(message)
        or wants_negative_evidence_question(message)
        or wants_provider_gate(message)
        or wants_identity(message)
        or wants_status(message)
        or bool(memory.get("selected_memories"))
        or bool(memory.get("negative_evidence"))
    )


def gate_chair_command(prompt: str, root: Path | None = None) -> tuple[list[str] | None, dict[str, Any]]:
    forced = os.environ.get("AIOS_GATE_CHAIR_FORCE_INTERNAL", "").strip().lower()
    if forced in {"1", "true", "yes", "on"}:
        return None, {"status": "configured", "mode": "internal_evidence_synthesizer", "model": "deterministic", "forced": True}
    config = load_gate_chair_runtime_config(root) if root else None
    if config:
        mode = str(config.get("mode") or "")
        if mode == "internal_evidence_synthesizer":
            return None, {
                "status": "configured",
                "mode": "internal_evidence_synthesizer",
                "model": "deterministic",
                "source": "chair_runtime_config",
            }
        if mode == "ollama":
            model = str(config.get("model") or os.environ.get("AIOS_GATE_OLLAMA_MODEL") or os.environ.get("AIOS_OLLAMA_MODEL") or "qwen2.5:7b")
            if _command_exists("ollama"):
                return ["ollama", "run", model, prompt], {
                    "status": "configured",
                    "mode": "ollama",
                    "model": model,
                    "source": "chair_runtime_config",
                }
            return None, {
                "status": "configured",
                "mode": "internal_evidence_synthesizer",
                "model": "deterministic",
                "source": "chair_runtime_config",
                "requested_mode": "ollama",
                "fallback_reason": "ollama_command_missing",
            }
        if mode in PROVIDER_CHAIR_MODES:
            command, provider_meta = chair_provider_command(mode, prompt, config)
            if command:
                return command, {
                    "status": "configured",
                    "mode": mode,
                    "model": provider_meta.get("model"),
                    "source": "chair_runtime_config",
                }
            return None, {
                "status": "configured",
                "mode": "internal_evidence_synthesizer",
                "model": "deterministic",
                "source": "chair_runtime_config",
                "requested_mode": mode,
                "fallback_reason": f"{mode}_command_missing",
            }
    env_cmd = os.environ.get("AIOS_GATE_AGENT_COMMAND", "").strip()
    if env_cmd:
        return ["/bin/bash", "-lc", env_cmd], {"status": "configured", "mode": "env_command"}
    if _command_exists("ollama"):
        model = os.environ.get("AIOS_GATE_OLLAMA_MODEL", os.environ.get("AIOS_OLLAMA_MODEL", "qwen2.5:7b"))
        return ["ollama", "run", model, prompt], {"status": "configured", "mode": "ollama", "model": model}
    return None, {"status": "configured", "mode": "internal_evidence_synthesizer", "model": "deterministic"}


def gate_chair_runtime_summary(root: Path | None = None) -> str:
    forced = os.environ.get("AIOS_GATE_CHAIR_FORCE_INTERNAL", "").strip().lower()
    if forced in {"1", "true", "yes", "on"}:
        return "AIOS_GATE_CHAIR_FORCE_INTERNAL이 켜져 있어서 baseline용 internal_evidence_synthesizer를 강제로 사용 중이야."
    override = os.environ.get("AIOS_GATE_CHAIR_RUNTIME_PATH", "").strip()
    runtime_label = override or ".aios/gate/founder/chair_runtime.json"
    runtime_kind = "candidate override" if override else "active runtime"
    config = load_gate_chair_runtime_config(root) if root else None
    if config:
        mode = str(config.get("mode") or "")
        if mode == "internal_evidence_synthesizer":
            return f"{runtime_label} ({runtime_kind})이 internal_evidence_synthesizer를 명시해서 deterministic Chair를 사용 중이야."
        if mode == "ollama":
            model = str(config.get("model") or "qwen2.5:7b")
            if _command_exists("ollama"):
                return f"{runtime_label} ({runtime_kind})이 local Ollama Chair model={model}를 지정했어."
            return f"{runtime_label} ({runtime_kind})은 Ollama Chair model={model}를 요청하지만, 이 머신에는 ollama command가 없어 internal fallback 중이야."
        if mode in PROVIDER_CHAIR_MODES:
            command, meta = chair_provider_command(mode, "", config)
            if command:
                model = f" model={meta.get('model')}" if meta.get("model") else ""
                return f"{runtime_label} ({runtime_kind})이 {mode} provider Chair{model}를 지정했어."
            return f"{runtime_label} ({runtime_kind})은 {mode} provider Chair를 요청하지만, 이 머신에는 {mode} command가 없어 internal fallback 중이야."
    env_cmd = os.environ.get("AIOS_GATE_AGENT_COMMAND", "").strip()
    if env_cmd:
        return "AIOS_GATE_AGENT_COMMAND가 설정되어 있어서 외부 Gate Chair command가 evidence를 자연어로 합성할 수 있어."
    if _command_exists("ollama"):
        model = os.environ.get("AIOS_GATE_OLLAMA_MODEL", os.environ.get("AIOS_OLLAMA_MODEL", "qwen2.5:7b"))
        return f"local Ollama Chair runtime이 연결되어 있고 model={model}로 Gate evidence를 합성할 수 있어."
    return (
        "외부/로컬 LLM Chair runtime은 아직 연결되지 않았고, 현재는 "
        "internal_evidence_synthesizer가 Gate/MemoryOS/CapabilityOS/GenesisOS evidence를 deterministic하게 정리해."
    )


def execute_internal_gate_chair(prompt: str) -> str:
    try:
        payload = json.loads(prompt)
    except json.JSONDecodeError:
        return sanitize_provider_text(prompt, max_lines=20, max_chars=2000)
    if not isinstance(payload, dict):
        return sanitize_provider_text(str(payload), max_lines=20, max_chars=2000)

    fallback = sanitize_provider_text(str(payload.get("deterministic_fallback") or ""), max_lines=40, max_chars=3000)
    memory = payload.get("memory_context") if isinstance(payload.get("memory_context"), dict) else {}
    gate = payload.get("gate_decision") if isinstance(payload.get("gate_decision"), dict) else {}
    selected = [item for item in (memory.get("selected_memories") or []) if isinstance(item, dict)]
    negative = [item for item in (memory.get("negative_evidence") or []) if isinstance(item, dict)]

    if gate.get("decision") == "answer_architecture" and fallback:
        return fallback
    if selected and fallback:
        return fallback
    if negative and fallback:
        return fallback
    if fallback:
        return fallback
    return "AIOS Gate Chair가 현재 evidence 안에서 답할 수 있는 내용이 부족해. 이 턴은 추가 MemoryOS context나 CapabilityOS route가 필요해."


def execute_gate_chair_turn(root: Path, prompt: str) -> tuple[bool, str, dict[str, Any]]:
    command, meta = gate_chair_command(prompt, root)
    if command is None:
        return (
            True,
            execute_internal_gate_chair(prompt),
            {"status": "success", "return_code": 0, "command": None, "meta": meta},
        )
    kwargs: dict[str, Any] = {
        "cwd": root,
        "text": True,
        "capture_output": True,
        "timeout": int(os.environ.get("AIOS_GATE_CHAIR_TIMEOUT", "45")),
    }
    if len(command) == 3 and command[0] == "/bin/bash" and command[1] == "-lc":
        kwargs["input"] = prompt
    try:
        result = subprocess.run(command, check=False, **kwargs)
    except OSError as exc:
        return False, "", {"status": "gate_chair_exception", "reason": str(exc), "command": command, "meta": meta}
    except subprocess.TimeoutExpired:
        return False, "", {"status": "gate_chair_timeout", "meta": meta}
    raw_out = result.stdout or ""
    raw_err = result.stderr or ""
    failure = classify_provider_failure((raw_out or raw_err), result.returncode)
    if failure:
        return (
            False,
            raw_out.strip(),
            {
                "status": failure,
                "return_code": result.returncode,
                "raw_stderr": raw_err[-800:],
                "command": command,
                "meta": meta,
            },
        )
    text = sanitize_provider_text(raw_out or raw_err, max_lines=40, max_chars=4000)
    if not text:
        return False, "", {"status": "empty_output", "command": command, "meta": meta}
    return True, text, {"status": "success", "return_code": result.returncode, "command": command, "meta": meta}


def _command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def chair_provider_command(substrate: str, prompt: str, config: dict[str, Any] | None = None) -> tuple[list[str] | None, dict[str, Any]]:
    config = config or {}
    if substrate == "claude":
        if not _command_exists("claude"):
            return None, {"status": "missing_command", "command": "claude"}
        model = str(config.get("model") or os.environ.get("AIOS_CLAUDE_MODEL", "claude-opus-4-6"))
        return ["claude", "--print", prompt, "--model", model], {"status": "configured", "mode": "claude", "model": model}
    if substrate == "codex":
        if not _command_exists("codex"):
            return None, {"status": "missing_command", "command": "codex"}
        return ["codex", "exec", prompt], {"status": "configured", "mode": "codex"}
    if substrate == "gemini":
        if not _command_exists("gemini"):
            return None, {"status": "missing_command", "command": "gemini"}
        return ["gemini", "--approval-mode", "plan", "-p", prompt], {"status": "configured", "mode": "gemini"}
    return None, {"status": "unsupported_chair_substrate", "substrate": substrate}


def provider_command(substrate: str, prompt: str) -> tuple[list[str] | None, dict[str, Any]]:
    if substrate == "codex":
        if not _command_exists("codex"):
            return None, {"status": "missing_command", "command": "codex"}
        return ["codex", "exec", "--dangerously-bypass-approvals-and-sandbox", prompt], {"status": "configured"}
    if substrate == "claude":
        if not _command_exists("claude"):
            return None, {"status": "missing_command", "command": "claude"}
        model = os.environ.get("AIOS_CLAUDE_MODEL", "claude-opus-4-6")
        return ["claude", "--print", prompt, "--dangerously-skip-permissions", "--model", model], {"status": "configured"}
    if substrate == "gemini":
        if not _command_exists("gemini"):
            return None, {"status": "missing_command", "command": "gemini"}
        return ["gemini", "--approval-mode", "plan", "-p", prompt], {"status": "configured"}
    if substrate in {"local_llm", "ollama_qwen"}:
        env_cmd = os.environ.get("AIOS_LOCAL_AGENT_COMMAND", "").strip()
        if env_cmd:
            return ["/bin/bash", "-lc", env_cmd], {"status": "configured", "mode": "stdin"}
        if _command_exists("ollama"):
            model = os.environ.get("AIOS_OLLAMA_MODEL", "qwen2.5:7b")
            return ["ollama", "run", model, prompt], {"status": "configured", "mode": "ollama"}
        return None, {"status": "missing_command", "command": "AIOS_LOCAL_AGENT_COMMAND or ollama"}
    if substrate == "aios_gate":
        return None, {"status": "policy_gate"}
    return None, {"status": "unsupported_substrate", "substrate": substrate}


def classify_provider_failure(text: str, returncode: int) -> str | None:
    lower = (text or "").lower()
    if returncode != 0:
        if any(token in lower for token in ("rate limit", "rate-limit", "429", "too many requests", "backpressure")):
            return "provider_backpressure"
        if any(token in lower for token in ("access denied", "permission denied", "auth", "authentication", "pin", "apikey", "api key", "invalid pin")):
            return "provider_access_denied"
        if any(token in lower for token in ("not found", "command not found", "missing", "unsupported", "unrecognized")):
            return "provider_missing_command"
    return None if returncode == 0 else "provider_execution_failed"


def execute_provider_turn(root: Path, substrate: str, prompt: str) -> tuple[bool, str, dict[str, Any]]:
    if substrate in NON_EXECUTING_SUBSTRATES:
        return False, "", {"status": "not_executing"}

    command, meta = provider_command(substrate, prompt)
    if command is None:
        if substrate in LOCAL_SUBSTRATES:
            fallback_order = [item.strip() for item in os.environ.get("AIOS_CHAT_FALLBACK_PROVIDERS", "codex,claude,gemini").split(",") if item.strip()]
            provider_meta: dict[str, Any] = {"status": "fallback_unattempted"}
            for fallback in fallback_order:
                fallback_command, fallback_meta = provider_command(fallback, prompt)
                if fallback_command is None:
                    continue
                try:
                    kwargs: dict[str, Any] = {
                        "cwd": root,
                        "text": True,
                        "capture_output": True,
                        "timeout": int(os.environ.get("AIOS_CHAT_PROVIDER_TIMEOUT", "60")),
                    }
                    result = subprocess.run(fallback_command, check=False, **kwargs)
                except OSError as exc:
                    provider_meta = {
                        "status": "provider_execution_exception",
                        "provider": fallback,
                        "reason": str(exc),
                        "command": fallback_command,
                        "meta": fallback_meta,
                    }
                    continue
                except subprocess.TimeoutExpired:
                    provider_meta = {"status": "provider_timeout", "provider": fallback, "meta": fallback_meta}
                    continue

                raw_out = result.stdout or ""
                raw_err = result.stderr or ""
                failure = classify_provider_failure((raw_out or raw_err), result.returncode)
                if failure:
                    provider_meta = {
                        "status": failure,
                        "provider": fallback,
                        "return_code": result.returncode,
                        "raw_stderr": raw_err[-800:],
                        "command": fallback_command,
                        "meta": fallback_meta,
                    }
                    continue
                text = sanitize_provider_text(raw_out or raw_err)
                if not text:
                    provider_meta = {"status": "empty_output", "provider": fallback, "command": fallback_command, "meta": fallback_meta}
                    continue
                return (
                    True,
                    text,
                    {
                        "status": "fallback_success",
                        "provider": fallback,
                        "return_code": result.returncode,
                        "command": fallback_command,
                        "meta": fallback_meta,
                    },
                )
            return False, "", {**meta, "status": "command_unavailable", "fallback_attempted": fallback_order, "last_meta": provider_meta}

        return False, "", {**meta, "status": "command_unavailable"}

    timeout = int(os.environ.get("AIOS_CHAT_PROVIDER_TIMEOUT", "60"))
    kwargs: dict[str, Any] = {
        "cwd": root,
        "text": True,
        "capture_output": True,
        "timeout": timeout,
    }
    if len(command) == 3 and command[0] == "/bin/bash" and command[1] == "-lc":
        kwargs["input"] = prompt
    try:
        result = subprocess.run(command, check=False, **kwargs)
    except OSError as exc:
        return (
            False,
            "",
            {
                "status": "provider_execution_exception",
                "provider": substrate,
                "reason": str(exc),
                "command": command,
                "meta": meta,
            },
        )
    except subprocess.TimeoutExpired:
        return (
            False,
            "",
            {"status": "provider_timeout", "provider": substrate, "meta": meta},
        )

    raw_out = result.stdout or ""
    raw_err = result.stderr or ""
    failure = classify_provider_failure((raw_out or raw_err), result.returncode)
    if failure:
        return (
            False,
            raw_out.strip(),
            {
                "status": failure,
                "provider": substrate,
                "return_code": result.returncode,
                "raw_stderr": raw_err[-800:],
                "command": command,
                "meta": meta,
            },
        )
    text = sanitize_provider_text(raw_out or raw_err)
    if not text:
        return False, "", {"status": "empty_output", "provider": substrate, "command": command, "meta": meta}
    return (
        True,
        text,
        {
            "status": "success",
            "provider": substrate,
            "return_code": result.returncode,
            "command": command,
            "meta": meta,
        },
    )


def wants_greeting(message: str) -> bool:
    lower = message.lower()
    return any(token in lower for token in ("hello", "hi", "hey", "안녕", "하이"))


def wants_identity(message: str) -> bool:
    lower = message.lower()
    compact = re.sub(r"\s+", "", lower)
    return any(
        token in lower
        for token in (
            "who are you",
            "what are you",
            "your identity",
            "identity",
            "정체",
            "누구",
            "너는 누구",
            "넌 누구",
            "aios가 뭐",
            "aios는 뭐",
        )
    ) or any(token in compact for token in ("너는누구", "넌누구", "너뭐야"))


def wants_action(message: str) -> bool:
    lower = message.lower()
    return any(
        token in lower
        for token in (
            "build",
            "fix",
            "make",
            "dispatch",
            "contract",
            "만들",
            "고쳐",
            "작업",
            "구현",
            "개선",
            "수정",
            "진행해",
            "진행하자",
            "진행시켜",
        )
    )


def describe_memory(memory: dict[str, Any]) -> str:
    if memory.get("status") != "available":
        return "MemoryOS context is unavailable for this turn, so I will keep the answer provisional."
    count = int(memory.get("context_items") or 0)
    trace = memory.get("trace_id")
    if count:
        negative_count = int(memory.get("negative_evidence_count") or 0)
        source = memory.get("negative_evidence_source")
        if negative_count and source == "aios_receipts":
            return f"MemoryOS returned {count} relevant context item(s){f' via {trace}' if trace else ''}; AIOS also found {negative_count} local negative evidence receipt(s)."
        negative = f", including {negative_count} negative evidence item(s)" if negative_count else ""
        return f"MemoryOS returned {count} relevant context item(s){negative}{f' via {trace}' if trace else ''}."
    return f"MemoryOS returned no selected context{f' via {trace}' if trace else ''}."


def describe_genesis(genesis: dict[str, Any] | None) -> str:
    if not genesis:
        return "GenesisOS returned no friction branch for this turn."
    frictions = [item for item in genesis.get("frictions") or [] if isinstance(item, dict)]
    if not frictions:
        return "GenesisOS returned a branch artifact, but no usable friction projection."
    first = frictions[0]
    return (
        f"GenesisOS projected {len(frictions)} friction item(s); first discomfort: "
        f"{first.get('discomfort') or 'unspecified'}"
    )


def memory_answer(memory: dict[str, Any]) -> list[str]:
    if memory.get("status") != "available":
        return ["MemoryOS에서 지금 바로 꺼낼 수 있는 기억이 없어. 그래서 이 답은 임시 답변으로 봐야 해."]
    selected = rank_memory_for_answer([item for item in (memory.get("selected_memories") or []) if isinstance(item, dict)])
    trace = memory.get("trace_id")
    if not selected:
        return [f"MemoryOS는 연결됐지만 이 질문에 바로 붙는 선택 기억은 없었어{f' ({trace})' if trace else ''}."]

    lines = [
        f"MemoryOS가 너와 AIOS 작업 방식에 관련된 기억 {len(selected)}개를 찾았어{f' ({trace})' if trace else ''}.",
        "핵심은 이거야.",
    ]
    for item in selected[:5]:
        content = str(item.get("content") or "").strip()
        if not content:
            continue
        refs = item.get("raw_refs") or []
        ref = f" [{refs[0]}]" if refs else ""
        lines.append(f"- {content}{ref}")
    lines.append("이 기억들은 아직 대화 답변에 쓰기 위한 context이고, 새 기억으로 자동 승인되지는 않아.")
    return lines


def negative_evidence_answer(memory: dict[str, Any]) -> list[str]:
    if memory.get("status") != "available":
        return ["MemoryOS negative evidence를 지금 조회할 수 없어. 그래서 provider 실패나 bad route 판단은 임시로 다뤄야 해."]
    negative = [item for item in (memory.get("negative_evidence") or []) if isinstance(item, dict)]
    trace = memory.get("trace_id")
    if not negative:
        return [f"MemoryOS는 연결됐지만 이 질문에 바로 붙는 실패/거절 기억은 없었어{f' ({trace})' if trace else ''}."]
    source = memory.get("negative_evidence_source")
    if source == "aios_receipts":
        lines = [
            f"MemoryOS가 선택한 accepted failure memory는 없었지만, AIOS가 local receipts에서 negative evidence {len(negative)}개를 찾았어{f' ({trace})' if trace else ''}.",
            "이건 아직 MemoryOS accepted memory가 아니라 Gate가 다음 route를 망치지 않기 위한 보조 증거야.",
        ]
    else:
        lines = [
            f"MemoryOS가 실패/거절/막힘에 대한 negative evidence {len(negative)}개를 찾았어{f' ({trace})' if trace else ''}.",
            "다음 route에서는 이걸 성공 기억만큼 강하게 반영해야 해.",
        ]
    for item in negative[:5]:
        content = str(item.get("content") or "").strip()
        refs = item.get("raw_refs") or []
        ref = f" [{refs[0]}]" if refs else ""
        lines.append(f"- {item.get('id')}: {content}{ref}")
    lines.append("이 항목들은 provider/tool 선택에서 피해야 할 패턴, fallback 필요성, privacy hold를 판단하는 증거로 써야 해.")
    return lines


def genesis_friction_answer(genesis: dict[str, Any] | None) -> list[str]:
    frictions = [item for item in (genesis or {}).get("frictions") or [] if isinstance(item, dict)]
    if not frictions:
        return ["GenesisOS가 이 턴에서 바로 쓸 수 있는 불편함/필요성 branch를 찾지 못했어."]
    lines = [
        f"GenesisOS가 이 질문에서 불편함/필요성 후보 {len(frictions)}개를 만들었어.",
        "가장 먼저 볼 것은 이거야.",
    ]
    for item in frictions[:3]:
        discomfort = strip_terminal_punctuation(item.get("discomfort"))
        need = strip_terminal_punctuation(item.get("need"))
        branch = item.get("branch_id") or item.get("type") or "branch"
        lines.append(f"- {branch}: {discomfort} -> {need}")
    lines.append("이건 실행 명령이 아니라, 다음 contract나 Hive 작업으로 승격하기 전의 speculative signal이야.")
    return lines


def rank_memory_for_answer(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def score(item: dict[str, Any]) -> tuple[int, float]:
        content = str(item.get("content") or "").lower()
        refs = " ".join(str(ref).lower() for ref in item.get("raw_refs") or [])
        value = 0
        for token in ("founder", "사용자", "재원", "네가", "너", "나", "위임", "aios완성", "마지막", "claude의 cli", "local llm"):
            if token in content:
                value += 3
        for token in ("closeout", "recorded outcome"):
            if token in content:
                value -= 2
        if "asc-005" in refs:
            value += 1
        try:
            confidence = float(item.get("confidence") or 0)
        except (TypeError, ValueError):
            confidence = 0.0
        return value, confidence

    return sorted(items, key=score, reverse=True)


def describe_route(substrate: str, intent: str, reason: str) -> str:
    if reason == "gate_requires_input":
        return "The AIOS Gate held provider execution because required input is missing."
    if reason == "requires_current_external_source":
        return "The AIOS Gate classified this as current information and requires a CapabilityOS current-source route."
    if reason == "gate_answer":
        return "The AIOS Gate answered this architecture question directly and held provider execution."
    if substrate == "hive_flow":
        return "I classified this as multi-step work, so the next executable path is Hive orchestration with contract/dispatch evidence."
    if reason == "operator_override":
        return f"I will respect your override and route this turn through {substrate}."
    if intent == "cheap_single_turn":
        return f"I routed this as a lightweight conversation turn through {substrate}."
    return f"I routed this through {substrate} using the current CapabilityOS recommendation."


def recommended_next(message: str, substrate: str, intent: str) -> str:
    if substrate == "gate_clarification":
        return "Next step: tell me the location, then AIOS can route this through a current-info capability instead of guessing."
    if substrate == "capability_route_required":
        return "Next step: use or attach a current-info provider route so AIOS can verify the answer with source evidence."
    if substrate == "hive_flow" or intent == "multi_step" or wants_action(message):
        return "Next step: promote this conversation into a reviewed session envelope or contract before execution."
    if wants_status(message):
        return "Next step: inspect the Agent Work panel for the latest envelope, artifacts, and blockers."
    return "Next step: keep talking here, or ask me to turn this into a goal when you want execution."


def assistant_text(
    root: Path,
    message: str,
    substrate: str,
    intent: str,
    reason: str,
    memory: dict[str, Any],
    invocation: dict[str, Any],
    gate: dict[str, Any],
    genesis: dict[str, Any] | None = None,
) -> str:
    lines: list[str] = []
    if gate.get("decision") == "clarify_location":
        lines.append("이건 현재 날씨 정보라 local LLM이 추측해서 답하면 안 돼.")
        lines.append("어느 지역 날씨인지 알려줘. 지역이 오면 AIOS Gate가 CapabilityOS의 current-info/weather route로 넘겨서 확인해야 해.")
    elif gate.get("decision") == "require_current_info_route":
        lines.append("이건 최신/현재 정보 질문이라 AIOS Gate가 일반 대화 답변으로 처리하지 않고 외부 근거 route가 필요하다고 판단했어.")
    elif gate.get("decision") == "answer_architecture":
        lines.append("가능해. provided chatbot, Codex CLI, Claude CLI, local LLM은 AIOS에 붙는 provider substrate로 흡수할 수 있어.")
        lines.append(
            "다만 필요한 것은 단순 Agent 하나가 아니라 Gate/Chair Agent 계층이야. 이 Gate가 네가 지금 Codex에게 맡기는 판단처럼 "
            "MemoryOS context, CapabilityOS tool/search route, GenesisOS divergence, Hive execution 여부를 먼저 결정한 뒤 provider를 부려야 해."
        )
        lines.append(f"현재 Gate Chair runtime 상태: {gate_chair_runtime_summary(root)}")
        lines.append(
            "그래서 지금 답변이 provider급 자유 대화처럼 느껴지지 않으면, 문제는 AIOS 원리 부재가 아니라 "
            "Chair runtime과 품질 평가 루프가 아직 약한 거야."
        )
        lines.append("즉 user -> AIOS Gate -> OS routing -> provider substrate 순서가 되어야 하고, provider가 AIOS 자체를 대체하면 안 돼.")
    elif wants_identity(message):
        lines.append(
            "나는 AIOS야. myworld control plane 위에서 Hive Mind, MemoryOS, CapabilityOS, GenesisOS를 묶어 "
            "목표를 기억, 도구 라우팅, 세계선 검토, 실행 계획, 계약/dispatch로 바꾸는 로컬 운영 인터페이스야."
        )
        lines.append(
            "이 창에서 보이는 나는 특정 provider 하나가 아니라 Codex, Claude, Ollama 같은 provider substrate를 "
            "필요에 따라 부리고 기록하는 AIOS 대화 표면이야."
        )
    elif wants_negative_evidence_question(message):
        lines.extend(negative_evidence_answer(memory))
    elif wants_genesis_friction_question(message):
        lines.extend(genesis_friction_answer(genesis))
    elif wants_memory_question(message):
        lines.extend(memory_answer(memory))
    elif wants_greeting(message):
        lines.append("안녕. AIOS와 직접 대화하는 창구가 연결되어 있어.")
    elif wants_action(message):
        lines.append("이건 실행 가능한 작업 후보로 볼 수 있어.")
        lines.append("AIOS에서는 이 대화를 바로 session이나 contract로 승격한 뒤, Hive orchestration이 실행하고 MemoryOS/CapabilityOS/GenesisOS가 옆에서 보조하는 흐름으로 넘기는 게 맞아.")
        frictions = [item for item in (genesis or {}).get("frictions") or [] if isinstance(item, dict)]
        if frictions:
            first = frictions[0]
            lines.append(f"GenesisOS가 먼저 건드린 불편함은 이거야: {strip_terminal_punctuation(first.get('discomfort'))}.")
            lines.append(f"그래서 필요한 다음 질문은: {strip_terminal_punctuation(first.get('need'))}.")
    elif wants_status(message):
        lines.append("현재 AIOS 상태를 대화 턴으로 정리할게.")
    else:
        lines.append("받았어. 이 대화 턴을 AIOS 라우터로 처리했어.")

    return "\n".join(lines)


def operating_receipt(
    message: str,
    substrate: str,
    intent: str,
    reason: str,
    memory: dict[str, Any],
    invocation: dict[str, Any],
    genesis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    invocation_status = invocation.get("overall_status")
    stop_conditions = invocation.get("stop_conditions_triggered") or []
    return {
        "route_summary": describe_route(substrate, intent, reason),
        "memory_summary": describe_memory(memory),
        "genesis_summary": describe_genesis(genesis),
        "session_status": invocation_status,
        "stop_conditions": [str(item) for item in stop_conditions],
        "next_step": recommended_next(message, substrate, intent),
    }


def write_memory_draft(
    chat_dir: Path,
    turn_id: str,
    message: str,
    response: str,
    conversation_id: str,
    genesis: dict[str, Any] | None = None,
    genesis_ref: str | None = None,
) -> dict[str, Any]:
    state = {
        "schema_version": "aios.chat.run_state.v1",
        "run_id": conversation_id,
        "user_request": message,
        "project": "AIOS",
        "phase": "chat",
        "status": "draft",
        "created_at": now_iso(),
    }
    write_json(chat_dir / "run_state.json", state)
    draft = {
        "type": "chat_turn_summary",
        "origin": "aios_chat",
        "status": "draft",
        "project": "AIOS",
        "confidence": 0.72,
        "conversation_id": conversation_id,
        "content": f"User asked: {message[:500]}\nAIOS replied: {response[:500]}",
        "raw_refs": ["messages.jsonl", "cost.json"],
        "provenance": {
            "source": "aios_chat",
            "message_ref": "messages.jsonl",
            "created_at": now_iso(),
        },
    }
    path = chat_dir / "memory_drafts.json"
    payload = read_json(path)
    if not isinstance(payload, dict):
        payload = {"schema_version": MEMORY_DRAFT_SCHEMA, "memory_drafts": []}
    drafts = payload.setdefault("memory_drafts", [])
    extra_ids: list[str] = []
    if isinstance(drafts, list):
        drafts.append(draft)
        frictions = [item for item in (genesis or {}).get("frictions") or [] if isinstance(item, dict)]
        if frictions:
            friction_lines = []
            for item in frictions[:3]:
                branch = item.get("branch_id") or item.get("type") or "branch"
                discomfort = strip_terminal_punctuation(item.get("discomfort"))
                need = strip_terminal_punctuation(item.get("need"))
                friction_lines.append(f"- {branch}: {discomfort} -> {need}")
            friction_draft = {
                "type": "genesis_friction_signal",
                "origin": "aios_chat_genesis",
                "status": "draft",
                "project": "AIOS",
                "confidence": 0.67,
                "conversation_id": conversation_id,
                "content": "GenesisOS projected discomfort/need signal:\n" + "\n".join(friction_lines),
                "raw_refs": [ref for ref in ["messages.jsonl", "gate_decisions", genesis_ref] if ref],
                "provenance": {
                    "source": "aios_chat",
                    "genesis_authority": genesis.get("authority") if isinstance(genesis, dict) else None,
                    "genesis_ref": genesis_ref,
                    "created_at": now_iso(),
                },
            }
            drafts.append(friction_draft)
            extra_ids.append(f"chatdraft_{turn_id}_genesis")
    write_json(path, payload)
    return {"id": f"chatdraft_{turn_id}", "extra_draft_ids": extra_ids, **draft}


def update_cost(chat_dir: Path, turn: dict[str, Any]) -> dict[str, Any]:
    path = chat_dir / "cost.json"
    payload = read_json(path)
    if not isinstance(payload, dict):
        payload = {
            "schema_version": COST_SCHEMA,
            "currency": "USD",
            "total_tokens_in": 0,
            "total_tokens_out": 0,
            "total_cost_usd": 0.0,
            "turns": [],
        }
    payload["total_tokens_in"] = int(payload.get("total_tokens_in") or 0) + int(turn["tokens_in"])
    payload["total_tokens_out"] = int(payload.get("total_tokens_out") or 0) + int(turn["tokens_out"])
    payload["total_cost_usd"] = round(float(payload.get("total_cost_usd") or 0.0) + float(turn["cost_usd"]), 6)
    payload.setdefault("turns", []).append(turn)
    write_json(path, payload)
    return payload


def route_turn(root: Path, message: str, conversation_id: str) -> dict[str, Any]:
    if not message.strip():
        raise SystemExit("message is required")
    if len(message) > MAX_MESSAGE_CHARS:
        raise SystemExit(f"message too large; max {MAX_MESSAGE_CHARS} chars")
    override, clean_message = strip_override(message)
    if not clean_message:
        raise SystemExit("message is required after override")

    chat_dir = conversation_dir(root, conversation_id)
    messages_path = chat_dir / "messages.jsonl"
    history = read_jsonl(messages_path)
    invocation = build_invocation(root, clean_message, conversation_id)
    capability_payload = load_capability_payload(root, invocation)
    genesis_payload = load_genesis_payload(root, invocation)
    genesis = genesis_friction_projection(genesis_payload)
    gate_pack = load_gate_pack(root)
    gate = build_gate_decision(clean_message, override)
    projection = gate_pack_projection(gate_pack)
    if projection:
        gate["gate_pack"] = projection
    if genesis:
        gate["genesis_friction"] = genesis
    memory = memory_context(root, clean_message)
    substrate, intent, reason, route_audit = choose_substrate(clean_message, override, capability_payload, gate, memory)
    if route_audit:
        gate["capability_route_audit"] = route_audit
    injection = aios_few_shot_injector.inject_prompt(root, clean_message, user="founder", substrate=substrate, limit=3)

    should_execute_provider = True
    base_response = assistant_text(root, clean_message, substrate, intent, reason, memory, invocation, gate, genesis)
    receipt = operating_receipt(clean_message, substrate, intent, reason, memory, invocation, genesis)
    if (
        substrate in NON_EXECUTING_SUBSTRATES
        or wants_greeting(message)
        or wants_identity(message)
        or wants_status(message)
        or (wants_negative_evidence_question(clean_message) and memory.get("negative_evidence"))
        or (wants_genesis_friction_question(clean_message) and genesis)
        or (wants_memory_question(clean_message) and memory.get("selected_memories"))
    ):
        should_execute_provider = False

    provider_prompt = _provider_prompt_payload(clean_message, injection, memory, gate)
    provider_output = ""
    provider_meta: dict[str, Any] = {"status": "not_executed"}
    provider_turn_path: str | None = None
    gate_chair_turn_path: str | None = None
    gate_chair_status: dict[str, Any] = {"attempted": False, "executed": False, "status": "not_attempted"}
    stop_conditions = list(invocation.get("stop_conditions_triggered") or [])
    if should_execute_provider:
        executed, provider_output, provider_meta = execute_provider_turn(root, substrate, provider_prompt)
        provider_turn_id = f"chatprov_{len(history)}_{stable_id(clean_message)}"
        provider_payload = {
            "schema_version": "aios.chat.provider_turn.v1",
            "turn_id": provider_turn_id,
            "substrate": substrate,
            "executed": executed,
            "provider_meta": provider_meta,
            "prompt_preview": provider_prompt[:200],
            "raw_output_preview": (provider_output or "")[:200],
            "created_at": now_iso(),
        }
        append_jsonl(chat_dir / "provider_turns.jsonl", provider_payload)
        provider_turn_path = f".aios/chat/{slugify(conversation_id)}/provider_turns.jsonl"
        if executed:
            response = f"{provider_output}\n\n---\n{base_response}"
            stop_conditions = stop_conditions[:]
        else:
            if provider_meta.get("status") in {
                "command_unavailable",
                "provider_timeout",
                "provider_execution_exception",
            }:
                response = base_response
            else:
                response = f"{base_response}\n\nProvider turn failed: {provider_meta.get('status')}. Proceeding with control-plane response."
            if provider_meta.get("status") not in {
                "not_executing",
                "command_unavailable",
                "provider_timeout",
                "provider_execution_exception",
            }:
                stop_conditions.append("provider_execution_failed")
        if not executed and provider_meta.get("status") in {"provider_backpressure", "provider_access_denied"}:
            stop_conditions.append(provider_meta.get("status"))
    else:
        response = base_response
        if gate_chair_allowed(root, clean_message, gate, memory):
            chair_prompt = gate_chair_prompt(clean_message, base_response, memory, gate, genesis)
            chair_executed, chair_output, chair_meta = execute_gate_chair_turn(root, chair_prompt)
            chair_turn_id = f"gatechair_{len(history)}_{stable_id(clean_message)}"
            chair_payload = {
                "schema_version": "aios.chat.gate_chair_turn.v1",
                "turn_id": chair_turn_id,
                "executed": chair_executed,
                "chair_meta": chair_meta,
                "prompt_preview": chair_prompt[:200],
                "raw_output_preview": (chair_output or "")[:200],
                "created_at": now_iso(),
            }
            append_jsonl(chat_dir / "gate_chair_turns.jsonl", chair_payload)
            gate_chair_turn_path = f".aios/chat/{slugify(conversation_id)}/gate_chair_turns.jsonl"
            gate_chair_status = {
                "attempted": True,
                "executed": chair_executed,
                "status": chair_meta.get("status", "unknown"),
                "mode": (chair_meta.get("meta") or {}).get("mode"),
                "model": (chair_meta.get("meta") or {}).get("model"),
            }
            if chair_executed:
                response = chair_output

    turn_id = stable_id(f"{conversation_id}:{len(history)}:{clean_message}:{now_iso()}")
    created_at = now_iso()
    gate = {**gate, "turn_id": turn_id, "created_at": created_at}
    gate_path = chat_dir / "gate_decisions" / f"{turn_id}.json"
    write_json(gate_path, gate)

    user_row = {
        "schema_version": MESSAGE_SCHEMA,
        "turn_id": turn_id,
        "role": "user",
        "content": clean_message,
        "created_at": created_at,
        "override": override,
    }
    assistant_row = {
        "schema_version": MESSAGE_SCHEMA,
        "turn_id": turn_id,
        "role": "assistant",
        "content": response,
        "created_at": now_iso(),
        "substrate": substrate,
        "intent": intent,
        "route_reason": reason,
        "patterns_injected": injection.get("patterns_injected") or [],
    }
    append_jsonl(messages_path, user_row)
    append_jsonl(messages_path, assistant_row)

    tokens_in = estimate_tokens(clean_message) + sum(estimate_tokens(str(row.get("content") or "")) for row in history[-8:])
    tokens_out = estimate_tokens(response)
    cost_usd = 0.0 if substrate in {"local_llm", "ollama_qwen", "hive_flow", "aios_gate", "gate_clarification", "capability_route_required"} else round((tokens_in + tokens_out) * 0.000002, 6)
    cost = update_cost(
        chat_dir,
        {
            "turn_id": turn_id,
            "created_at": created_at,
            "substrate": substrate,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_usd": cost_usd,
        },
    )
    artifact_paths = {
        "messages": relative(messages_path, root),
        "cost": relative(chat_dir / "cost.json", root),
        "memory_drafts": relative(chat_dir / "memory_drafts.json", root),
        "run_state": relative(chat_dir / "run_state.json", root),
        "gate_decision": relative(gate_path, root),
        "pattern_injection_audit": injection.get("audit_path"),
    }
    invocation_paths = invocation.get("artifact_paths") or {}
    if isinstance(invocation_paths, dict):
        artifact_paths["invocation_receipt"] = invocation_paths.get("receipt")
        artifact_paths["genesis_branches"] = invocation_paths.get("genesis")
        artifact_paths["capability_route"] = invocation_paths.get("capability")
        artifact_paths["memory_context_pack"] = invocation_paths.get("memory_context_pack")
    if provider_turn_path:
        artifact_paths["provider_turns"] = provider_turn_path
    if gate_chair_turn_path:
        artifact_paths["gate_chair_turns"] = gate_chair_turn_path
    draft = write_memory_draft(
        chat_dir,
        turn_id,
        clean_message,
        response,
        conversation_id,
        genesis=genesis,
        genesis_ref=artifact_paths.get("genesis_branches"),
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "status": "routed",
        "conversation_id": slugify(conversation_id),
        "turn_id": turn_id,
        "created_at": created_at,
        "chosen_substrate": substrate,
        "intent": intent,
        "route_reason": reason,
        "gate_decision": gate,
        "genesis_friction": genesis,
        "operator_override": override,
        "message_count": len(history) + 2,
        "response": response,
        "operating_receipt": receipt,
        "patterns_injected": injection.get("patterns_injected") or [],
        "memory_context": memory,
        "memory_draft": {"id": draft["id"], "status": draft["status"], "extra_draft_ids": draft.get("extra_draft_ids", [])},
        "cost": {
            "turn_tokens_in": tokens_in,
            "turn_tokens_out": tokens_out,
            "turn_cost_usd": cost_usd,
            "total_cost_usd": cost["total_cost_usd"],
        },
        "artifact_paths": artifact_paths,
        "provider_turn": provider_turn_path,
        "gate_chair_turn": gate_chair_turn_path,
        "gate_chair_status": gate_chair_status,
        "invocation_status": invocation.get("overall_status"),
        "injected_prompt_hash": injection.get("prompt_hash"),
        "stop_conditions_triggered": stop_conditions,
    }


def relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--conversation", default="default")
    parser.add_argument("--message", required=True)
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = route_turn(args.root.resolve(), args.message, args.conversation)
    if args.json:
        print(canonical_json(result))
    else:
        print(result["response"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

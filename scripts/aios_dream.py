#!/usr/bin/env python3
"""aios dream — the AIOS wake/consolidation cycle (the "dream" organ).

This is the slow loop the human operator currently runs by hand. One wake:

  1. gather a compact digest of accumulated experience
     (MemoryOS draft count, recent ledger entries, helper observations,
      recent contracts)
  2. call the consolidation specialist helper (local LLM) — the dream
  3. write a dream report: recurring schemas, stale records, open questions
     — ALL proposals, nothing accepted (DNA Invariant 2)
  4. turn open questions into a research queue (each paired with a
     CapabilityOS web-research plan) — the input to the search→absorb organ
  5. propose next actions for the deterministic round controller

Boundary: the dream organ PROPOSES. It never accepts memory, never closes
contracts, never overrides an agent. The deterministic kernel + operator
review decide what proposals become. The local LLM is a clerk, not a chief.

This is what lets AIOS turn without the operator being the consolidation
pathway — the autopoietic threshold organ.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CONSOLIDATE_HELPER = "cap_helper_consolidate"
DREAM_DIR = ".aios/dream"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def now_stamp() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y%m%dT%H%M%S")


def tail_lines(path: Path, n: int) -> list[str]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return lines[-n:]


def gather_digest(root: Path) -> dict[str, Any]:
    """Compact digest of AIOS accumulated experience — kept small for a local LLM."""
    digest: dict[str, Any] = {"generated_at": now_iso()}

    # MemoryOS draft count
    memoryos = root / "memoryOS"
    draft_count = None
    if memoryos.exists():
        proc = subprocess.run(
            [sys.executable, "-m", "memoryos", "drafts", "list", "--status", "draft"],
            cwd=memoryos, capture_output=True, text=True,
        )
        if proc.returncode == 0:
            for line in proc.stdout.splitlines():
                if "found" in line and "draft" in line.lower():
                    digest["memoryos_drafts_line"] = line.strip()
                    break
    digest.setdefault("memoryos_drafts_line", "(memoryOS draft count unavailable)")

    # recent ledger entries
    ledger = root / "docs" / "AIOS_AGENT_LEDGER.md"
    ledger_heads = [ln for ln in tail_lines(ledger, 400) if ln.startswith("## ")][-6:]
    digest["recent_ledger"] = ledger_heads

    # helper observations
    obs = root / ".aios" / "helpers" / "observations.jsonl"
    digest["helper_observation_count"] = len(tail_lines(obs, 10000))

    # recent contracts
    contracts_dir = root / "docs" / "contracts"
    recent_contracts: list[str] = []
    if contracts_dir.exists():
        files = sorted(contracts_dir.glob("ASC-*.md"))[-8:]
        for f in files:
            recent_contracts.append(f.stem)
    digest["recent_contracts"] = recent_contracts

    # self-model — AIOS dreams with a model of itself: its condition and its
    # own open gaps are part of the experience it consolidates.
    self_model = root / "scripts" / "aios_self_model.py"
    if self_model.exists():
        proc = subprocess.run(
            [sys.executable, self_model.as_posix(), "--root", root.as_posix(),
             "build", "--json"],
            cwd=root, capture_output=True, text=True, timeout=150,
        )
        try:
            sm = json.loads(proc.stdout)
            digest["self_assessment"] = sm.get("self_assessment", "")
            digest["self_open_gaps"] = sm.get("open_gaps", [])
        except (ValueError, OSError):
            digest.setdefault("self_assessment", "(self-model unavailable)")
            digest.setdefault("self_open_gaps", [])
    else:
        digest["self_assessment"] = "(self-model organ not present)"
        digest["self_open_gaps"] = []

    return digest


def digest_to_text(digest: dict[str, Any]) -> str:
    lines = [
        "AIOS ACCUMULATED EXPERIENCE DIGEST",
        f"generated: {digest['generated_at']}",
        f"memoryOS: {digest['memoryos_drafts_line']}",
        f"helper invocations recorded: {digest['helper_observation_count']}",
        "",
        "recent ledger entries:",
    ]
    lines += [f"  {h}" for h in digest.get("recent_ledger", [])] or ["  (none)"]
    lines += ["", "recent contracts:"]
    lines += [f"  {c}" for c in digest.get("recent_contracts", [])] or ["  (none)"]
    if digest.get("self_assessment"):
        lines += ["", "AIOS self-model (how AIOS sees itself now):",
                  f"  {digest['self_assessment']}"]
        for g in digest.get("self_open_gaps", []):
            lines.append(f"  open gap: {g}")
    return "\n".join(lines)


def call_consolidation_helper(root: Path, digest_text: str) -> tuple[bool, str]:
    proc = subprocess.run(
        [sys.executable, (root / "scripts" / "aios_helper.py").as_posix(),
         "--root", root.as_posix(), "run", "--helper", CONSOLIDATE_HELPER,
         "--input", digest_text, "--json"],
        cwd=root, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        return False, (proc.stderr or proc.stdout or "consolidation helper failed").strip()
    try:
        payload = json.loads(proc.stdout)
        return True, str(payload.get("result", "")).strip()
    except (ValueError, KeyError) as exc:
        return False, f"could not parse helper output: {exc}"


def extract_open_questions(consolidation_text: str) -> list[str]:
    """Pull OPEN QUESTIONS from the helper's output — handles both formats:
    inline ("OPEN QUESTIONS — <text>") and following-line bullets."""
    questions: list[str] = []
    in_section = False
    for raw in consolidation_text.splitlines():
        line = raw.strip()
        if not line:
            continue
        upper = line.upper()
        if "OPEN QUESTION" in upper:
            in_section = True
            # capture any inline content on the header line itself
            after = re.sub(r"(?i)\bopen questions?\b", "", line, count=1)
            after = after.lstrip(" —–-:.)*#(0123456789").strip()
            if after and len(after) > 8:
                # one line may pack several questions separated by ; or  /
                for part in re.split(r"\s*;\s*", after):
                    part = part.strip()
                    if len(part) > 8:
                        questions.append(part)
            continue
        if in_section:
            if "RECURRING SCHEMA" in upper or upper.lstrip("(").startswith("STALE") \
               or re.match(r"^\(?[12]\)?[\s.)]", line):
                break
            cleaned = line.lstrip("-*0123456789.) ").strip()
            if len(cleaned) > 8:
                questions.append(cleaned)
    return questions[:10]


def web_plan_for(root: Path, question: str) -> dict[str, Any]:
    """Ask CapabilityOS for a recommendation-only web-research plan."""
    capabilityos = root / "CapabilityOS"
    proc = subprocess.run(
        [sys.executable, "-m", "capabilityos.cli", "web-route", "--task", question, "--json"],
        cwd=capabilityos, capture_output=True, text=True,
    )
    if proc.returncode == 0:
        try:
            return {"question": question, "plan": json.loads(proc.stdout)}
        except ValueError:
            pass
    return {"question": question, "plan": None}


CLASSIFY_HELPER = "cap_helper_classify_vision_level"


def triage_questions(root: Path, questions: list[str]) -> dict[str, Any]:
    """Boundary 2 — the kernel decides which surfaced questions it pursues
    autonomously vs escalates. Each open question is classified VISION vs
    OPERATOR via the classify helper (a pre-filter). VISION → escalate to
    founder; OPERATOR → autonomous research. This is progressive autonomy:
    self-handle the routine, escalate the vital (2026 guardrails consensus)."""
    operator_qs: list[str] = []
    vision_qs: list[dict[str, str]] = []
    for q in questions:
        proc = subprocess.run(
            [sys.executable, (root / "scripts" / "aios_helper.py").as_posix(),
             "--root", root.as_posix(), "run", "--helper", CLASSIFY_HELPER,
             "--input", q, "--json"],
            cwd=root, capture_output=True, text=True,
        )
        verdict = "OPERATOR"
        reason = ""
        if proc.returncode == 0:
            try:
                out = json.loads(proc.stdout).get("result", "")
                head = out.strip().upper()
                if "VISION" in head.split(".")[0].split("\n")[0]:
                    verdict = "VISION"
                reason = out.strip()[:160]
            except (ValueError, KeyError):
                pass
        if verdict == "VISION":
            vision_qs.append({"question": q, "classifier_reason": reason})
        else:
            operator_qs.append(q)
    return {"operator_questions": operator_qs, "vision_questions": vision_qs}


def run_research_and_absorb(root: Path) -> dict[str, Any]:
    """search→absorb tail: fetch the research queue, absorb notes as MemoryOS drafts.

    Key-gated — runs only if a Tavily key is present. Skipped cleanly otherwise
    (the research queue still stands for operator-assisted fetch)."""
    key_present = (root / ".aios" / "secrets" / "tavily.key").exists()
    import os

    if not key_present and not os.environ.get("TAVILY_API_KEY"):
        return {"status": "skipped", "reason": "no_tavily_key — research queue left for operator-assisted fetch"}

    fetch = subprocess.run(
        [sys.executable, (root / "scripts" / "aios_research_fetch.py").as_posix(),
         "--root", root.as_posix(), "--json"],
        cwd=root, capture_output=True, text=True,
    )
    fetched = 0
    notes: list[str] = []
    try:
        fr = json.loads(fetch.stdout)
        fetched = fr.get("fetched", 0)
        notes = [r["note"] for r in fr.get("receipts", []) if r.get("ok") and r.get("note")]
    except (ValueError, KeyError):
        return {"status": "fetch_failed", "reason": (fetch.stderr or "unparseable").strip()[:200]}

    absorbed = 0
    if notes:
        memoryos = root / "memoryOS"
        imp = subprocess.run(
            [sys.executable, "-m", "memoryos", "import",
             *[("../" + n) for n in notes], "--json"],
            cwd=memoryos, capture_output=True, text=True,
        )
        absorbed = len(notes) if imp.returncode == 0 else 0
    return {"status": "ok", "fetched": fetched, "absorbed_notes": absorbed,
            "boundary": "research notes imported as MemoryOS DRAFTS — review required"}


def embedding_coverage(root: Path) -> dict[str, Any]:
    """Read MemoryOS embedding coverage — the dream phase-1 progress signal."""
    memoryos = root / "memoryOS"
    proc = subprocess.run(
        [sys.executable, "-m", "memoryos", "--root", ".", "stats", "--json"],
        cwd=memoryos, capture_output=True, text=True,
    )
    try:
        return json.loads(proc.stdout).get("embedding_coverage", {})
    except (ValueError, KeyError):
        return {}


def consolidate_memory(root: Path, budget_seconds: int = 240) -> dict[str, Any]:
    """Dream phase 1 — CLS-style memory consolidation.

    During wake, memory is appended fast and unindexed (hippocampal store).
    During dream, it is slowly embedded so it becomes semantically
    retrievable (neocortical consolidation). This is the founder's framing:
    "when memory is idle, periodically consolidate (embed) it."

    Time-boxed: each dream cycle embeds for a bounded budget; `memoryos embed`
    caches results, so already-embedded nodes are skipped and coverage
    converges across cycles instead of blocking one cycle indefinitely."""
    memoryos = root / "memoryOS"
    if not memoryos.exists():
        return {"status": "skipped", "reason": "no memoryOS"}
    before = embedding_coverage(root)
    timed_out = False
    try:
        subprocess.run(
            [sys.executable, "-m", "memoryos", "--root", ".", "embed", "--all"],
            cwd=memoryos, capture_output=True, text=True, timeout=budget_seconds,
        )
    except subprocess.TimeoutExpired:
        timed_out = True
    after = embedding_coverage(root)
    return {
        "status": "ok",
        "timed_out": timed_out,
        "coverage_before": before,
        "coverage_after": after,
        "note": "dream phase 1 — embedding consolidation; cached + time-boxed, "
                "coverage converges across cycles",
    }


def run_dream(root: Path, json_mode: bool, do_fetch: bool = True,
              consolidate_budget: int = 240) -> int:
    # Dream phase 1 — consolidate the memory append-store (embed) before the
    # consolidation helper reads the digest, so each cycle leaves memory more
    # retrievable than it found it.
    memory_consolidation = consolidate_memory(root, budget_seconds=consolidate_budget)
    digest = gather_digest(root)
    digest_text = digest_to_text(digest)
    ok, consolidation = call_consolidation_helper(root, digest_text)

    dream_dir = root / DREAM_DIR
    dream_dir.mkdir(parents=True, exist_ok=True)
    stamp = now_stamp()

    if not ok:
        report = {
            "schema": "aios.dream_report.v1",
            "status": "consolidation_failed",
            "generated_at": now_iso(),
            "reason": consolidation,
            "memory_consolidation": memory_consolidation,
            "digest": digest,
        }
        (dream_dir / f"report-{stamp}.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        if json_mode:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print(f"dream cycle FAILED: {consolidation}")
        return 1

    open_questions = extract_open_questions(consolidation)

    # Boundary 2 — the kernel triages its own surfaced questions:
    # OPERATOR-level → autonomous research; VISION-level → escalate to founder.
    triage = triage_questions(root, open_questions)
    operator_qs = triage["operator_questions"]
    vision_qs = triage["vision_questions"]
    research_queue = [web_plan_for(root, q) for q in operator_qs]

    report = {
        "schema": "aios.dream_report.v1",
        "status": "ok",
        "generated_at": now_iso(),
        "boundary": "all entries are PROPOSALS — nothing accepted; deterministic kernel + operator review decide",
        "memory_consolidation": memory_consolidation,
        "digest": digest,
        "consolidation": consolidation,
        "open_questions": open_questions,
        "triage": {
            "operator_level": operator_qs,
            "vision_level_escalated": vision_qs,
            "rule": "OPERATOR → autonomous research; VISION → founder escalation queue",
        },
        "proposed_next_actions": [
            "operator/kernel: review consolidation proposals; accept schemas via MemoryOS review",
            "search→absorb organ: autonomously researched the operator-level questions",
            "founder: review the escalation queue for vision-level questions",
        ],
    }
    report_path = dream_dir / f"report-{stamp}.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    queue = {
        "schema": "aios.research_queue.v1",
        "generated_at": now_iso(),
        "source_dream_report": report_path.name,
        "scope": "operator-level questions only — vision-level are escalated, not auto-researched",
        "items": research_queue,
    }
    queue_path = dream_dir / "research_queue.json"
    queue_path.write_text(json.dumps(queue, indent=2, ensure_ascii=False), encoding="utf-8")

    escalation = {
        "schema": "aios.escalation_queue.v1",
        "generated_at": now_iso(),
        "source_dream_report": report_path.name,
        "note": "vision-level questions the kernel will NOT act on autonomously — founder decision required",
        "items": vision_qs,
    }
    (dream_dir / "escalation_queue.json").write_text(
        json.dumps(escalation, indent=2, ensure_ascii=False), encoding="utf-8")

    # search→absorb tail: fetch the research queue and absorb notes as drafts
    research = {"status": "skipped", "reason": "fetch_disabled"} if not do_fetch \
        else run_research_and_absorb(root)
    report["research_absorb"] = research

    latest = dream_dir / "latest.json"
    latest.write_text(json.dumps({"latest_report": report_path.name,
                                  "generated_at": report["generated_at"]},
                                 indent=2, ensure_ascii=False), encoding="utf-8")
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    if json_mode:
        print(json.dumps({"status": "ok", "report": str(report_path.relative_to(root)),
                          "research_queue": str(queue_path.relative_to(root)),
                          "open_questions": len(open_questions),
                          "research_absorb": research},
                         indent=2, ensure_ascii=False))
    else:
        print(f"dream cycle complete")
        print(f"  report:         {report_path.relative_to(root)}")
        print(f"  triage:         {len(operator_qs)} operator-level (auto-research), "
              f"{len(vision_qs)} vision-level (escalated to founder)")
        print(f"  research queue: {queue_path.relative_to(root)} ({len(operator_qs)} questions)")
        print(f"  search→absorb:  {research.get('status')} "
              f"(fetched {research.get('fetched', 0)}, absorbed {research.get('absorbed_notes', 0)})")
        print("--- consolidation (proposals) ---")
        print(consolidation)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="AIOS dream — wake/consolidation cycle")
    p.add_argument("--root", default=".")
    p.add_argument("action", nargs="?", default="run", choices=["run", "latest"])
    p.add_argument("--json", action="store_true")
    p.add_argument("--no-fetch", action="store_true", help="skip the search→absorb tail")
    p.add_argument("--consolidate-budget", type=int, default=240,
                   help="seconds budgeted for dream phase-1 memory embedding")
    args = p.parse_args(argv)
    root = Path(args.root).resolve()

    if args.action == "latest":
        latest = root / DREAM_DIR / "latest.json"
        if not latest.exists():
            print("no dream cycle has run yet")
            return 1
        print(latest.read_text(encoding="utf-8"))
        return 0
    return run_dream(root, args.json, do_fetch=not args.no_fetch,
                     consolidate_budget=args.consolidate_budget)


if __name__ == "__main__":
    sys.exit(main())

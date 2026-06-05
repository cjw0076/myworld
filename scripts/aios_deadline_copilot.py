#!/usr/bin/env python3
"""AIOS outside-domain value proof: a thin vertical slice of "Deadline Copilot"
(the highest-leverage uri student-utility flow, per the 2026-06-05 multi-substrate
panel — codex ranked it #1, qwen3-coder echoed the theme).

It runs through the AIOS organism instead of hand-writing content:
  student assignments  ->  LOCAL substrate (qwen3-coder:30b) generates a dated
  action plan  ->  GenesisOS critique as a quality gate (best-effort)  ->  a
  provenance receipt (substrate id, inputs, plan, critique, timestamp).

This is the outside-value capability the operator harness + local-substrate
assetization were built for: AIOS taking real outside input and producing useful,
provenance-tracked output, on a free/private local model. NOT a uri product change
— a control-plane capability demo; the real flow belongs in uri/hivemind.

Schema: aios.deadline_copilot.v1
Usage: python scripts/aios_deadline_copilot.py [--assignments FILE.json] [--json]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "aios.deadline_copilot.v1"
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
SUBSTRATE = "qwen3-coder:30b"
GENESIS = ROOT / "GenesisOS"

SAMPLE = [
    {"course": "자료구조", "title": "과제 3: 이진탐색트리 구현", "due": "2026-06-08"},
    {"course": "선형대수", "title": "중간고사", "due": "2026-06-10"},
    {"course": "교양영어", "title": "에세이 초안 제출", "due": "2026-06-07"},
]


def generate_plan(assignments: list[dict], today: str) -> tuple[str, list[dict]]:
    prompt = (
        f"오늘은 {today}. 다음은 한 대학생의 이번 주 과제/시험 목록(JSON)이다.\n"
        f"{json.dumps(assignments, ensure_ascii=False)}\n\n"
        "먼저 기계가 읽을 스케줄을 fenced ```json 블록으로 출력하라: "
        '[{"date":"YYYY-MM-DD","course":"<입력의 course 그대로>","task":"..."}] '
        "— 오늘부터 각 과제 마감일 이내로 배분(course 이름은 입력과 정확히 동일하게). "
        "그 다음 사람이 읽을 한국어 행동계획을 날짜별로, 각 항목에 '왜 지금' 한 줄로 "
        "간결하게. 마감 역산으로 급한 것부터."
    )
    body = json.dumps({"model": SUBSTRATE, "prompt": prompt, "stream": False}).encode()
    req = urllib.request.Request(OLLAMA_URL, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        text = json.loads(resp.read()).get("response", "").strip()
    return text, extract_schedule(text)


def extract_schedule(text: str) -> list[dict]:
    """Leniently pull the first JSON array of schedule entries out of the model
    output. Returns [] if absent/unparseable — verification then flags it."""
    import re

    m = re.search(r"\[\s*\{.*?\}\s*\]", text, re.S)
    if not m:
        return []
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return []
    return [d for d in data if isinstance(d, dict) and d.get("course") and d.get("date")]


def verify_schedule(schedule: list[dict], assignments: list[dict], today: str) -> dict:
    """Deterministic date-consistency check — the RIGHT tool for date logic, which
    LLMs get wrong (qwen muddled a due-date). LLM plans; code verifies."""
    by_course: dict[str, list[str]] = {}
    for e in schedule:
        by_course.setdefault(str(e["course"]), []).append(str(e["date"]))
    violations = []
    for a in assignments:
        course, due = a["course"], a["due"]
        dates = sorted(by_course.get(course, []))
        if not dates:
            violations.append({"course": course, "issue": "not scheduled"})
            continue
        if dates[-1] > due:  # ISO dates compare lexicographically = chronologically
            violations.append({"course": course, "issue": f"last work {dates[-1]} is AFTER due {due}"})
        if dates[0] < today:
            violations.append({"course": course, "issue": f"work {dates[0]} is BEFORE today {today}"})
    return {"ok": not violations, "violations": violations, "courses_scheduled": len(by_course)}


def genesis_critique(plan: str) -> dict:
    """Best-effort GenesisOS prompt-prison critique of the plan as a quality gate.
    Note: the critic's `--text` is a FILE PATH (not inline text), so write a temp
    file first. (memory: project_aios_5os_state critic CLI quirk.)"""
    try:
        import tempfile

        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as fh:
            fh.write(plan)
            tmp = fh.name
        r = subprocess.run(
            ["python", "-m", "genesisos.cli", "critic", "--text", tmp, "--json"],
            cwd=GENESIS, capture_output=True, text=True, timeout=60,
        )
        Path(tmp).unlink(missing_ok=True)
        if r.returncode == 0:
            try:
                return {"status": "ok", "findings": json.loads(r.stdout)}
            except json.JSONDecodeError:
                return {"status": "ok", "output": r.stdout.strip()[:800]}
        return {"status": "unavailable", "detail": r.stderr.strip()[:200]}
    except Exception as exc:  # organ optional — never break the value flow
        return {"status": "unavailable", "detail": str(exc)[:200]}


def run(assignments: list[dict], today: str) -> dict:
    plan, schedule = generate_plan(assignments, today)
    verification = verify_schedule(schedule, assignments, today)
    critique = genesis_critique(plan)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": today,
        "substrate": SUBSTRATE,
        "substrate_note": "local ollama on dual RTX 5090 — free, private, no provider dependency",
        "assignments": assignments,
        "plan": plan,
        "schedule": schedule,
        "verification": verification,
        "genesis_critique": critique,
        "provenance": "local gen + deterministic date-verify; inputs + substrate id recorded for MemoryOS draft",
    }


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--assignments", type=Path, help="JSON list of {course,title,due}")
    p.add_argument("--today", default=None, help="YYYY-MM-DD (default: system date)")
    p.add_argument("--json", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    assignments = json.loads(args.assignments.read_text()) if args.assignments else SAMPLE
    today = args.today or time.strftime("%Y-%m-%d")
    receipt = run(assignments, today)

    out_dir = ROOT / ".aios" / "copilot"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%S")
    (out_dir / f"receipt-{stamp}.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if args.json:
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
    else:
        v = receipt["verification"]
        print(f"=== Deadline Copilot (substrate: {receipt['substrate']}, {today}) ===\n")
        print(receipt["plan"])
        verdict = "PASS" if v["ok"] else "FLAGGED " + "; ".join(
            f"{x['course']}: {x['issue']}" for x in v["violations"]
        )
        print(f"\n[date-verify: {verdict}] [genesis: {receipt['genesis_critique']['status']}] "
              f"[receipt: .aios/copilot/receipt-{stamp}.json]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

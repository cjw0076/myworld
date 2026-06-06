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
from pathlib import Path

import aios_substrate_router as router

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "aios.deadline_copilot.v1"
SUBSTRATE = "qwen3-coder:30b"
# churn-resilient fallback chain (preferred → backups), all local
SUBSTRATE_CHAIN = [SUBSTRATE, "qwen3:30b-a3b", "deepseek-coder-v2:16b"]
GENESIS = ROOT / "GenesisOS"

SAMPLE = [
    {"course": "자료구조", "title": "과제 3: 이진탐색트리 구현", "due": "2026-06-08"},
    {"course": "선형대수", "title": "중간고사", "due": "2026-06-10"},
    {"course": "교양영어", "title": "에세이 초안 제출", "due": "2026-06-07"},
]


def generate_plan(
    assignments: list[dict], today: str, prior_context: str = ""
) -> tuple[str, list[dict], str | None, list[dict]]:
    context_line = f"[지난 맥락] {prior_context}\n" if prior_context else ""
    prompt = (
        f"{context_line}"
        f"오늘은 {today}. 다음은 한 대학생의 이번 주 과제/시험 목록(JSON)이다.\n"
        f"{json.dumps(assignments, ensure_ascii=False)}\n\n"
        "먼저 기계가 읽을 스케줄을 fenced ```json 블록으로 출력하라: "
        '[{"date":"YYYY-MM-DD","course":"<입력의 course 그대로>","task":"..."}] '
        "— 오늘부터 각 과제 마감일 이내로 배분(course 이름은 입력과 정확히 동일하게). "
        "그 다음 사람이 읽을 한국어 행동계획을 날짜별로, 각 항목에 '왜 지금' 한 줄로 "
        "간결하게. 마감 역산으로 급한 것부터."
    )
    res = router.generate(prompt, prefer=SUBSTRATE_CHAIN)
    text = res["text"]
    return text, extract_schedule(text), res["substrate"], res["trail"]


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


def run(assignments: list[dict], today: str, prior_context: str = "") -> dict:
    plan, schedule, served, trail = generate_plan(assignments, today, prior_context)
    verification = verify_schedule(schedule, assignments, today)
    critique = genesis_critique(plan)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": today,
        "substrate": served,
        "routing_trail": trail,
        "prior_context": prior_context,
        "substrate_note": "churn-resilient local fallback chain on dual RTX 5090 — free, private, no provider dependency",
        "assignments": assignments,
        "plan": plan,
        "schedule": schedule,
        "verification": verification,
        "genesis_critique": critique,
        "provenance": "local gen + deterministic date-verify; inputs + substrate id recorded for MemoryOS draft",
    }


# --- real-input adapters (production gap #1): a student exports their LMS /
# calendar deadlines as .ics, or a simple CSV — no external deps. ---
def _unfold(text: str) -> list[str]:
    """RFC5545 line unfolding: continuation lines begin with space/tab."""
    out: list[str] = []
    for line in text.splitlines():
        if line[:1] in (" ", "\t") and out:
            out[-1] += line[1:]
        else:
            out.append(line)
    return out


def _ical_date(val: str) -> str:
    digits = "".join(ch for ch in val if ch.isdigit())[:8]
    return f"{digits[0:4]}-{digits[4:6]}-{digits[6:8]}" if len(digits) >= 8 else val.strip()


def parse_ical(text: str) -> list[dict]:
    assignments: list[dict] = []
    cur: dict = {}
    in_event = False
    for line in _unfold(text):
        s = line.strip()
        if s == "BEGIN:VEVENT":
            in_event, cur = True, {}
        elif s == "END:VEVENT":
            if in_event and cur.get("title") and cur.get("due"):
                cur.setdefault("course", cur["title"][:24])
                assignments.append(cur)
            in_event, cur = False, {}
        elif not in_event:
            continue
        elif s.startswith("SUMMARY:"):
            cur["title"] = s[len("SUMMARY:"):].strip()
        elif s.startswith("DTSTART"):
            cur["due"] = _ical_date(s.split(":", 1)[1]) if ":" in s else cur.get("due")
        elif s.startswith("CATEGORIES:"):
            cur["course"] = s[len("CATEGORIES:"):].split(",")[0].strip()
    return assignments


def parse_csv(text: str) -> list[dict]:
    import csv
    import io

    out: list[dict] = []
    for row in csv.DictReader(io.StringIO(text)):
        low = {(k or "").lower().strip(): (v or "").strip() for k, v in row.items()}
        title = low.get("title") or low.get("assignment") or low.get("summary")
        due = low.get("due") or low.get("date") or low.get("deadline")
        if title and due:
            out.append({"course": low.get("course") or title[:24], "title": title, "due": due[:10]})
    return out


def load_assignments(args: argparse.Namespace) -> list[dict]:
    if getattr(args, "ical", None):
        return parse_ical(args.ical.read_text(encoding="utf-8"))
    if getattr(args, "csv", None):
        return parse_csv(args.csv.read_text(encoding="utf-8"))
    if args.assignments:
        return json.loads(args.assignments.read_text())
    return SAMPLE


def student_dir(student: str | None) -> Path:
    return ROOT / ".aios" / "copilot" / (student or "_default")


def load_prior_context(directory: Path) -> str:
    """One-line continuity summary from a student's prior receipts — per-student
    memory, uri's '나를 아는 에이전트' thesis (the copilot remembers you)."""
    receipts = sorted(directory.glob("receipt-*.json")) if directory.exists() else []
    courses: list[str] = []
    last_date = ""
    for fp in receipts[-5:]:
        try:
            r = json.loads(fp.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        last_date = r.get("generated_at", last_date)
        for a in r.get("assignments", []):
            course = a.get("course")
            if course and course not in courses:
                courses.append(course)
    if not courses:
        return ""
    return f"이전 계획에서 다룬 과목: {', '.join(courses[:8])} (최근 {last_date}). 연속성 고려."


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--assignments", type=Path, help="JSON list of {course,title,due}")
    p.add_argument("--ical", type=Path, help=".ics export (LMS/calendar) of deadlines")
    p.add_argument("--csv", type=Path, help="CSV with course,title,due columns")
    p.add_argument("--student", default=None, help="student id — enables per-student memory/personalization")
    p.add_argument("--today", default=None, help="YYYY-MM-DD (default: system date)")
    p.add_argument("--json", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    assignments = load_assignments(args)
    today = args.today or time.strftime("%Y-%m-%d")
    out_dir = student_dir(getattr(args, "student", None))
    prior = load_prior_context(out_dir)
    receipt = run(assignments, today, prior)

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
        cont = "yes" if receipt.get("prior_context") else "no"
        print(f"\n[date-verify: {verdict}] [genesis: {receipt['genesis_critique']['status']}] "
              f"[continuity: {cont}] [receipt: {out_dir.name}/receipt-{stamp}.json]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

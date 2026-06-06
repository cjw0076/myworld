#!/usr/bin/env python3
"""Exam Readiness Copilot — 3rd outside-value capability, built by REUSING the
factory pipeline (codex panel #2). Heavy reuse proves the factory is real:
parse_ical + extract_schedule + norm_date come straight from the deadline copilot,
the substrate router does generation, and only the exam-specific deterministic
verify is new.

  exam .ics → local LLM proposes prep/deep-work blocks → DETERMINISTIC verify
  (every prep block is before its exam, after today, and each exam has prep) →
  provenance receipt.

Schema: aios.exam_copilot.v1
Usage: python scripts/aios_exam_copilot.py --ical exams.ics [--today YYYY-MM-DD] [--json]
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import aios_capability_base as base
from aios_deadline_copilot import extract_schedule, norm_date, parse_ical

SCHEMA_VERSION = "aios.exam_copilot.v1"


def generate_prep(exams: list[dict], today: str) -> tuple[str, list[dict], str | None, list[dict]]:
    prompt = (
        f"오늘은 {today}. 다음은 한 대학생의 시험 일정(JSON, due=시험일)이다.\n"
        f"{json.dumps(exams, ensure_ascii=False)}\n\n"
        "각 시험 전에 집중 공부(deep-work) 블록을 배치하라. 먼저 기계용 스케줄을 fenced "
        '```json [{"date":"YYYY-MM-DD","course":"<입력 course 그대로>","focus":"..."}] 로 '
        "(모든 블록은 오늘 이후 ~ 해당 시험 전날 사이, course는 입력과 정확히 동일). 그 다음 "
        "사람용 한국어 공부 계획을 날짜별로 간결히."
    )
    text, served, trail = base.generate(prompt)
    return text, extract_schedule(text), served, trail


def verify_prep(prep: list[dict], exams: list[dict], today: str) -> dict:
    """DETERMINISTIC: every prep block must fall in [today, exam) for its course,
    and every exam must have prep. Pure date logic — LLM proposes, code checks."""
    today_n = norm_date(today) or today
    by_course: dict[str, list[str]] = {}
    for p in prep:
        d = norm_date(p.get("date"))
        if d:
            by_course.setdefault(str(p.get("course")), []).append(d)
    violations = []
    for e in exams:
        course = e["course"]
        exam_d = norm_date(e.get("due"))
        if not exam_d:
            violations.append({"course": course, "issue": f"invalid exam date {e.get('due')!r}"})
            continue
        dates = sorted(by_course.get(course, []))
        if not dates:
            violations.append({"course": course, "issue": "no prep scheduled"})
            continue
        if dates[-1] >= exam_d:
            violations.append({"course": course, "issue": f"prep {dates[-1]} is not before exam {exam_d}"})
        if dates[0] < today_n:
            violations.append({"course": course, "issue": f"prep {dates[0]} is before today {today_n}"})
    return {"ok": not violations, "violations": violations, "exams": len(exams)}


def run(exams: list[dict], today: str) -> dict:
    plan, prep, served, trail = generate_prep(exams, today)
    verification = verify_prep(prep, exams, today)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": today,
        "substrate": served,
        "routing_trail": trail,
        "exams": exams,
        "prep_schedule": prep,
        "verification": verification,
        "plan": plan,
        "provenance": "prep generated locally; deterministic verify vs exam dates",
    }


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--ical", type=Path, required=True, help="exam .ics (DTSTART/DUE = exam date)")
    p.add_argument("--today", default=None)
    p.add_argument("--json", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    exams = parse_ical(args.ical.read_text(encoding="utf-8"))
    today = args.today or time.strftime("%Y-%m-%d")
    receipt = run(exams, today)
    _, stamp = base.write_receipt("exam", receipt)

    v = receipt["verification"]
    if args.json:
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
    else:
        print(f"=== Exam Readiness (substrate: {receipt['substrate']}, {today}) ===\n")
        print(receipt["plan"])
        verdict = "PASS" if v["ok"] else "FLAGGED " + "; ".join(f"{x['course']}: {x['issue']}" for x in v["violations"])
        print(f"\n[prep-verify: {verdict}] [receipt: .aios/exam/receipt-{stamp}.json]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

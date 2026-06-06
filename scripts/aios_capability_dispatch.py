#!/usr/bin/env python3
"""Capability dispatcher — the operating layer OVER the copilot family.

AIOS is the operating layer above the individual capabilities: a student (or a
frontend) hands in any academic document and the dispatcher detects which value
capability applies and routes to it. One entry point for the whole family
(deadline / grade / exam / tuition).

Detection (by input shape):
  - .ics            → deadline plan  (or exam prep if kind=exam)
  - csv current,weight_completed,…  → grade recovery
  - csv …,amount,status             → tuition cashflow
  - csv course,title,due            → deadline plan

Schema: aios.capability_dispatch.v1
Usage: python scripts/aios_capability_dispatch.py --csv FILE [--ical FILE] [--kind exam] [--json]
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import aios_capability_base as base
import aios_deadline_copilot as deadline
import aios_exam_copilot as exam
import aios_grade_copilot as grade
import aios_tuition_copilot as tuition

SCHEMA_VERSION = "aios.capability_dispatch.v1"


_EXAM_SIGNALS = ("시험", "기말", "중간", "exam", "quiz", "midterm", "final", "고사")


def detect_capability(payload: dict) -> str | None:
    if payload.get("ical"):
        if payload.get("kind") == "exam":
            return "exam"
        text = str(payload["ical"]).lower()
        # auto-route an exam-looking calendar to exam prep, else a deadline plan
        return "exam" if any(kw in text for kw in _EXAM_SIGNALS) else "deadline"
    text = payload.get("csv") or ""
    header = text.splitlines()[0].lower() if text.strip() else ""
    if "weight_completed" in header or "current" in header:
        return "grade"
    if "amount" in header:
        return "tuition"
    if "due" in header:
        return "deadline"
    return None


def dispatch(payload: dict, today: str) -> tuple[str | None, dict]:
    cap = detect_capability(payload)
    if cap == "deadline":
        items = deadline.parse_ical(payload["ical"]) if payload.get("ical") else deadline.parse_csv(payload.get("csv", ""))
        student = payload.get("student")
        prior = deadline.load_prior_context(deadline.student_dir(student)) if student else ""
        return cap, deadline.run(items, today, prior)
    if cap == "exam":
        return cap, exam.run(exam.parse_ical(payload["ical"]), today)
    if cap == "grade":
        return cap, grade.run(grade.parse_grades_csv(payload.get("csv", "")), today)
    if cap == "tuition":
        return cap, tuition.run(tuition.parse_bursar_csv(payload.get("csv", "")), today)
    return None, {"error": "could not detect a capability from the input"}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--csv", type=Path)
    p.add_argument("--ical", type=Path)
    p.add_argument("--kind", choices=["exam"], help="for .ics: treat as exam prep")
    p.add_argument("--student", default=None, help="student id → per-student memory (deadline)")
    p.add_argument("--today", default=None)
    p.add_argument("--json", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload: dict = {}
    if args.ical:
        payload["ical"] = args.ical.read_text(encoding="utf-8")
    if args.csv:
        payload["csv"] = args.csv.read_text(encoding="utf-8")
    if args.kind:
        payload["kind"] = args.kind
    if args.student:
        payload["student"] = args.student
    today = args.today or time.strftime("%Y-%m-%d")

    cap, receipt = dispatch(payload, today)
    if cap is None:
        print(json.dumps(receipt, ensure_ascii=False))
        return 1
    base.write_receipt(cap, receipt)
    print(f"[dispatched → {cap}]")
    print(json.dumps(receipt, ensure_ascii=False, indent=2) if args.json else receipt.get("plan") or receipt.get("advice") or "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

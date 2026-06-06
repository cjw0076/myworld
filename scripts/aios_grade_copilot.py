#!/usr/bin/env python3
"""Grade Recovery Copilot — the SECOND outside-value capability, reusing the
Deadline Copilot pipeline (real-input → local-gen → deterministic-verify →
provenance → measure). Proves the pipeline is a reusable capability factory.

The star here is the DETERMINISTIC verify step: grades are pure arithmetic, which
LLMs get wrong and code gets exact. From a student's grade CSV we compute, per
course, the current weighted grade and exactly what they need on the remaining
work to hit their target (and whether it's even possible). The local LLM only
adds study-focus narrative for the at-risk courses — it never touches the math.

  CSV columns: course,current,weight_completed,target   (percents; weight 0-100)
    current          = your % on the graded-so-far portion
    weight_completed = % of the final grade already determined
    target           = desired final %

Schema: aios.grade_copilot.v1
Usage: python scripts/aios_grade_copilot.py --csv grades.csv [--student id] [--json]
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import time
from pathlib import Path

import aios_capability_base as base

SCHEMA_VERSION = "aios.grade_copilot.v1"


def parse_grades_csv(text: str) -> list[dict]:
    out: list[dict] = []
    for row in csv.DictReader(io.StringIO(text)):
        low = {(k or "").lower().strip(): (v or "").strip() for k, v in row.items()}
        course = low.get("course") or low.get("class")
        try:
            cur = float(low.get("current", ""))
            wc = float(low.get("weight_completed", ""))
            target = float(low.get("target", "") or 90)
        except ValueError:
            continue
        if course:
            out.append({"course": course, "current": cur, "weight_completed": wc, "target": target})
    return out


def grade_analysis(courses: list[dict]) -> list[dict]:
    """DETERMINISTIC: exact weighted-grade math (LLM-free). For each course compute
    points earned so far, the score needed on remaining work to hit target, and
    feasibility."""
    rows: list[dict] = []
    for c in courses:
        cur = float(c["current"])
        wc = max(0.0, min(100.0, float(c["weight_completed"]))) / 100.0
        target = float(c["target"])
        earned = cur * wc                       # points locked in (out of 100)
        remaining = 1.0 - wc
        if remaining <= 1e-9:
            needed = None  # course finished
            status = "final" if cur >= target else "missed"
        else:
            needed = round((target - earned) / remaining, 1)
            if needed > 100:
                status = "impossible"
            elif needed > 90:
                status = "at_risk"
            elif needed <= 0:
                status = "secured"
            else:
                status = "on_track"
        rows.append({
            "course": c["course"],
            "current": round(cur, 1),
            "target": round(target, 1),
            "needed_on_remaining": needed,
            "status": status,
        })
    return rows


def generate_advice(analysis: list[dict]) -> tuple[str, str | None, list[dict]]:
    at_risk = [r for r in analysis if r["status"] in ("at_risk", "impossible")]
    if not at_risk:
        return ("모든 과목이 목표 안정권. 현 페이스 유지.", None, [])
    prompt = (
        "다음은 한 대학생의 성적 분석(이미 정확히 계산됨)이다. 숫자를 다시 계산하지 말고, "
        "위험 과목에 대해 남은 평가에서 점수를 끌어올릴 구체적 공부 전략을 과목별 2줄로 한국어로.\n"
        f"{json.dumps(at_risk, ensure_ascii=False)}"
    )
    return base.generate(prompt)


def run(courses: list[dict], today: str) -> dict:
    analysis = grade_analysis(courses)
    advice, served, trail = generate_advice(analysis)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": today,
        "substrate": served,
        "routing_trail": trail,
        "analysis": analysis,
        "advice": advice,
        "provenance": "grades computed deterministically (LLM-free); advice generated locally for at-risk only",
    }


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--csv", type=Path, required=True, help="course,current,weight_completed,target")
    p.add_argument("--student", default=None)
    p.add_argument("--today", default=None)
    p.add_argument("--json", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    courses = parse_grades_csv(args.csv.read_text(encoding="utf-8"))
    today = args.today or time.strftime("%Y-%m-%d")
    receipt = run(courses, today)
    _, stamp = base.write_receipt("grade", receipt)

    if args.json:
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
    else:
        print(f"=== Grade Recovery (substrate: {receipt['substrate']}, {today}) ===")
        for r in receipt["analysis"]:
            need = "—" if r["needed_on_remaining"] is None else f"need {r['needed_on_remaining']}% on remaining"
            print(f"  {r['course']}: now {r['current']}% → target {r['target']}% [{r['status']}] {need}")
        print(f"\n{receipt['advice']}\n[receipt: .aios/grade/receipt-{stamp}.json]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

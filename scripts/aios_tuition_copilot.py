#!/usr/bin/env python3
"""Tuition & Aid Cashflow Copilot — 4th outside-value capability (codex panel #3),
reusing the factory pipeline. Completes the panel's three follow-ons.

  bursar/aid CSV → DETERMINISTIC cashflow analysis (overdue detection, due-date
  ordering, runway math — pure arithmetic/date logic, LLM-free) → local LLM writes
  a payment-sequencing plan for the at-risk items only → provenance receipt.

  CSV columns: item,due,amount,status   (status: due | paid)

Schema: aios.tuition_copilot.v1
Usage: python scripts/aios_tuition_copilot.py --csv bursar.csv [--today YYYY-MM-DD] [--json]
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import time
from datetime import date
from pathlib import Path

import aios_capability_base as base
from aios_deadline_copilot import norm_date

SCHEMA_VERSION = "aios.tuition_copilot.v1"


def _to_date(value) -> date | None:
    n = norm_date(value)
    if not n:
        return None
    y, m, d = n.split("-")
    return date(int(y), int(m), int(d))


def parse_bursar_csv(text: str) -> list[dict]:
    out: list[dict] = []
    for row in csv.DictReader(io.StringIO(text)):
        low = {(k or "").lower().strip(): (v or "").strip() for k, v in row.items()}
        item = low.get("item") or low.get("description")
        try:
            amount = float(low.get("amount", ""))
        except ValueError:
            continue
        if item:
            out.append({"item": item, "due": low.get("due", ""), "amount": amount,
                        "status": (low.get("status") or "due").lower()})
    return out


def cashflow_analysis(items: list[dict], today: str) -> dict:
    """DETERMINISTIC: overdue detection + due-date ordering + runway totals. The
    money/date math the LLM must never do."""
    td = _to_date(today)
    rows: list[dict] = []
    total_due = 0.0
    for it in items:
        if it.get("status") in ("paid", "완료"):
            rows.append({"item": it["item"], "amount": it["amount"], "status": "paid"})
            continue
        due = _to_date(it.get("due"))
        if due is None:
            rows.append({"item": it["item"], "amount": it["amount"], "status": "invalid_date"})
            continue
        days = (due - td).days if td else None
        total_due += float(it["amount"])
        rows.append({
            "item": it["item"], "amount": it["amount"], "due": due.isoformat(),
            "days_until": days,
            "status": "overdue" if (days is not None and days < 0) else "due",
        })
    rows.sort(key=lambda r: r.get("due") or "9999-99-99")
    return {
        "rows": rows,
        "total_due": round(total_due, 2),
        "overdue_count": sum(1 for r in rows if r.get("status") == "overdue"),
        "next_due": next((r["due"] for r in rows if r.get("status") in ("due", "overdue")), None),
    }


def generate_plan(analysis: dict) -> tuple[str, str | None, list[dict]]:
    at_risk = [r for r in analysis["rows"] if r.get("status") in ("overdue", "due")]
    if not at_risk:
        return ("미납 항목 없음. 조치 불필요.", None, [])
    prompt = (
        "다음은 한 대학생의 등록금/장학 납부 분석(이미 정확히 계산됨; 금액·마감·연체는 확정)이다. "
        "숫자를 다시 계산하지 말고, 연체/임박 항목의 납부 순서와 현실적 대응(분납·장학·상담)을 "
        "항목별 1~2줄 한국어로. 입력에 없는 항목은 언급 금지.\n"
        f"{json.dumps(at_risk, ensure_ascii=False)}"
    )
    return base.generate(prompt)


def run(items: list[dict], today: str) -> dict:
    analysis = cashflow_analysis(items, today)
    advice, served, trail = generate_plan(analysis)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": today,
        "substrate": served,
        "routing_trail": trail,
        "analysis": analysis,
        "advice": advice,
        "provenance": "amounts/dates computed deterministically (LLM-free); advice for at-risk items only",
    }


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--csv", type=Path, required=True, help="item,due,amount,status")
    p.add_argument("--today", default=None)
    p.add_argument("--json", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    items = parse_bursar_csv(args.csv.read_text(encoding="utf-8"))
    today = args.today or time.strftime("%Y-%m-%d")
    receipt = run(items, today)
    _, stamp = base.write_receipt("tuition", receipt)

    a = receipt["analysis"]
    if args.json:
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
    else:
        print(f"=== Tuition Cashflow (substrate: {receipt['substrate']}, {today}) ===")
        print(f"  total due: {a['total_due']} | overdue: {a['overdue_count']} | next due: {a['next_due']}")
        for r in a["rows"]:
            d = r.get("days_until")
            when = "paid" if r["status"] == "paid" else (f"{d}d" if d is not None else r["status"])
            print(f"  {r['item']}: {r['amount']} [{r['status']}] {when}")
        print(f"\n{receipt['advice']}\n[receipt: .aios/tuition/receipt-{stamp}.json]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

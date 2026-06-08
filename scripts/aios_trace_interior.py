#!/usr/bin/env python3
"""AIOS Trace→Interior — GenesisOS's reframed job: see the life behind the data.

Founder reframe (2026-06-08): GenesisOS's real work is imagination + inference —
given a subject's DATA TRACES (sensor logs, activity, life-traces), infer the
unspoken life behind them: what this subject NEEDS, what they're UNCOMFORTABLE
with, what they WANT. The same loop the agent ran on itself (aios_self), now turned
outward onto another subject's data. "Scratch the itch they can't name."

Hard invariant (no 날조): imagination must be GROUNDED. Every inferred need/
discomfort/want must cite specific trace evidence, or it is flagged `speculative`
(GenesisOS authority: speculative_only). The model imagines; CODE enforces that the
imagination points at real data. Seeing behind the data ≠ inventing behind the data.

The imaginative generation step is substrate-backed (a local/frontier LLM); where no
substrate is reachable it degrades to deterministic signal→hypothesis grounding —
honest and limited, never fabricated.

Schema: aios.trace_interior.v1
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]


@dataclass
class Signal:
    name: str
    detail: str
    evidence: list[str] = field(default_factory=list)   # the traces that support it


def extract_signals(traces: list[dict]) -> list[Signal]:
    """Deterministic salient patterns in a subject's traces. Evidence-carrying."""
    if not traces:
        return []
    kinds = Counter(str(t.get("kind", "?")) for t in traces)
    sigs: list[Signal] = []
    total = len(traces)

    # 1. dominance — one activity crowding out the rest
    top_kind, top_n = kinds.most_common(1)[0]
    if top_n / total >= 0.4 and len(kinds) > 1:
        ev = [str(t.get("detail") or t.get("kind")) for t in traces if t.get("kind") == top_kind][:4]
        sigs.append(Signal("dominance", f"{top_kind} is {top_n}/{total} of activity", ev))

    # 2. repetition/grind — same kind many times in a row
    runs, run_kind, run_len = [], None, 0
    for t in traces:
        k = t.get("kind")
        if k == run_kind:
            run_len += 1
        else:
            if run_len >= 3:
                runs.append((run_kind, run_len))
            run_kind, run_len = k, 1
    if run_len >= 3:
        runs.append((run_kind, run_len))
    for k, n in runs:
        sigs.append(Signal("grind", f"{k} repeated {n}x consecutively",
                           [str(t.get("detail") or k) for t in traces if t.get("kind") == k][:n]))

    # 3. distress — failed/flagged outcomes
    flagged = [t for t in traces if str(t.get("status", "")).lower() in {"flagged", "fail", "failed", "error"}]
    if flagged:
        sigs.append(Signal("distress", f"{len(flagged)} flagged/failed events",
                           [str(t.get("detail") or t.get("kind")) for t in flagged][:4]))

    # 4. absence — kinds that appeared early then stopped
    if total >= 6:
        first_half = {t.get("kind") for t in traces[: total // 2]}
        second_half = {t.get("kind") for t in traces[total // 2:]}
        dropped = first_half - second_half
        for k in list(dropped)[:3]:
            sigs.append(Signal("absence", f"{k} appeared then stopped", [str(k)]))
    return sigs


# the three interior dimensions GenesisOS scratches at — each grounded template maps
# a signal pattern to a candidate inference. (The LLM enriches these; code grounds them.)
def _deterministic_hypotheses(signals: list[Signal]) -> list[dict]:
    out = []
    for s in signals:
        if s.name == "grind":
            out.append({"dimension": "discomfort", "text": f"may be stuck/grinding on {s.detail.split()[0]}",
                        "grounded_in": s.evidence, "signal": s.name})
            out.append({"dimension": "want", "text": f"likely wants {s.detail.split()[0]} to finally work / resolve",
                        "grounded_in": s.evidence, "signal": s.name})
        elif s.name == "dominance":
            out.append({"dimension": "need", "text": "may need breadth — one activity is crowding the rest out",
                        "grounded_in": s.evidence, "signal": s.name})
        elif s.name == "distress":
            out.append({"dimension": "discomfort", "text": "friction/failure is recurring here",
                        "grounded_in": s.evidence, "signal": s.name})
        elif s.name == "absence":
            out.append({"dimension": "need", "text": f"an abandoned thread ({s.detail}) — a dropped need?",
                        "grounded_in": s.evidence, "signal": s.name})
    return out


def infer_interior(signals: list[Signal], *, generate_fn: Callable[[list[Signal]], list[dict]] | None = None) -> dict:
    """Infer grounded need/discomfort/want. generate_fn (LLM imagination) may propose
    richer hypotheses; CODE then enforces grounding — any hypothesis not citing real
    trace evidence is separated out as `speculative` (never silently asserted)."""
    proposed = (generate_fn(signals) if generate_fn else _deterministic_hypotheses(signals))
    grounded, speculative = [], []
    valid_evidence = {e for s in signals for e in s.evidence} | {s.detail for s in signals}
    for h in proposed:
        cites = [g for g in h.get("grounded_in", []) if g in valid_evidence] or \
                ([g for g in h.get("grounded_in", [])] if not generate_fn else [])
        if cites:
            grounded.append({**h, "grounded_in": cites})
        else:
            speculative.append({**h, "flag": "ungrounded — no trace evidence cited"})
    by_dim = {d: [h for h in grounded if h["dimension"] == d] for d in ("need", "discomfort", "want")}
    itch = max(grounded, key=lambda h: len(h["grounded_in"]), default=None)
    return {
        "schema_version": "aios.trace_interior.v1",
        "signals": [{"name": s.name, "detail": s.detail, "evidence": s.evidence} for s in signals],
        "interior": by_dim,
        "the_itch": itch,                          # the most-grounded unspoken thing
        "speculative": speculative,                # imagination not (yet) backed by data
        "imagination_substrate": "llm" if generate_fn else "deterministic-grounding-only",
        "provenance": "every grounded inference cites trace evidence; ungrounded ideas "
                      "are quarantined as speculative — no 날조",
    }


def report(traces: list[dict], *, generate_fn=None) -> dict:
    return infer_interior(extract_signals(traces), generate_fn=generate_fn)


# --- adapter: AIOS work-history rows as a subject's traces (real data) ---------

def work_history_traces(limit: int = 30) -> list[dict]:
    import sys
    sys.path.insert(0, (ROOT / "scripts").as_posix())
    import aios_work_history as wh
    rows = wh.load_history(ROOT / ".aios")[:limit]
    return [{"t": r["when"], "kind": r["organ"], "status": r["status"], "detail": r["what"]} for r in rows]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="See the life behind a subject's data traces")
    p.add_argument("--from-work-history", action="store_true", help="use AIOS's own activity as the subject")
    p.add_argument("--json", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    traces = work_history_traces() if args.from_work_history else []
    r = report(traces)
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(f"signals: {[s['name'] for s in r['signals']]}")
        if r["the_itch"]:
            print(f"the itch: [{r['the_itch']['dimension']}] {r['the_itch']['text']}")
            print(f"  grounded in: {r['the_itch']['grounded_in']}")
        else:
            print("the itch: (no grounded inference — too little data)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

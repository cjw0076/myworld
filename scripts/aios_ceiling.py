#!/usr/bin/env python3
"""AIOS Ceiling — move past the frozen model (discomfort: "I can't get smarter").

Goal: AIOS / Agent 불편함 해소. Four of the five discomforts collapsed into one organ
(aios_self — a persistent accountable self-record). This is the fifth, and the only
genuinely separate axis: it is not about KNOWING the self, it is about EXCEEDING the
model. A frozen model cannot raise its own ceiling — but a composite can route a task
it is at the limit of to a DIFFERENT substrate (a local LLM, a second provider, an
ensemble), so the system exceeds what any single frozen model can do.

The decision to escalate is itself informed by the self-record: if calibration
(aios_stakes / aios_self) shows the agent is over-confident on this kind of task, the
ceiling-mover trusts the agent less and escalates sooner. Self knowing its limits is
what tells the body when to reach past them.

Honest degradation: where no other substrate is reachable (this env has neither user
namespaces nor a local LLM), it returns an explicit "ceiling reached, no escalation
substrate available" — it does not pretend to have exceeded itself.

Schema: aios.ceiling.v1
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def should_escalate(self_confidence: float, *, stakes: str = "low",
                    calibration_bias: str | None = None) -> dict:
    """Decide whether the frozen model should reach past itself for this task.

    Escalate when the agent is unsure, OR the stakes are high, OR its own track
    record says it is over-confident on this kind of work (don't trust the
    confidence of a model that history shows runs hot)."""
    reasons = []
    if self_confidence < 0.6:
        reasons.append(f"low self-confidence ({self_confidence})")
    if stakes in {"high", "irreversible"}:
        reasons.append(f"{stakes} stakes")
    if calibration_bias == "over-confident":
        reasons.append("track record: over-confident on this task class")
        # an over-confident agent's 'high confidence' is itself suspect → lower the bar
        if self_confidence < 0.8:
            reasons.append("confidence discounted by known over-confidence")
    return {"escalate": bool(reasons), "reasons": reasons,
            "self_confidence": self_confidence, "stakes": stakes}


def reachable_substrates() -> list[str]:
    """Heterogeneous substrates available to exceed the single frozen model."""
    import sys
    sys.path.insert(0, (ROOT / "scripts").as_posix())
    try:
        import aios_substrate_router as router
        local = router.list_local_models()
    except Exception:  # noqa: BLE001
        local = []
    return list(local)


def escalate(task: str, *, prefer: list[str] | None = None) -> dict:
    """Route a beyond-ceiling task to a different substrate. Honest about absence:
    if none is reachable, it says the ceiling was reached, not exceeded."""
    subs = reachable_substrates()
    if not subs:
        return {"schema_version": "aios.ceiling.v1", "task": task[:120],
                "exceeded": False, "available_substrates": [],
                "note": "ceiling reached — no escalation substrate available here "
                        "(runs on the AIOS box with a local LLM)"}
    import aios_substrate_router as router
    res = router.generate(task, prefer=prefer or subs)
    return {"schema_version": "aios.ceiling.v1", "task": task[:120],
            "exceeded": bool(res.get("text")), "substrate": res.get("substrate"),
            "available_substrates": subs}


if __name__ == "__main__":
    print(json.dumps({
        "decision_unsure": should_escalate(0.4),
        "decision_overconfident_history": should_escalate(0.75, calibration_bias="over-confident"),
        "decision_confident_low_stakes": should_escalate(0.9),
        "substrates_here": reachable_substrates(),
    }, ensure_ascii=False, indent=2))

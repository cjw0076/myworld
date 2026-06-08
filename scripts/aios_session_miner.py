#!/usr/bin/env python3
"""AIOS Session Miner — reverse-engineer agent behavior from session logs.

Founder insight (2026-06-09): claude and codex both write append-only JSONL session
logs (claude: ~/.../projects/<proj>/<uuid>.jsonl; codex: ~/.codex/sessions/YYYY/MM/DD/
rollout-*.jsonl). Those logs are the GROUND TRUTH of how each agent actually behaves —
far richer and more honest than the hand-written self-observation log. Mine them and
the operator's real workflow grammar, recovery habits, parallelism, cadence, and the
per-provider behavioral fingerprint fall out — the inductive engine for ASC-0066
(substrate-equivalent adapters) and a source of systematization candidates (recurring
tool-sequences worth turning into a skill).

This is the same shape as aios_trace_interior: a log is an agent's trace data; mining
it infers behavior. And it grounds aios_self / the self-observation corpus in real
data instead of memory.

PRIVACY (DNA #7) — hard invariant: the miner reads ONLY structural/behavioral fields
(line type, tool NAME, timestamp, is_error boolean, role, mode). It NEVER reads or
emits tool arguments, message text, file contents, command bodies, or outputs. Tool
names (Bash/Edit/…) are not secrets; everything that could carry a secret is never
touched. (test_aios_session_miner injects a secret and asserts it never appears.)

Schema: aios.session_miner.v1
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

CLAUDE_PROJECTS = Path.home() / "cli-profiles" / "jaewon" / "claude" / "projects"
CODEX_SESSIONS = Path.home() / ".codex" / "sessions"


@dataclass
class Event:
    """One behavioral event — names/timing only, never content."""
    ts: str = ""
    role: str = ""              # user / assistant / tool / system
    tools: list[str] = field(default_factory=list)   # tool NAMES only
    had_error: bool = False


def parse_claude_log(path: Path) -> list[Event]:
    events: list[Event] = []
    for line in _lines(path):
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        typ = o.get("type")
        msg = o.get("message") if isinstance(o.get("message"), dict) else {}
        tools, had_error = [], False
        for c in (msg.get("content") or []) if isinstance(msg.get("content"), list) else []:
            if isinstance(c, dict):
                if c.get("type") == "tool_use":
                    tools.append(str(c.get("name", "?")))   # NAME only
                if c.get("type") == "tool_result" and c.get("is_error"):
                    had_error = True
        events.append(Event(ts=str(o.get("timestamp", "")), role=str(typ or ""),
                            tools=tools, had_error=had_error))
    return events


def parse_codex_log(path: Path) -> list[Event]:
    events: list[Event] = []
    for line in _lines(path):
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        p = o.get("payload") if isinstance(o.get("payload"), dict) else {}
        ptype = str(p.get("type", ""))
        tools, had_error, role = [], False, str(p.get("role", ""))
        if "name" in p and ptype in {"function_call", "local_shell_call", "custom_tool_call", ""}:
            tools.append(str(p.get("name", "?")))            # NAME only
        if ptype.endswith("call_output") or (isinstance(p.get("output"), dict) and p["output"].get("exit_code")):
            # an output line; treat nonzero exit as error WITHOUT reading the body
            out = p.get("output")
            if isinstance(out, dict) and out.get("exit_code") not in (0, None):
                had_error = True
        events.append(Event(ts=str(o.get("timestamp", "")), role=role or ptype,
                            tools=tools, had_error=had_error))
    return events


def _lines(path: Path):
    try:
        with path.open(encoding="utf-8", errors="ignore") as fh:
            yield from fh
    except OSError:
        return


def profile(events: list[Event]) -> dict:
    """Behavioral profile — names/counts/timing only."""
    tool_hist: Counter = Counter()
    turns_with_tools = 0
    parallel_total = 0
    errors = 0
    recoveries = 0
    seq: list[str] = []           # flattened tool sequence for n-grams
    prev_error = False
    for e in events:
        if e.tools:
            turns_with_tools += 1
            parallel_total += len(e.tools)
            for t in e.tools:
                tool_hist[t] += 1
                seq.append(t)
            if prev_error:        # a tool action right after an error = a recovery
                recoveries += 1
        if e.had_error:
            errors += 1
        prev_error = e.had_error
    bigrams = Counter(zip(seq, seq[1:]))
    trigrams = Counter(zip(seq, seq[1:], seq[2:]))
    return {
        "events": len(events),
        "tool_calls": sum(tool_hist.values()),
        "tool_histogram": dict(tool_hist.most_common(20)),
        "mean_parallelism": round(parallel_total / turns_with_tools, 2) if turns_with_tools else 0,
        "errors": errors, "recoveries": recoveries,
        "recovery_rate": round(recoveries / errors, 2) if errors else None,
        "top_sequences": [{"seq": " → ".join(g), "n": n} for g, n in trigrams.most_common(8)],
        "top_pairs": [{"seq": " → ".join(g), "n": n} for g, n in bigrams.most_common(8)],
    }


def systematization_candidates(prof: dict, *, min_count: int = 5) -> list[dict]:
    """Recurring tool-sequences frequent enough to be worth turning into a skill /
    automation — the operator's workflow grammar, surfaced inductively."""
    out = []
    for s in prof.get("top_sequences", []):
        if s["n"] >= min_count:
            out.append({"pattern": s["seq"], "occurrences": s["n"],
                        "candidate": "recurring workflow → package as a skill/automation"})
    return out


def mine_dir(kind: str, limit: int | None = None) -> dict:
    """Aggregate a behavioral fingerprint across many logs of one provider."""
    if kind == "claude":
        files = list(CLAUDE_PROJECTS.rglob("*.jsonl"))
        parse = parse_claude_log
    else:
        files = list(CODEX_SESSIONS.rglob("rollout-*.jsonl"))
        parse = parse_codex_log
    # most-recent N by mtime (UUID/name order is NOT time order — the first run's
    # claude sample was tiny because of name-sorting; the data surfaced the bug)
    files = sorted(files, key=lambda f: f.stat().st_mtime if f.exists() else 0)
    if limit:
        files = files[-limit:]
    all_events: list[Event] = []
    for f in files:
        all_events.extend(parse(f))
    prof = profile(all_events)
    return {"schema_version": "aios.session_miner.v1", "provider": kind,
            "logs": len(files), **prof,
            "systematization_candidates": systematization_candidates(prof)}


def fingerprint_diff(a: dict, b: dict) -> dict:
    """Normalized tool-distribution difference between two providers — the seed of a
    substrate-equivalent adapter (ASC-0066): how claude's behavior differs from codex's."""
    def norm(p):
        tot = p.get("tool_calls") or 1
        return {k: round(v / tot, 3) for k, v in p.get("tool_histogram", {}).items()}
    na, nb = norm(a), norm(b)
    keys = set(na) | set(nb)
    return {"provider_a": a.get("provider"), "provider_b": b.get("provider"),
            "tool_share_delta": {k: round(na.get(k, 0) - nb.get(k, 0), 3)
                                 for k in sorted(keys, key=lambda k: -abs(na.get(k, 0) - nb.get(k, 0)))[:12]}}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Reverse-engineer agent behavior from session logs")
    p.add_argument("--provider", choices=["claude", "codex", "both"], default="both")
    p.add_argument("--limit", type=int, default=40, help="most recent N logs per provider")
    p.add_argument("--json", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = {}
    if args.provider in ("claude", "both"):
        result["claude"] = mine_dir("claude", args.limit)
    if args.provider in ("codex", "both"):
        result["codex"] = mine_dir("codex", args.limit)
    if "claude" in result and "codex" in result:
        result["fingerprint_diff"] = fingerprint_diff(result["claude"], result["codex"])
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for prov in ("claude", "codex"):
            if prov in result:
                r = result[prov]
                print(f"[{prov}] {r['logs']} logs, {r['tool_calls']} tool-calls, "
                      f"parallelism {r['mean_parallelism']}, recovery {r['recovery_rate']}")
                print(f"  top tools: {list(r['tool_histogram'])[:8]}")
                for c in r["systematization_candidates"][:3]:
                    print(f"  systematize: {c['pattern']} (x{c['occurrences']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

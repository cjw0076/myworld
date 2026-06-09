#!/usr/bin/env python3
"""AIOS Packet — the inter-agent communication envelope (blueprint step 4).

Teardown §comms: codex/gemini correlate every call to its result by an explicit
`call_id` and thread lineage (`parent_call_id`/`trace_id`); sub-agents run a
`spawn → wait{status} → result` lifecycle; "done/ask/blocked/approve" are typed
control messages, not prose. AIOS's `.aios/inbox|outbox/<repo>/` bus matches by
filename/order — fragile under concurrency (we've hit ID-collision races) and a
packet that never arrives is a silent hang.

This is the envelope that fixes both, head-on:
  - `call_id` correlation (no more order/filename matching) + `parent_id`/`trace_id`
    lineage = the provenance chain (DNA invariant 5) for free.
  - typed `kind` (request | result | done | ask | blocked | approval) so a control
    message ("I'm blocked, need a decision") is structured, not text to parse.
  - a `status` lifecycle (pending → running → final | timed_out | denied) with
    `wait_status`, giving cross-OS dispatch a NAMED EXIT + liveness (DNA invariant 4)
    instead of drop-and-pray.

Privacy (DNA #7): a packet carries a `payload_ref` (a path/id), never inline content.

Schema: aios.packet.v1
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUS = ROOT / ".aios" / "bus"

KINDS = ("request", "result", "done", "ask", "blocked", "approval")
STATUSES = ("pending", "running", "final", "timed_out", "denied")


def _h(*parts) -> str:
    h = 0
    for p in parts:
        for c in str(p):
            h = (h * 131 + ord(c)) % (1 << 32)
    return f"{h:08x}"


@dataclass
class Packet:
    kind: str                 # request | result | done | ask | blocked | approval
    from_agent: str
    to_os: str
    action: str
    id: str = ""              # call_id — correlation key
    parent_id: str = ""       # the request this replies to / forked from
    trace_id: str = ""        # threads the whole conversation (lineage)
    status: str = "pending"
    payload_ref: str = ""     # path/id, NEVER inline content (DNA #7)
    ts: str = ""

    def to_dict(self) -> dict:
        return {"schema_version": "aios.packet.v1", **asdict(self)}


def new_request(from_agent: str, to_os: str, action: str, *, parent: "Packet | None" = None,
                payload_ref: str = "", seq: int = 0, ts: str = "") -> Packet:
    """A request packet with a correlation id and threaded lineage."""
    cid = "req-" + _h(from_agent, to_os, action, parent.id if parent else "", seq)
    trace = parent.trace_id if parent else ("tr-" + _h(from_agent, to_os, action, seq))
    return Packet(kind="request", from_agent=from_agent, to_os=to_os, action=action,
                  id=cid, parent_id=parent.id if parent else "", trace_id=trace,
                  status="pending", payload_ref=payload_ref, ts=ts)


def reply(request: Packet, kind: str, *, status: str = "final", from_agent: str = "",
          payload_ref: str = "", ts: str = "") -> Packet:
    """A typed reply correlated to `request` by id, inheriting its trace lineage."""
    if kind not in KINDS:
        raise ValueError(f"unknown kind: {kind}")
    return Packet(kind=kind, from_agent=from_agent or request.to_os,
                  to_os=request.from_agent.split("@")[-1] if "@" in request.from_agent else request.from_agent,
                  action=request.action, id="res-" + _h(request.id, kind),
                  parent_id=request.id, trace_id=request.trace_id,
                  status=status, payload_ref=payload_ref, ts=ts)


def correlate(requests: list[Packet], results: list[Packet]) -> list[dict]:
    """Match each request to its reply by call_id (NOT by filename/order)."""
    by_parent: dict[str, Packet] = {r.parent_id: r for r in results}
    return [{"request": req.id, "action": req.action, "to": req.to_os,
             "reply": by_parent.get(req.id).kind if req.id in by_parent else None,
             "status": by_parent[req.id].status if req.id in by_parent else "pending"}
            for req in requests]


def wait_status(call_id: str, results: list[Packet], *, deadline_passed: bool = False) -> str:
    """Liveness / named exit: the reply's status, or `timed_out` once the deadline has
    passed with no reply — a hang becomes a named outcome, never silent."""
    for r in results:
        if r.parent_id == call_id:
            return r.status
    return "timed_out" if deadline_passed else "pending"


def write_packet(p: Packet, *, bus: Path = BUS) -> Path:
    """Persist a packet to the bus, filename keyed by call_id (collision-free)."""
    d = bus / p.to_os
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{p.kind}-{p.id}.json"
    path.write_text(json.dumps(p.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def read_packets(to_os: str, *, bus: Path = BUS) -> list[Packet]:
    d = bus / to_os
    if not d.is_dir():
        return []
    out = []
    for f in sorted(d.glob("*.json")):
        try:
            o = json.loads(f.read_text(encoding="utf-8"))
            o.pop("schema_version", None)
            out.append(Packet(**{k: v for k, v in o.items() if k in Packet.__dataclass_fields__}))
        except (json.JSONDecodeError, OSError, TypeError):
            continue
    return out


if __name__ == "__main__":
    req = new_request("claude@myworld", "hivemind", "commit_to_child_repo")
    res = reply(req, "done", status="final")
    blk = reply(req, "blocked", status="pending")
    print(json.dumps({"request": req.to_dict(), "done": res.to_dict(),
                      "correlation": correlate([req], [res]),
                      "lineage_shared": req.trace_id == res.trace_id}, ensure_ascii=False, indent=2))

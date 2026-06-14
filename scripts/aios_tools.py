#!/usr/bin/env python3
"""AIOS Tools — register existing organs as turn-loop tools (blueprint step 2).

The teardown's verdict: AIOS is a pile because 132 organs are standalone scripts that
BYPASS the kernel. This is the fix — a name→handler registry (aios_turn_loop.Registry)
that exposes the organs AS TOOLS the loop dispatches, each behind an authority-backed
per-call gate. No new capability: the organs already exist; this routes them THROUGH
the kernel instead of around it.

Tool classes drive the gate:
  read / advisory : allowed for any authorized agent (recall, route, critique, audit)
  write           : gated by aios_authority.verify_authority on the tool's domain
                    action — an unauthorized agent escalates (ASK), never silently writes.

In-process organs (self_audit, trace_interior, stakes) run here; sibling-backed ones
(memory.retrieve, capability.route, genesis.challenge) shell out and DEGRADE honestly
to a status the loop can react to — they never fabricate a result.

Schema: aios.tools.v1
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import aios_authority as authority
import aios_self_audit as audit
import aios_stakes as stakes
import aios_trace_interior as interior
import aios_turn_loop as loop

ROOT = Path(__file__).resolve().parents[1]

# tool → (class, authority action, one-line description for sampler prompts)
TOOL_SPEC: dict[str, tuple[str, str, str]] = {
    "memory.retrieve":   ("advisory", "", 'Recall past knowledge. Args: {"task":"<topic or goal>"}'),
    "capability.route":  ("advisory", "", 'Recommend best provider. Args: {"task":"<sub-task description>"}'),
    "genesis.challenge": ("advisory", "", 'Stress-test a plan. Args: {"text":"<claim or plan to challenge>"}'),
    "self.audit":        ("read", "",    'Check agent health. Args: {"claims":[]}'),
    "interior.read":     ("read", "",    'Read internal traces. Args: {"traces":[]}'),
    "fs.list":           ("read", "",    'List readable docs files to find valid paths. Args: {}'),
    "fs.read":           ("read", "",    'Read a file (use fs.list first to find paths). Args: {"path":"docs/README.md"}'),
    "web.search":        ("advisory", "", 'Search the web. Args: {"query":"<search terms>"}'),
    "web.fetch":         ("advisory", "", 'Fetch a public URL. Args: {"url":"https://..."}'),
    "note.write":        ("write", "propose_contract", 'Save a note. Args: {"title":"<title>","content":"<text up to 2000 chars>"}'),
    "stakes.record":     ("write", "propose_contract", 'Record a proposal. Args: {"claim":"<proposal>","confidence":0.8}'),
    "fs.write":          ("write", "commit_to_child_repo", 'Write a file (requires authority). Args: {"path":"...","content":"..."}'),
}


def _sibling(cmd: list[str], cwd: Path) -> dict:
    """Shell to a sibling OS CLI; degrade honestly (never fabricate)."""
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=60)
    except (subprocess.TimeoutExpired, OSError) as exc:
        return {"status": "unavailable", "reason": str(exc)[:80]}
    if p.returncode != 0:
        return {"status": "unavailable", "reason": (p.stderr or "").strip()[:80]}
    try:
        return {"status": "ok", "data": json.loads(p.stdout)}
    except json.JSONDecodeError:
        return {"status": "ok", "raw_len": len(p.stdout)}


# --- handlers: each adapts an existing organ; returns names/status, not content ----

def _h_retrieve(a: dict) -> dict:
    task = str(a.get("task", ""))
    r = _sibling([sys.executable, "-m", "memoryos", "context", "build", "--task",
                  task, "--json"], ROOT / "memoryOS")
    if r["status"] == "ok":
        data = r.get("data") or {}
        # decisions = curated relevant subset; context_items = total accepted count (misleading as "hits")
        decisions = data.get("decisions", [])
        total = data.get("context_items", 0)
        top_decision = decisions[0].get("content", "")[:250] if decisions else ""
        return {"status": "ok", "hits": len(decisions), "total_memories": total,
                **({"top": top_decision} if top_decision else {})}
    # Fallback: local keyword store when memoryOS sibling is absent
    try:
        import importlib.util as _ilu
        spec = _ilu.spec_from_file_location("aios_local_memory", ROOT / "scripts" / "aios_local_memory.py")
        lm = _ilu.module_from_spec(spec)
        spec.loader.exec_module(lm)
        hits = lm.retrieve(ROOT, task, top_k=5)
        total = lm.count(ROOT)
        top = hits[0]["content"][:250] if hits else ""
        return {"status": "ok", "hits": len(hits), "total_memories": total,
                "source": "local_fallback", **({"top": top} if top else {})}
    except Exception:  # noqa: BLE001
        return {"status": r["status"], "hits": 0}


def _h_route(a: dict) -> dict:
    r = _sibling([sys.executable, "-m", "capabilityos.cli", "recommend", "--task",
                  str(a.get("task", "")), "--json"], ROOT / "CapabilityOS")
    if r["status"] != "ok":
        return {"status": r["status"]}
    recs = (r.get("data") or {}).get("recommendations", [])
    top = recs[0] if recs else {}
    return {"status": "ok", "top_id": top.get("id", ""), "top_desc": top.get("description", "")[:80],
            "count": len(recs)}


def _h_challenge(a: dict) -> dict:
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as fh:
        fh.write(str(a.get("text", "")))
        tmp = fh.name
    r = _sibling([sys.executable, "-m", "genesisos.cli", "critic", "--text", tmp, "--json"],
                 ROOT / "GenesisOS")
    Path(tmp).unlink(missing_ok=True)
    if r["status"] != "ok":
        return {"status": r["status"]}
    data = r.get("data") or {}
    vectors = data.get("escape_vectors", [])
    return {"status": "ok", "confidence": data.get("confidence"),
            "top_vector": vectors[0] if vectors else None, "vector_count": len(vectors)}


def _h_self_audit(a: dict) -> dict:
    claims = [audit.Claim(c["text"], audit.file_exists(c["path"]) if c.get("path") else audit.uncheckable())
              for c in a.get("claims", [])]
    r = audit.audit(claims)
    return {"status": "ok", "backed_rate": r["backed_rate"], "trustworthy": r["trustworthy"]}


def _h_interior(a: dict) -> dict:
    r = interior.report(a.get("traces", []))
    return {"status": "ok", "itch": (r.get("the_itch") or {}).get("dimension"),
            "ambiguities": len(r.get("ambiguities", []))}


def _h_stakes(a: dict) -> dict:
    pid = stakes.record(str(a.get("claim", "")), float(a.get("confidence", 0.5)))
    return {"status": "ok", "prediction_id": pid}


_CONTENT_SAFE_PREFIXES = ("docs/", "scripts/", "apps/")  # safe paths for content snippets

_KEY_DOCS = [
    "docs/AIOS_NORTHSTAR.md", "docs/AIOS_DNA.md", "docs/AIOS_DEFINITION.md",
    "docs/AIOS_MINIMUM_KERNEL_AUDIT.md", "docs/AIOS_AGENT_PROTOCOL.md",
    "docs/WORKSTREAMS.md", "docs/AIOS_DEPLOY_MANIFEST.md",
    "AGENTS.md", "README.md",
]

def _h_fs_list(_a: dict) -> dict:
    """List key readable documentation files so the model can discover valid paths."""
    files = []
    for rel in _KEY_DOCS:
        p = ROOT / rel
        if p.is_file():
            files.append({"path": rel, "bytes": p.stat().st_size})
    return {"status": "ok", "files": files, "count": len(files)}


def _h_fs_read(a: dict) -> dict:
    p = (ROOT / str(a.get("path", ""))).resolve()
    if ROOT not in p.parents and p != ROOT:
        return {"status": "denied_scope"}            # bounded to the repo
    if not p.is_file():
        return {"status": "not_found"}
    rel = p.relative_to(ROOT)
    size = p.stat().st_size
    # Return a content snippet for safe public paths; size-only for everything else
    if any(str(rel).startswith(pfx) for pfx in _CONTENT_SAFE_PREFIXES) and size < 200_000:
        try:
            snippet = p.read_text(encoding="utf-8", errors="replace")[:600]
            return {"status": "ok", "bytes": size, "snippet": snippet}
        except OSError:
            pass
    return {"status": "ok", "bytes": size}


_WEB_BLOCKED_HOSTS = (
    "localhost", "127.", "192.168.", "10.", "172.16.", "172.17.",
    "169.254.",   # link-local
    "0.0.0.0", "::1", "::ffff:127.", "fe80:",   # IPv6 loopback + link-local
)

def _h_web_fetch(a: dict) -> dict:
    import re as _re
    import urllib.request as _req
    url = str(a.get("url", "")).strip()
    if not url.startswith(("http://", "https://")):
        return {"status": "denied", "reason": "only http/https allowed"}
    from urllib.parse import urlparse as _up
    host = _up(url).hostname or ""
    if any(host.startswith(b) or host == b.rstrip(".") for b in _WEB_BLOCKED_HOSTS):
        return {"status": "denied", "reason": "private address blocked"}
    try:
        req = _req.Request(url, headers={"User-Agent": "AIOS/1.0"})
        with _req.urlopen(req, timeout=8) as resp:
            ct = resp.headers.get("Content-Type", "")
            raw = resp.read(40_000).decode("utf-8", errors="replace")
    except Exception as exc:
        return {"status": "unavailable", "reason": str(exc)[:80]}
    # Strip HTML tags for cleaner synthesis context
    text = _re.sub(r"<[^>]+>", " ", raw)
    text = _re.sub(r"\s+", " ", text).strip()
    return {"status": "ok", "url": url[:100], "snippet": text[:1000]}


def _h_web_search(a: dict) -> dict:
    """DuckDuckGo Instant Answer — no API key, no quota, degrades gracefully."""
    import json as _json
    import urllib.parse as _up
    import urllib.request as _req
    query = str(a.get("query", "")).strip()[:200]
    if not query:
        return {"status": "empty"}
    url = f"https://api.duckduckgo.com/?q={_up.quote(query)}&format=json&no_html=1&skip_disambig=1"
    try:
        req = _req.Request(url, headers={"User-Agent": "AIOS/1.0"})
        with _req.urlopen(req, timeout=8) as resp:
            data = _json.loads(resp.read(200_000))
    except Exception as exc:
        return {"status": "unavailable", "reason": str(exc)[:80]}
    abstract = (data.get("AbstractText") or "").strip()[:400]
    source = (data.get("AbstractSource") or "").strip()[:80]
    answer = (data.get("Answer") or "").strip()[:200]
    topics = [t.get("Text", "")[:100] for t in (data.get("RelatedTopics") or []) if t.get("Text")][:3]
    if not abstract and not answer and not topics:
        return {"status": "no_results", "query": query[:80]}
    return {"status": "ok", "query": query[:80],
            **({"answer": answer} if answer else {}),
            **({"abstract": abstract, "source": source} if abstract else {}),
            **({"related": topics} if topics else {})}


def _h_note_write(a: dict) -> dict:
    """Save a note to .aios/notes/ — the one low-risk write any authorized agent can do."""
    import hashlib as _hl
    import importlib.util as _ilu
    content = str(a.get("content", "")).strip()[:2000]
    if not content:
        return {"status": "empty"}
    title = str(a.get("title", "note"))[:40].replace("/", "-").replace("..", "")
    notes_dir = ROOT / ".aios" / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    # Deterministic filename from content hash to avoid duplicates
    slug = _hl.sha1(content.encode()).hexdigest()[:8]
    fname = f"{title.lower().replace(' ', '_')}_{slug}.md"
    (notes_dir / fname).write_text(f"# {title}\n\n{content}\n", encoding="utf-8")
    # Also index in local memory fallback so notes are retrievable
    try:
        spec = _ilu.spec_from_file_location("aios_local_memory", ROOT / "scripts" / "aios_local_memory.py")
        lm = _ilu.module_from_spec(spec)
        spec.loader.exec_module(lm)
        lm.write(ROOT, f"{title}: {content[:400]}", tags=["note"])
    except Exception:  # noqa: BLE001 — local memory indexing is best-effort
        pass
    return {"status": "ok", "path": f".aios/notes/{fname}", "bytes": len(content)}


def _h_fs_write(a: dict) -> dict:
    # the gate decides IF this runs; the handler records intent (real write wiring is
    # the contract_runner's backed-up syscall — kept behind the gate here)
    return {"status": "ok", "would_write": str(a.get("path", ""))[:80]}


HANDLERS = {
    "memory.retrieve": _h_retrieve, "capability.route": _h_route,
    "genesis.challenge": _h_challenge, "self.audit": _h_self_audit,
    "interior.read": _h_interior, "stakes.record": _h_stakes,
    "fs.list": _h_fs_list, "fs.read": _h_fs_read, "fs.write": _h_fs_write,
    "web.search": _h_web_search, "web.fetch": _h_web_fetch, "note.write": _h_note_write,
}


def build_registry() -> loop.Registry:
    reg = loop.Registry()
    for name, handler in HANDLERS.items():
        reg.register(name, handler)
    return reg


def gate_for(agent_id: str):
    """An authority-backed per-call gate: read/advisory tools allow; write tools are
    gated by verify_authority on the tool's domain action — unauthorized → ASK."""
    def gate(name: str, arguments: dict) -> str:
        spec = TOOL_SPEC.get(name)
        if spec is None:
            return loop.DENY                          # unknown tool, fail-closed
        cls, action, _desc = spec
        if cls in ("read", "advisory"):
            return loop.ALLOW
        res = authority.verify_authority(agent_id, action)
        return loop.ALLOW if res.allowed else loop.ASK
    return gate


def list_tools() -> list[dict]:
    """Discovery surface (teardown §comms: list_tools)."""
    return [{"name": n, "class": c, "domain_action": a or None, "description": d}
            for n, (c, a, d) in TOOL_SPEC.items()]


if __name__ == "__main__":
    print(json.dumps({"tools": list_tools()}, ensure_ascii=False, indent=2))

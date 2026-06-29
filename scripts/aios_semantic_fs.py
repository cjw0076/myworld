#!/usr/bin/env python3
"""aios_semantic_fs — AIOS-native semantic memory filesystem (plaintext/graph tier).

The plaintext tier of a MemOS-style memory hierarchy (grounded in LSFS "LLM Semantic File
System for AIOS", arXiv 2410.11843, and MemOS, arXiv 2505.22101). Realizes the founder's
design: a graph whose NODES ARE POINTERS TO FILES (not language models). The file content
stays on disk; a node only points + indexes it. The header (any agent) then ROUTES to
memory via semantic search instead of holding it in context — "the header need not remember
everything."

Privacy (DNA #7): the index stores a pointer + short summary + embedding, LOCAL ONLY. File
content never leaves the device. Append-only journals (DNA #3): rm = tombstone, never a
destructive rewrite.

Layout ($AIOS_FS_ROOT or ~/.aios/fs/):
  blobs/        — registered file copies (the pointed-to content)
  index.jsonl   — append-only node records {id, path, summary, tags, embedding, ts, deleted}
  edges.jsonl   — append-only graph edges {src, dst, relation, ts}
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path


def _root() -> Path:
    raw = os.environ.get("AIOS_FS_ROOT", "")
    # .resolve() so a relative AIOS_FS_ROOT yields absolute node pointers (get() must not
    # be cwd-dependent).
    return (Path(raw).expanduser() if raw else Path.home() / ".aios" / "fs").resolve()


def _paths():
    root = _root()
    return root, root / "blobs", root / "index.jsonl", root / "edges.jsonl"


def _embed(text: str) -> list[float] | None:
    """Embed via the shared AIOS helper (local nomic-embed-text). None on any failure —
    callers degrade to keyword search; never crash. Reuses aios_agent_behavior._embed_batch
    so the ollama HTTP code is not duplicated."""
    try:
        sp = str(Path(__file__).resolve().parent)
        if sp not in sys.path:
            sys.path.insert(0, sp)
        import aios_agent_behavior as AB  # noqa: PLC0415
        vecs = AB._embed_batch([text[:500]])
        return vecs[0] if vecs else None
    except Exception:  # noqa: BLE001
        return None


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return -1.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else -1.0


def _append(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except Exception:  # noqa: BLE001
                continue
    return out


def _live_nodes() -> dict[str, dict]:
    """Collapse the append-only index into the current live node set (last write wins;
    tombstoned ids dropped). Append-only on disk; this is the read-time projection."""
    _, _, index, _ = _paths()
    nodes: dict[str, dict] = {}
    for rec in _read_jsonl(index):
        nid = rec.get("id")
        if not nid:
            continue
        if rec.get("deleted"):
            nodes.pop(nid, None)
        else:
            nodes[nid] = rec
    return nodes


# ── public API ───────────────────────────────────────────────────────────────

def put(path_or_text: str, summary: str | None = None, tags: list[str] | None = None) -> dict:
    """Register a file (or a text blob) as a node pointing to it. Returns the node."""
    root, blobs, index, _ = _paths()
    blobs.mkdir(parents=True, exist_ok=True)
    # detect a real file path WITHOUT crashing on long inline text (Path.exists on a
    # multi-KB string raises OSError "File name too long").
    src = None
    if len(path_or_text) < 4096:
        try:
            cand = Path(path_or_text).expanduser()
            if cand.exists() and cand.is_file():
                src = cand
        except OSError:
            src = None
    if src is not None:
        content = src.read_text(encoding="utf-8", errors="replace")
        name = src.name
    else:                                   # treat the argument as inline text
        content = path_or_text
        name = "note.txt"
    nid = "fsn-" + hashlib.sha256(f"{name}:{content[:200]}:{time.time()}".encode()).hexdigest()[:12]
    dst = blobs / f"{nid}__{name}"
    dst.write_text(content, encoding="utf-8")     # the pointed-to copy lives on disk
    # parens matter: an explicit `summary` must win even when content is empty/whitespace.
    summ = (summary or (content.strip().splitlines()[0] if content.strip() else ""))[:200]
    node = {
        "id": nid,
        "path": dst.as_posix(),               # POINTER to the file (content stays on disk)
        "summary": summ,
        "tags": tags or [],
        "embedding": _embed(f"{summ} {' '.join(tags or [])} {content[:400]}"),
        "ts": int(time.time()),
        "deleted": False,
    }
    _append(index, node)
    return node


def get(node: dict | str) -> str:
    """Return the on-disk content the node points to (pointer integrity)."""
    nid = node if isinstance(node, str) else node.get("id")
    rec = _live_nodes().get(nid)
    if not rec:
        raise KeyError(f"no live node {nid}")
    return Path(rec["path"]).read_text(encoding="utf-8", errors="replace")


def search(query: str, k: int = 5) -> list[dict]:
    """Rank live nodes by semantic similarity to the query; fall back to keyword/substring
    match when embeddings are unavailable. Tombstoned nodes are excluded."""
    nodes = list(_live_nodes().values())
    if not nodes:
        return []
    qvec = _embed(query)
    scored: list[tuple[float, dict]] = []
    if qvec is not None and any(n.get("embedding") for n in nodes):
        for n in nodes:
            emb = n.get("embedding")
            scored.append((_cosine(qvec, emb) if emb else -1.0, n))
        method = "semantic"
    else:                                    # keyword fallback — no crash without ollama
        q = query.lower()
        terms = [t for t in q.replace(",", " ").split() if t]
        for n in nodes:
            hay = f"{n.get('summary','')} {' '.join(n.get('tags',[]))} {n.get('path','')}".lower()
            score = sum(hay.count(t) for t in terms) + (5.0 if q in hay else 0.0)
            scored.append((float(score), n))
        method = "keyword"
    scored.sort(key=lambda s: s[0], reverse=True)
    out = []
    for score, n in scored[:k]:
        if score <= 0:                       # drop no-embedding/dim-mismatch (-1.0) and
            continue                         # zero-keyword hits in BOTH modes
        out.append({**n, "_score": round(score, 4), "_method": method})
    return out


def link(a: dict | str, b: dict | str, relation: str = "related") -> dict:
    _, _, _, edges = _paths()
    edge = {"src": a if isinstance(a, str) else a["id"],
            "dst": b if isinstance(b, str) else b["id"],
            "relation": relation, "ts": int(time.time())}
    _append(edges, edge)
    return edge


def neighbors(node: dict | str, relation: str | None = None) -> list[dict]:
    nid = node if isinstance(node, str) else node["id"]
    _, _, _, edges = _paths()
    live = _live_nodes()
    out = []
    for e in _read_jsonl(edges):
        if e.get("src") == nid and (relation is None or e.get("relation") == relation):
            tgt = live.get(e.get("dst"))
            if tgt:
                out.append({**tgt, "_relation": e.get("relation")})
    return out


def rm(node: dict | str) -> None:
    """Tombstone a node (append-only — never rewrites the journal)."""
    _, _, index, _ = _paths()
    nid = node if isinstance(node, str) else node["id"]
    _append(index, {"id": nid, "deleted": True, "ts": int(time.time())})


def ls() -> list[dict]:
    return list(_live_nodes().values())


# ── CLI ──────────────────────────────────────────────────────────────────────

def _demo() -> int:
    import tempfile
    os.environ["AIOS_FS_ROOT"] = tempfile.mkdtemp(prefix="aios_fs_demo_")
    seeds = {
        "solar.txt": "Photovoltaic panels convert sunlight into electricity; perovskite tandem cells raise efficiency.",
        "lean.txt": "Lean 4 is a theorem prover; tactics like omega and simp discharge proof goals.",
        "pasta.txt": "Carbonara uses guanciale, egg yolk, pecorino; never cream in the authentic recipe.",
    }
    for name, text in seeds.items():
        put(text, summary=text, tags=[name.split(".")[0]])
    hits = search("how do we capture energy from the sun", k=1)
    print("demo query: 'how do we capture energy from the sun'")
    for h in hits:
        print(f"  top-1 [{h['_method']} score={h['_score']}]: {h['summary'][:60]}")
    return 0


def main(argv: list[str] | None = None) -> int:
    import argparse
    p = argparse.ArgumentParser(prog="aios fs", description="AIOS semantic memory filesystem (nodes point to files).")
    sub = p.add_subparsers(dest="cmd")
    sp = sub.add_parser("put"); sp.add_argument("path_or_text"); sp.add_argument("--tags", default="")
    ss = sub.add_parser("search"); ss.add_argument("query"); ss.add_argument("-k", type=int, default=5)
    sg = sub.add_parser("get"); sg.add_argument("node_id")
    sl = sub.add_parser("link"); sl.add_argument("a"); sl.add_argument("b"); sl.add_argument("--rel", default="related")
    sub.add_parser("ls")
    sub.add_parser("demo")
    args = p.parse_args(argv)

    if args.cmd == "put":
        print(json.dumps(put(args.path_or_text, tags=[t for t in args.tags.split(",") if t]), ensure_ascii=False, indent=2))
    elif args.cmd == "search":
        for h in search(args.query, args.k):
            print(f"{h['_score']:>8} [{h['_method']}] {h['id']}  {h['summary'][:70]}")
    elif args.cmd == "get":
        print(get(args.node_id))
    elif args.cmd == "link":
        print(json.dumps(link(args.a, args.b, args.rel), ensure_ascii=False))
    elif args.cmd == "ls":
        for n in ls():
            print(f"{n['id']}  emb={'Y' if n.get('embedding') else 'N'}  {n['summary'][:70]}")
    elif args.cmd == "demo":
        return _demo()
    else:
        p.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

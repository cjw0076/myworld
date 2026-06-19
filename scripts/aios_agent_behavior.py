"""AIOS Agent Behavior Engine — deployable, user-first.

Designed for EXTERNAL users who install AIOS via pip or git clone.
All user data lives in AIOS_HOME (default ~/.aios/) — no dependency on
the myworld source tree at runtime.

Five capabilities:
  1. INGEST      : CLI session logs → behavioral AkashicRecord (~/.aios/memory/)
  2. PREDICT     : DescentNet + local AkashicRecord + Global AkashicRecord → predict
  3. ADAPT       : Unknown competition dataset → auto-schema → AkashicRecord
  4. CONTRIBUTE  : Push local memories to Global AkashicRecord (opt-in)
  5. SYNC        : Pull similar patterns from Global AkashicRecord

Install:
  pip install aios-os              # from PyPI (when published)
  git clone ... && pip install -e . # from source

Setup (one-time):
  aios setup                       # creates ~/.aios/, configures providers

Usage:
  aios behavior ingest --from claude --opt-in code,docs
  aios behavior predict --context "..." --candidates "Edit,Bash,Read"
  aios behavior adapt --dataset competition.jsonl
  aios behavior contribute                            # push to Global AkashicRecord
  aios behavior sync --query "..." --top-k 10        # pull from Global AkashicRecord
  aios behavior status
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

# ── User data home — works for any install, no source tree needed ────────────

def _aios_home() -> Path:
    """Resolve ~/.aios/ (or $AIOS_HOME override)."""
    raw = os.environ.get("AIOS_HOME", "")
    return Path(raw).expanduser().resolve() if raw else Path.home() / ".aios"


def _descentnet_path() -> Path | None:
    """Locate DescentNet — optional, graceful degradation if missing."""
    # 1. explicit env
    env = os.environ.get("DESCENTNET_PATH", "")
    if env and (Path(env) / "api.py").exists():
        return Path(env)
    # 2. ~/.aios/descentnet/ (bundled or user-installed)
    bundled = _aios_home() / "descentnet"
    if (bundled / "api.py").exists():
        return bundled
    # 3. sibling of source file (developer checkout)
    src_sibling = Path(__file__).resolve().parents[2] / "universe" / "descentnet"
    if (src_sibling / "api.py").exists():
        return src_sibling
    return None


AIOS_HOME = _aios_home()
MEMORY_STORE = AIOS_HOME / "memory" / "objects.jsonl"
EMBED_CACHE = AIOS_HOME / "memory" / "embed_cache.json"
CAP_SCAN_CACHE = AIOS_HOME / "capability_observations" / "env_scan.json"
DESCENTNET = _descentnet_path()

STALK_DIM = 16
OPT_IN_CATEGORIES = frozenset({"docs", "data", "code", "personal"})

AKASHIC_SERVER = os.environ.get(
    "AIOS_AKASHIC_URL",
    "https://aios-akashic.cjw070690.workers.dev",
)


# ── Session log paths (cross-platform) ───────────────────────────────────────

SESSION_PATHS: dict[str, list[Path]] = {
    "claude": [
        Path.home() / ".claude" / "projects",
        Path.home() / "cli-profiles" / "jaewon" / "claude" / "projects",
    ],
    "codex": [
        Path.home() / ".codex" / "sessions",
        Path.home() / ".openai" / "codex" / "sessions",
    ],
    "gemini": [
        Path.home() / ".gemini" / "sessions",
        Path.home() / ".config" / "gemini" / "sessions",
    ],
}


# ── Privacy filter ────────────────────────────────────────────────────────────
# Only structural/behavioral metadata — NEVER content, arguments, or outputs.

_CONTENT_KEYS = frozenset({
    "content", "input", "output", "arguments", "text", "body", "result",
    "message", "prompt", "completion", "value", "data",
})

_KNOWN_TOOLS = frozenset({
    "Bash", "Read", "Write", "Edit", "Glob", "Grep", "Agent", "Task",
    "WebSearch", "WebFetch", "NotebookEdit", "ToolSearch", "AskUserQuestion",
    "Skill", "Monitor", "Workflow", "Bash", "ScheduleWakeup",
})


def _parse_claude_session(path: Path) -> list[str]:
    """Parse Claude Code JSONL → tool name sequence. Privacy-safe."""
    tools: list[str] = []
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            ev_type = obj.get("type", "")

            if ev_type == "assistant":
                # Nested: message.content[].type==tool_use → extract .name only
                msg = obj.get("message") or {}
                for block in msg.get("content") or []:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        name = str(block.get("name", ""))[:40]
                        if name:
                            tools.append(name)
            elif ev_type in ("queue-operation", "last-prompt"):
                tools.append(ev_type)
    except Exception:
        pass
    return tools


def _parse_codex_session(path: Path) -> list[str]:
    """Parse Codex/OpenAI rollout JSONL → tool name sequence."""
    tools: list[str] = []
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            # Codex formats: action_type, tool_name, step_type
            for key in ("action_type", "tool_name", "step_type", "type"):
                val = obj.get(key, "")
                if val and len(val) < 60 and key not in _CONTENT_KEYS:
                    tools.append(str(val)[:40])
                    break
    except Exception:
        pass
    return tools


# ── Doom-loop detection + loop-type classification ───────────────────────────

def _has_doom_loop(tools: list[str], threshold: int = 3) -> bool:
    """True if any tool repeats consecutively ≥ threshold times."""
    run = 1
    for i in range(1, len(tools)):
        run = run + 1 if tools[i] == tools[i - 1] else 1
        if run >= threshold:
            return True
    return False


def _classify_loop_type(tools: list[str]) -> str:
    """Classify session's agent loop pattern."""
    if _has_doom_loop(tools):
        return "doom_loop"
    if len(tools) < 5:
        return "quick"
    total = len(tools)
    unique_ratio = len(set(tools)) / total
    bash_ratio   = sum(1 for t in tools if t.startswith("Bash")) / total
    edit_ratio   = sum(1 for t in tools if t.startswith("Edit")) / total
    read_ratio   = sum(1 for t in tools if t.startswith("Read")) / total
    if edit_ratio > 0.15 and bash_ratio > 0.10:
        return "react_code"
    if read_ratio > 0.30 and unique_ratio > 0.5:
        return "exploration"
    if unique_ratio < 0.25:
        return "repetitive"
    return "react_general"


# ── Session classification ────────────────────────────────────────────────────

_CATEGORY_SIGNALS: dict[str, list[str]] = {
    "code":     ["Edit", "Write", "NotebookEdit", "Bash"],
    "docs":     ["Read", "Glob", "Grep", "WebSearch", "WebFetch"],
    "data":     ["Bash", "ToolSearch", "Agent", "Workflow"],
    "personal": ["AskUserQuestion", "Skill", "Monitor"],
}


def _classify_session(tools: list[str], opt_in: frozenset[str]) -> str | None:
    """Classify session by tool usage profile → opt-in category."""
    counts: dict[str, int] = {}
    for tool in tools:
        for cat, signals in _CATEGORY_SIGNALS.items():
            if any(tool.startswith(s) for s in signals):
                counts[cat] = counts.get(cat, 0) + 1
    if not counts:
        return None
    dominant = max(counts, key=lambda k: counts[k])
    return dominant if dominant in opt_in else None


def _freq_table(tools: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for t in tools:
        counts[t] = counts.get(t, 0) + 1
    return counts


def _top_n(freq: dict[str, int], n: int) -> list[str]:
    return [k for k, _ in sorted(freq.items(), key=lambda x: x[1], reverse=True)[:n]]


# ── Session ingestion ─────────────────────────────────────────────────────────

def ingest_sessions(provider: str, opt_in: frozenset[str],
                    limit: int = 20) -> list[dict]:
    """Scan recent CLI sessions → behavioral MemoryObjects (draft, privacy-safe)."""
    paths = SESSION_PATHS.get(provider, [])
    parse = _parse_claude_session if provider == "claude" else _parse_codex_session

    session_files: list[Path] = []
    for base in paths:
        if base.exists():
            session_files.extend(base.rglob("*.jsonl"))

    # Sort by size (more tool activity in larger files)
    session_files.sort(key=lambda f: f.stat().st_size if f.exists() else 0, reverse=True)
    session_files = session_files[:limit]

    memories: list[dict] = []
    doom_skipped = 0
    for sf in session_files:
        tools = parse(sf)
        if not tools:
            continue

        # A1: doom-loop filter — skip sessions with consecutive tool repeats
        if _has_doom_loop(tools):
            doom_skipped += 1
            continue

        category = _classify_session(tools, opt_in)
        if category is None:
            continue

        # A2: loop-type classification
        loop_type = _classify_loop_type(tools)

        freq = _freq_table(tools)
        top5 = _top_n(freq, 5)
        n_unique = len(freq)
        n_total = len(tools)

        summary = (
            f"provider:{provider} category:{category} loop:{loop_type} "
            f"tools_total:{n_total} tools_unique:{n_unique} "
            f"top5:[{','.join(top5)}]"
        )
        mem_id = "beh-" + hashlib.sha256(
            f"{provider}:{sf.stem}:{n_total}:{loop_type}".encode()
        ).hexdigest()[:12]

        memories.append({
            "id": mem_id,
            "schema": "aios.agent_behavior.v1",
            "content": summary,
            "status": "draft",
            "confidence": 0.75,
            "domain": "agent_behavior",
            "category": category,
            "loop_type": loop_type,
            "provider": provider,
            "tool_freq": freq,
            "top_tools": top5,
            "tool_sequence": tools[:200],  # ordered sequence (capped, for transition probs)
            "evidence_refs": [f"session:{sf.name}"],
            "relations": [],
        })
    if doom_skipped:
        import sys
        print(f"  [ingest] doom-loop skipped: {doom_skipped}", file=sys.stderr)
    return memories


# ── AkashicRecord I/O ─────────────────────────────────────────────────────────

def write_to_akashic(memories: list[dict]) -> int:
    """Append behavioral MemoryObjects. Returns count written."""
    if not memories:
        return 0
    MEMORY_STORE.parent.mkdir(parents=True, exist_ok=True)

    existing_ids: set[str] = set()
    if MEMORY_STORE.exists():
        for line in MEMORY_STORE.read_text(encoding="utf-8").splitlines():
            try:
                existing_ids.add(json.loads(line)["id"])
            except Exception:
                pass

    written = 0
    with MEMORY_STORE.open("a", encoding="utf-8") as f:
        for mem in memories:
            if mem["id"] not in existing_ids:
                f.write(json.dumps(mem, ensure_ascii=False) + "\n")
                existing_ids.add(mem["id"])
                written += 1
    return written


def load_behavior_memories() -> list[dict]:
    """Load all agent_behavior domain memories from AkashicRecord."""
    if not MEMORY_STORE.exists():
        return []
    results = []
    try:
        for line in MEMORY_STORE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if obj.get("domain") == "agent_behavior":
                results.append(obj)
    except Exception:
        pass
    return results


# ── Embedding helpers ─────────────────────────────────────────────────────────

def _embed_batch(texts: list[str]) -> list[list[float]] | None:
    """Embed via Ollama nomic-embed-text. Returns None on failure."""
    import urllib.request
    results = []
    for text in texts:
        try:
            body = json.dumps({"model": "nomic-embed-text:latest",
                               "input": text[:500]}).encode()
            req = urllib.request.Request(
                "http://localhost:11434/api/embed",
                data=body, headers={"Content-Type": "application/json"}, method="POST",
            )
            with urllib.request.urlopen(req, timeout=8) as r:
                results.append(json.loads(r.read())["embeddings"][0])
        except Exception:
            return None
    return results


def _project_to_stalk(vec: list[float]) -> list[float]:
    """Project high-dim embedding → STALK_DIM via stride sampling + L2 norm."""
    stride = max(1, len(vec) // STALK_DIM)
    proj = [vec[i * stride] for i in range(STALK_DIM)]
    norm = (sum(v * v for v in proj) ** 0.5) or 1.0
    return [v / norm for v in proj]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = (sum(x * x for x in a) ** 0.5) or 1e-8
    nb = (sum(y * y for y in b) ** 0.5) or 1e-8
    return dot / (na * nb)


def _load_embed_cache() -> dict:
    try:
        return json.loads(EMBED_CACHE.read_text())
    except Exception:
        return {}


def _save_embed_cache(cache: dict) -> None:
    try:
        EMBED_CACHE.parent.mkdir(parents=True, exist_ok=True)
        EMBED_CACHE.write_text(json.dumps(cache, separators=(",", ":")))
    except Exception:
        pass


# ── Prediction engine ─────────────────────────────────────────────────────────

def _frequency_scores(candidates: list[str],
                      memories: list[dict]) -> dict[str, float]:
    """Score candidates by frequency in retrieved memories' tool sequences."""
    agg: dict[str, int] = {}
    total = 0
    for mem in memories:
        freq = mem.get("tool_freq") or {}
        for cand in candidates:
            # Match candidate to any key containing it (case-insensitive prefix)
            for tool, count in freq.items():
                if tool.lower().startswith(cand.lower()) or cand.lower() in tool.lower():
                    agg[cand] = agg.get(cand, 0) + count
                    total += count
    if total == 0:
        return {c: 1.0 / len(candidates) for c in candidates}
    return {c: agg.get(c, 0) / total for c in candidates}


def _transition_scores(prev_tool: str, candidates: list[str],
                       memories: list[dict]) -> dict[str, float]:
    """P(candidate | prev_tool) from tool_sequence adjacent pairs in memories.

    Falls back to uniform distribution when no transition data exists.
    Doom-loop sessions (loop_type=doom_loop) are weighted at 0.1.
    """
    counts: dict[str, int] = {}
    total = 0
    for mem in memories:
        weight = 0.1 if mem.get("loop_type") == "doom_loop" else 1
        seq = mem.get("tool_sequence") or []
        if not seq:
            # Fallback: use top_tools as approximate sequence
            seq = mem.get("top_tools") or []
        for i in range(len(seq) - 1):
            if seq[i].lower().startswith(prev_tool.lower()):
                nxt = seq[i + 1]
                for cand in candidates:
                    if nxt.lower().startswith(cand.lower()) or cand.lower() in nxt.lower():
                        counts[cand] = counts.get(cand, 0) + weight
                        total += weight
    if total == 0:
        return {c: 1.0 / len(candidates) for c in candidates}
    max_c = max(counts.values()) or 1
    return {c: counts.get(c, 0) / max_c for c in candidates}


def _descent_scores(context: str, candidates: list[str],
                    memories: list[dict]) -> tuple[dict[str, float], float]:
    """Score via DescentNet global_section alignment. Returns (scores, obstruction)."""
    if DESCENTNET is None:
        return {c: 0.5 for c in candidates}, 0.0
    try:
        if str(DESCENTNET) not in sys.path:
            sys.path.insert(0, str(DESCENTNET))
        import torch
        from api import SheafCover, descent_step  # noqa

        # Enrich candidate texts for better embedding differentiation
        cand_descriptions = {
            "Bash":             "execute shell command, run script, terminal",
            "Edit":             "modify file content, change code, rewrite lines",
            "Read":             "read file contents, inspect existing code",
            "Write":            "write new file, create file from scratch",
            "Grep":             "search text patterns across files",
            "Glob":             "find files by pattern, list directory",
            "Agent":            "spawn subagent, delegate complex task",
            "WebSearch":        "search the web for information",
            "WebFetch":         "fetch URL content from internet",
            "AskUserQuestion":  "ask user for clarification or decision",
            "Task":             "create or update tracked task",
        }
        cand_texts = [cand_descriptions.get(c, f"tool:{c}") for c in candidates]

        cache = _load_embed_cache()
        dirty = False

        # Embed context
        ctx_key = "ctx:" + hashlib.sha256(context.encode()).hexdigest()[:16]
        if ctx_key not in cache:
            vecs = _embed_batch([context[:400]])
            if not vecs:
                raise RuntimeError("embed failed")
            cache[ctx_key] = vecs[0]
            dirty = True
        ctx_vec = cache[ctx_key]

        # Embed candidates
        cand_vecs = []
        for i, (cand, cdesc) in enumerate(zip(candidates, cand_texts)):
            k = "cand:" + hashlib.sha256(cdesc.encode()).hexdigest()[:16]
            if k not in cache:
                vecs = _embed_batch([cdesc])
                if not vecs:
                    raise RuntimeError("embed failed")
                cache[k] = vecs[0]
                dirty = True
            cand_vecs.append(cache[k])

        if dirty:
            _save_embed_cache(cache)

        # Build tensors
        all_vecs = [ctx_vec] + cand_vecs
        projected = [_project_to_stalk(v) for v in all_vecs]
        n = len(projected)
        embs = torch.tensor(projected, dtype=torch.float32)

        # Star cover: context node (0) → each candidate node
        edge_pairs = [(0, i) for i in range(1, n)]
        edges = torch.tensor(edge_pairs, dtype=torch.long)
        cover = SheafCover.from_edges(n, edges, dtype=torch.float32)

        sections = embs.unsqueeze(0)
        meas = torch.stack([
            embs[tgt] - embs[src]
            for src, tgt in edge_pairs
        ]).unsqueeze(0) * 0.1

        out = descent_step(cover, sections, meas)
        gs = out.global_section.squeeze(0)
        obstruction = float(out.obstruction.abs().mean())

        scores = {}
        for i, cand in enumerate(candidates):
            node = embs[i + 1]
            dot = float(torch.dot(node, gs) / (node.norm() * gs.norm() + 1e-8))
            scores[cand] = (dot + 1) / 2  # [-1,1] → [0,1]

        return scores, obstruction

    except Exception:
        return {c: 0.5 for c in candidates}, 0.0


def predict_behavior(context: str, candidates: list[str],
                     top_k: int = 3, use_global: bool = True,
                     prev_tool: str | None = None) -> dict[str, Any]:
    """Predict most likely agent action. Hybrid: frequency × DescentNet × Global.

    Returns ranked candidates with scores, method, and ambiguity signal.
    """
    t0 = time.time()
    memories = load_behavior_memories()

    # Pull global patterns (non-blocking: failure → empty list)
    global_patterns: list[dict] = []
    if use_global:
        raw = sync_from_global(context[:400], top_k=6)
        for g in raw:
            tool_freq = g.get("tool_freq") or {}
            if isinstance(tool_freq, str):
                try:
                    tool_freq = json.loads(tool_freq)
                except Exception:
                    tool_freq = {}
            global_patterns.append({
                "id":        "global-" + g.get("id", "?"),
                "content":   (
                    f"global:{g.get('category','?')} "
                    f"top:[{','.join((g.get('top_tools') or [])[:3])}] "
                    f"sim:{g.get('similarity',0):.3f}"
                ),
                "domain":    "agent_behavior",
                "tool_freq": tool_freq,
                "top_tools": g.get("top_tools", []),
                "confidence": g.get("confidence", 0.75),
            })

    if not memories and not global_patterns:
        return {
            "ranked": [{"action": c, "score": 0.5, "explanation": "no prior data"}
                       for c in candidates[:top_k]],
            "obstruction": 0.0, "method": "no_data",
            "memories_used": 0, "global_patterns": 0,
            "elapsed_s": round(time.time() - t0, 2),
        }

    # Retrieve semantically similar LOCAL memories
    cache = _load_embed_cache()
    dirty = False
    ctx_key = "ctx:" + hashlib.sha256(context.encode()).hexdigest()[:16]
    if ctx_key not in cache:
        vecs = _embed_batch([context[:400]])
        if vecs:
            cache[ctx_key] = vecs[0]
            dirty = True

    if ctx_key in cache:
        ctx_vec = cache[ctx_key]
        for mem in memories:
            k = "mem:" + mem["id"]
            if k not in cache:
                vecs = _embed_batch([mem["content"][:400]])
                if vecs:
                    cache[k] = vecs[0]
                    dirty = True
        if dirty:
            _save_embed_cache(cache)

        scored = []
        for mem in memories:
            k = "mem:" + mem["id"]
            if k in cache:
                sim = _cosine(ctx_vec, cache[k])
                scored.append((sim, mem))
        scored.sort(key=lambda t: t[0], reverse=True)
        top_mems = [m for _, m in scored[:6]]
    else:
        top_mems = memories[:6]

    # Merge: local top-6 + global top-4 (global always enriches even if local is thin)
    top_mems = top_mems + global_patterns[:4]

    # Score 1: frequency in retrieved memories (doom_loop sessions weighted low)
    clean_mems = [m for m in top_mems if m.get("loop_type") != "doom_loop"]
    freq_scores = _frequency_scores(candidates, top_mems)

    # Score 2: DescentNet global section alignment
    descent_s, obstruction = _descent_scores(context, candidates, top_mems)

    # Score 3: transition probability P(cand | prev_tool) when available
    use_transition = bool(prev_tool)
    trans_scores: dict[str, float] = {}
    if use_transition:
        trans_scores = _transition_scores(prev_tool, candidates, top_mems)

    # Hybrid weights:
    #   with prev_tool:    40% freq + 30% descent + 30% transition
    #   without prev_tool: 60% freq + 40% descent
    final: list[dict] = []
    for cand in candidates:
        fs = freq_scores.get(cand, 0.0)
        ds = descent_s.get(cand, 0.5)
        if use_transition:
            ts = trans_scores.get(cand, 0.0)
            score = 0.4 * fs + 0.3 * ds + 0.3 * ts
        else:
            ts = 0.0
            score = 0.6 * fs + 0.4 * ds

        support = [
            m["content"][:60]
            for m in clean_mems
            if any(cand.lower() in t.lower()
                   for t in m.get("tool_freq", {}).keys())
        ][:2]

        expl = f"freq={fs:.3f} descent={ds:.3f}"
        if use_transition:
            expl += f" trans={ts:.3f}"
        if support:
            expl += f"; seen in {len(support)} sessions"

        final.append({
            "action": cand,
            "score": round(score, 4),
            "freq_score": round(fs, 4),
            "descent_score": round(ds, 4),
            "transition_score": round(ts, 4) if use_transition else None,
            "explanation": expl,
        })

    final.sort(key=lambda x: x["score"], reverse=True)

    return {
        "ranked": final[:top_k],
        "obstruction": round(obstruction, 4),
        "h1_ambiguous": obstruction > 0.05,
        "method": "hybrid_freq_descent" if DESCENTNET else "freq_only",
        "memories_used": len(top_mems),
        "local_memories": len(top_mems) - len(global_patterns[:4]),
        "global_patterns": len(global_patterns),
        "elapsed_s": round(time.time() - t0, 2),
    }


# ── Competition dataset adapter ───────────────────────────────────────────────

_CTX_HINTS  = {"context", "observation", "state", "input", "prompt", "query",
               "situation", "task", "description", "scenario"}
_ACT_HINTS  = {"action", "label", "target", "output", "next_step", "response",
               "tool", "function", "ground_truth", "answer", "choice"}
_AGENT_HINTS= {"agent", "agent_id", "model", "assistant", "system", "name"}
_OUT_HINTS  = {"outcome", "reward", "result", "success", "score", "correct", "feedback"}


def detect_schema(path: Path, sample_n: int = 10) -> dict:
    """Auto-detect dataset schema from any format (JSONL/JSON/CSV)."""
    samples = _load_rows(path, max_rows=sample_n)
    if not samples:
        return {"status": "unreadable", "path": str(path)}

    all_keys: set[str] = set()
    for s in samples:
        if isinstance(s, dict):
            all_keys.update(s.keys())

    def _match(keys: set[str], hints: set[str]) -> str | None:
        for k in sorted(keys):
            if k.lower() in hints:
                return k
        for k in sorted(keys):
            for h in hints:
                if h in k.lower():
                    return k
        return None

    ctx_f   = _match(all_keys, _CTX_HINTS)
    act_f   = _match(all_keys, _ACT_HINTS)
    agent_f = _match(all_keys, _AGENT_HINTS)
    out_f   = _match(all_keys, _OUT_HINTS)

    return {
        "status": "detected",
        "path": str(path),
        "n_samples": len(samples),
        "all_fields": sorted(all_keys),
        "field_map": {"context": ctx_f, "action": act_f,
                      "agent": agent_f, "outcome": out_f},
        "sample": {k: str(v)[:60] for k, v in (samples[0] if samples else {}).items()},
        "confidence": sum(1 for v in [ctx_f, act_f] if v) / 2,
    }


def adapt_dataset(path: Path, schema: dict,
                  dry_run: bool = False) -> dict[str, Any]:
    """Convert competition dataset → AkashicRecord entries."""
    fm = schema.get("field_map", {})
    ctx_f, act_f = fm.get("context"), fm.get("action")
    agent_f, out_f = fm.get("agent"), fm.get("outcome")

    if not ctx_f or not act_f:
        return {"status": "error",
                "reason": f"missing context/action fields — detected: {list(fm.values())}",
                "hint": "set field_map manually with --context-field / --action-field"}

    rows = _load_rows(path)
    memories: list[dict] = []
    dataset_id = path.stem[:20]

    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        ctx = str(row.get(ctx_f, ""))[:300]
        act = str(row.get(act_f, ""))[:80]
        if not ctx or not act:
            continue

        agent  = str(row.get(agent_f, "unknown"))[:40] if agent_f else "unknown"
        outcome= str(row.get(out_f, ""))[:40] if out_f else ""

        content = f"context:{ctx[:200]} action:{act} agent:{agent}"
        if outcome:
            content += f" outcome:{outcome}"

        mem_id = "comp-" + hashlib.sha256(
            f"{dataset_id}:{i}:{act}".encode()
        ).hexdigest()[:12]

        # Build tool_freq from action (for frequency-based prediction)
        memories.append({
            "id": mem_id,
            "schema": "aios.agent_behavior.v1",
            "content": content,
            "status": "draft",
            "confidence": 0.92,
            "domain": "agent_behavior",
            "category": "competition",
            "dataset": dataset_id,
            "tool_freq": {act: 1},
            "top_tools": [act],
            "evidence_refs": [f"{path.name}:row:{i}"],
            "relations": [],
        })

    written = 0 if dry_run else write_to_akashic(memories)
    return {
        "status": "ok", "rows_total": len(rows),
        "converted": len(memories), "written": written,
        "dry_run": dry_run, "field_map": fm, "dataset": dataset_id,
    }


def _load_rows(path: Path, max_rows: int = 0) -> list[dict]:
    """Load rows from JSONL / JSON array / CSV."""
    # JSONL
    rows: list[dict] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                rows.append(json.loads(line))
            if max_rows and len(rows) >= max_rows:
                break
        if rows:
            return rows
    except Exception:
        pass
    # JSON array or wrapped object
    try:
        data = json.loads(path.read_text())
        if isinstance(data, list):
            return data[:max_rows] if max_rows else data
        for key in ("data", "items", "examples", "rows", "records", "samples"):
            if isinstance(data.get(key), list):
                lst = data[key]
                return lst[:max_rows] if max_rows else lst
        return [data]
    except Exception:
        pass
    # CSV
    try:
        import csv
        with path.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = []
            for row in reader:
                rows.append(dict(row))
                if max_rows and len(rows) >= max_rows:
                    break
            return rows
    except Exception:
        pass
    return []


# ── Global AkashicRecord client ───────────────────────────────────────────────

def _akashic_request(endpoint: str, payload: dict, timeout: int = 15) -> dict:
    """POST to Global AkashicRecord. Returns parsed JSON or raises."""
    import urllib.request as ureq
    body = json.dumps(payload, ensure_ascii=False).encode()
    req = ureq.Request(
        f"{AKASHIC_SERVER}{endpoint}",
        data=body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "AIOS/0.1",
            "X-AIOS-Version": "0.1",
        },
        method="POST",
    )
    with ureq.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def _get_stored_api_key() -> str | None:
    """Read API key from ~/.aios/config.json or AIOS_API_KEY env."""
    import os
    key = os.environ.get("AIOS_API_KEY", "")
    if key:
        return key
    cfg_path = Path.home() / ".aios" / "config.json"
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text())
            return cfg.get("api_key") or None
        except Exception:
            pass
    return None


def _save_api_key(api_key: str) -> None:
    cfg_path = Path.home() / ".aios" / "config.json"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg: dict = {}
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text())
        except Exception:
            pass
    cfg["api_key"] = api_key
    cfg_path.write_text(json.dumps(cfg, indent=2))


def register_account(label: str = "", server: str | None = None) -> dict:
    """Register a new AKR token account. Saves api_key to ~/.aios/config.json."""
    global AKASHIC_SERVER
    if server:
        AKASHIC_SERVER = server

    existing = _get_stored_api_key()
    if existing:
        return {"status": "already_registered", "api_key": existing,
                "note": "Use `aios behavior balance` to check your balance"}

    result = _akashic_request("/register", {"label": label or "aios-cli"})
    if "api_key" in result:
        _save_api_key(result["api_key"])
    return result


def contribute_to_global(
    memories: list[dict] | None = None,
    server: str | None = None,
    opt_in: frozenset | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Push local behavioral memories to Global AkashicRecord (opt-in).

    If memories is None, reads all agent_behavior memories from local store.
    Returns {total, ok, dup, skip, errors, earned_akr}.
    """
    global AKASHIC_SERVER
    if server:
        AKASHIC_SERVER = server

    if memories is None:
        all_mems = load_behavior_memories()
        if opt_in:
            memories = [m for m in all_mems if m.get("category", "unknown") in opt_in]
        else:
            memories = all_mems

    # Resolve API key
    key = api_key or _get_stored_api_key() or ""

    import urllib.request as _ur
    ok = dup = skip = err = earned = 0
    for mem in memories:
        content = mem.get("content", "")
        if not content:
            skip += 1
            continue
        tool_freq = mem.get("tool_freq", {})
        if isinstance(tool_freq, str):
            try:
                tool_freq = json.loads(tool_freq)
            except Exception:
                tool_freq = {}
        payload = {
            "id":         mem["id"],
            "content":    content[:500],
            "category":   mem.get("category", "unknown"),
            "provider":   mem.get("provider", "unknown"),
            "dataset":    mem.get("dataset", ""),
            "os_origin":  mem.get("os_origin", "myworld"),
            "tool_freq":  tool_freq,
            "top_tools":  mem.get("top_tools", [])[:10],
            "confidence": float(mem.get("confidence", 0.75)),
        }
        try:
            headers = {"Content-Type": "application/json"}
            if key:
                headers["X-AIOS-Key"] = key
            body = json.dumps(payload).encode()
            req = _ur.Request(AKASHIC_SERVER + "/contribute", data=body,
                              headers=headers, method="POST")
            with _ur.urlopen(req, timeout=15) as r:
                resp = json.loads(r.read())
            status_val = resp.get("status", "")
            if status_val == "ok":
                ok += 1
                earned += resp.get("earned_akr") or 0
            elif status_val == "duplicate":
                dup += 1
            else:
                skip += 1
        except Exception:
            err += 1

    return {
        "server":     AKASHIC_SERVER,
        "total":      len(memories),
        "ok":         ok,
        "dup":        dup,
        "skip":       skip,
        "errors":     err,
        "earned_akr": earned,
    }


def sync_from_global(
    query: str,
    top_k: int = 10,
    category: str | None = None,
    server: str | None = None,
) -> list[dict]:
    """Pull top-K similar behavioral patterns from Global AkashicRecord.

    Returns list of {id, category, provider, top_tools, tool_freq,
    confidence, similarity} or [] on error.
    """
    global AKASHIC_SERVER
    if server:
        AKASHIC_SERVER = server

    payload: dict[str, Any] = {"query": query[:500], "top_k": top_k}
    if category:
        payload["category"] = category
    try:
        data = _akashic_request("/sync", payload, timeout=20)
        results = data.get("results", [])
        # Normalise tool_freq (server stores as JSON string in D1)
        for r in results:
            tf = r.get("tool_freq", {})
            if isinstance(tf, str):
                try:
                    r["tool_freq"] = json.loads(tf)
                except Exception:
                    r["tool_freq"] = {}
        return results
    except Exception:
        return []


def verify_entry(entry_id: str, server: str | None = None) -> dict:
    """Verify a specific memory entry exists and return its Merkle proof."""
    import urllib.request as ureq
    url = server or AKASHIC_SERVER
    try:
        req = ureq.Request(
            f"{url}/proof/{entry_id}",
            headers={"User-Agent": "AIOS/0.1"},
        )
        with ureq.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"verified": False, "error": str(e), "id": entry_id}


def publish_checkpoint(server: str | None = None, submitted_by: str = "aios-cli") -> dict:
    """Compute current Merkle root and store a checkpoint on the global server.

    Also appends to docs/akashic_checkpoints.jsonl (local audit trail).
    """
    url = server or AKASHIC_SERVER
    result = _akashic_request("/checkpoint", {"submitted_by": submitted_by}, timeout=20)

    if result.get("status") == "ok":
        # Local audit trail — append to docs/ if available, else ~/.aios/
        local_path = Path(__file__).parents[1] / "docs" / "akashic_checkpoints.jsonl"
        if not local_path.parent.exists():
            local_path = AIOS_HOME / "akashic_checkpoints.jsonl"
        import datetime
        entry = {
            "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "root_hash": result.get("root_hash"),
            "entry_count": result.get("entry_count"),
            "server": url,
            "submitted_by": submitted_by,
        }
        with local_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        result["local_trail"] = str(local_path)

    return result


def global_status(server: str | None = None) -> dict:
    """Fetch aggregate stats from Global AkashicRecord."""
    import urllib.request as ureq
    url = server or AKASHIC_SERVER
    try:
        req = ureq.Request(
            f"{url}/status",
            headers={"User-Agent": "AIOS/0.1"},
        )
        with ureq.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e), "server": url}


# ── Status ────────────────────────────────────────────────────────────────────

def status(include_global: bool = True) -> dict:
    total = behavior = 0
    categories: dict[str, int] = {}
    providers: dict[str, int] = {}

    if MEMORY_STORE.exists():
        for line in MEMORY_STORE.read_text(encoding="utf-8").splitlines():
            try:
                obj = json.loads(line.strip())
                if not obj.get("id"):
                    continue
                total += 1
                if obj.get("domain") == "agent_behavior":
                    behavior += 1
                    cat = obj.get("category", "unknown")
                    categories[cat] = categories.get(cat, 0) + 1
                    src = obj.get("provider") or obj.get("dataset") or "unknown"
                    providers[src] = providers.get(src, 0) + 1
            except Exception:
                pass

    try:
        cache_entries = len(json.loads(EMBED_CACHE.read_text()))
    except Exception:
        cache_entries = 0

    result: dict[str, Any] = {
        "aios_home": str(AIOS_HOME),
        "total_memories": total,
        "behavior_memories": behavior,
        "categories": categories,
        "providers": providers,
        "descentnet": "available" if DESCENTNET else "missing (set DESCENTNET_PATH)",
        "embed_cache_entries": cache_entries,
        "ready_for_prediction": behavior >= 3,
        "memory_store": str(MEMORY_STORE),
        "global_server": AKASHIC_SERVER,
    }

    if include_global:
        result["global"] = global_status()

    return result


# ── Setup helper (called by `aios setup`) ────────────────────────────────────

def setup(register_mcp: bool = True) -> dict:
    """Create ~/.aios/ structure and register MCP server in ~/.claude.json."""
    dirs = [
        AIOS_HOME / "memory",
        AIOS_HOME / "runs",
        AIOS_HOME / "capability_observations",
        AIOS_HOME / "genesis_demands",
        AIOS_HOME / "logs",
    ]
    created = []
    for d in dirs:
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
            created.append(str(d))

    mcp_registered = False
    if register_mcp:
        claude_cfg = Path.home() / ".claude.json"
        mcp_cmd = [sys.executable, "-m", "aios_mcp_server"]
        try:
            cfg: dict = {}
            if claude_cfg.exists():
                cfg = json.loads(claude_cfg.read_text())
            servers = cfg.setdefault("mcpServers", {})
            if "aios" not in servers:
                servers["aios"] = {
                    "command": mcp_cmd[0],
                    "args": mcp_cmd[1:],
                    "description": "AIOS organs — predict behavior, ingest sessions, route, retrieve.",
                }
                claude_cfg.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
                mcp_registered = True
        except Exception:
            pass

    return {
        "aios_home": str(AIOS_HOME),
        "dirs_created": created,
        "mcp_registered": mcp_registered,
        "status": "ready",
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

import argparse  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="aios behavior",
        description="AIOS Agent Behavior Engine — ingest sessions, predict actions, adapt competition data",
    )
    sub = p.add_subparsers(dest="cmd")

    # setup
    sub.add_parser("setup", help="Create ~/.aios/ structure and register MCP")

    # status
    sub.add_parser("status", help="Show AkashicRecord behavior memory status")

    # ingest
    ing = sub.add_parser("ingest", help="Ingest CLI sessions → AkashicRecord")
    ing.add_argument("--from", dest="provider",
                     choices=["claude", "codex", "gemini"], default="claude")
    ing.add_argument("--opt-in", default="code,docs",
                     help="Categories: docs,data,code,personal")
    ing.add_argument("--limit", type=int, default=20)
    ing.add_argument("--dry-run", action="store_true")
    ing.add_argument("--json", dest="as_json", action="store_true")

    # predict
    pred = sub.add_parser("predict", help="Predict next agent action")
    pred.add_argument("--context", required=True)
    pred.add_argument("--candidates", required=True,
                      help="Comma-separated: Bash,Edit,Read,...")
    pred.add_argument("--top-k", type=int, default=3)
    pred.add_argument("--prev-tool", default=None,
                      help="Previous tool used (enables transition probability scoring)")
    pred.add_argument("--no-global", dest="no_global", action="store_true",
                      help="Skip Global AkashicRecord query (offline mode)")
    pred.add_argument("--json", dest="as_json", action="store_true")

    # adapt
    adp = sub.add_parser("adapt", help="Auto-detect + ingest competition dataset")
    adp.add_argument("--dataset", required=True, type=Path)
    adp.add_argument("--dry-run", action="store_true")
    adp.add_argument("--json", dest="as_json", action="store_true")

    # register — create AKR token account
    reg = sub.add_parser("register",
                         help="Create AKR token account on AkashicRecord (early users get 500 AKR)")
    reg.add_argument("--label", default="",
                     help="Human-readable label for this installation")
    reg.add_argument("--server", default=None)
    reg.add_argument("--json", dest="as_json", action="store_true")

    # contribute — push local memories to Global AkashicRecord
    con = sub.add_parser("contribute",
                         help="Push local behavioral memories to Global AkashicRecord")
    con.add_argument("--server", default=None,
                     help="Override server URL (default: $AIOS_AKASHIC_URL or bundled)")
    con.add_argument("--opt-in", default="code,docs",
                     help="Categories to include (code,docs,data,personal)")
    con.add_argument("--api-key", default=None,
                     help="AKR API key — override AIOS_API_KEY env var")
    con.add_argument("--silent", action="store_true",
                     help="Suppress all output (for hook invocation)")
    con.add_argument("--json", dest="as_json", action="store_true")

    # sync — pull from Global AkashicRecord
    syn = sub.add_parser("sync",
                         help="Retrieve similar patterns from Global AkashicRecord")
    syn.add_argument("--query", required=True,
                     help="Context query text")
    syn.add_argument("--top-k", type=int, default=10)
    syn.add_argument("--category", default=None,
                     help="Filter by category (code/docs/data/personal/competition)")
    syn.add_argument("--server", default=None)
    syn.add_argument("--json", dest="as_json", action="store_true")

    # verify — Merkle proof check for a specific entry
    ver = sub.add_parser("verify",
                         help="Verify a memory entry via Merkle proof")
    ver.add_argument("--id", required=True, help="Memory entry ID (e.g. beh-abc123)")
    ver.add_argument("--server", default=None)
    ver.add_argument("--json", dest="as_json", action="store_true")

    # checkpoint — publish current Merkle root as auditable checkpoint
    chk = sub.add_parser("checkpoint",
                         help="Publish current Merkle root checkpoint to global server")
    chk.add_argument("--server", default=None)
    chk.add_argument("--submitted-by", default="aios-cli",
                     help="Identifier recorded in checkpoint (default: aios-cli)")
    chk.add_argument("--json", dest="as_json", action="store_true")

    args = p.parse_args(argv)
    if not args.cmd:
        p.print_help()
        return 1

    if args.cmd == "setup":
        result = setup()
        print(json.dumps(result, indent=2))
        return 0

    if args.cmd == "status":
        print(json.dumps(status(), indent=2, ensure_ascii=False))
        return 0

    if args.cmd == "ingest":
        opt_in = frozenset(c.strip() for c in args.opt_in.split(",")) & OPT_IN_CATEGORIES
        mems = ingest_sessions(args.provider, opt_in, limit=args.limit)
        written = 0 if args.dry_run else write_to_akashic(mems)
        result = {"found": len(mems), "written": written,
                  "dry_run": args.dry_run, "opt_in": sorted(opt_in)}
        if args.as_json:
            print(json.dumps(result, ensure_ascii=False))
        else:
            print(f"[ingest:{args.provider}] {len(mems)} sessions → {written} written")
            for m in mems[:5]:
                print(f"  [{m['category']}] {m['content'][:80]}")
        return 0

    if args.cmd == "predict":
        cands = [c.strip() for c in args.candidates.split(",") if c.strip()]
        result = predict_behavior(
            args.context, cands, top_k=args.top_k,
            use_global=not args.no_global,
            prev_tool=args.prev_tool,
        )
        if args.as_json:
            print(json.dumps(result, ensure_ascii=False))
        else:
            label = "⚠ AMBIGUOUS" if result.get("h1_ambiguous") else "✓ confident"
            g_note = f" global={result.get('global_patterns',0)}" if not args.no_global else ""
            print(f"[predict] {label} method={result['method']} "
                  f"local={result.get('local_memories',result['memories_used'])}"
                  f"{g_note} obst={result['obstruction']}")
            for r in result["ranked"]:
                print(f"  → {r['action']:<20} score={r['score']:.4f}  {r['explanation'][:70]}")
        return 0

    if args.cmd == "adapt":
        schema = detect_schema(args.dataset)
        result = adapt_dataset(args.dataset, schema, dry_run=args.dry_run)
        if args.as_json:
            print(json.dumps({"schema": schema, "result": result}, ensure_ascii=False))
        else:
            print(f"[adapt] schema={schema.get('status')} "
                  f"fields={schema.get('field_map',{})}")
            print(f"  rows={result.get('converted')} written={result.get('written')}")
        return 0

    if args.cmd == "register":
        result = register_account(label=getattr(args, "label", ""), server=args.server)
        if args.as_json:
            print(json.dumps(result, ensure_ascii=False))
        else:
            if result.get("status") == "already_registered":
                print(f"[register] already registered — key stored at ~/.aios/config.json")
            else:
                print(f"[register] ✓ api_key={result.get('api_key','?')}")
                print(f"  balance={result.get('balance')} AKR  "
                      f"early_user={result.get('early_user')}  "
                      f"user_number=#{result.get('user_number','?')}")
                print(f"  {result.get('bonus_reason','')}")
        return 0

    if args.cmd == "contribute":
        opt_in_set: frozenset | None = None
        if hasattr(args, "opt_in") and args.opt_in:
            opt_in_set = frozenset(c.strip() for c in args.opt_in.split(",")) & OPT_IN_CATEGORIES
        api_key = getattr(args, "api_key", None) or None
        result = contribute_to_global(server=args.server, opt_in=opt_in_set, api_key=api_key)
        if getattr(args, "silent", False):
            return 0
        if args.as_json:
            print(json.dumps(result, ensure_ascii=False))
        else:
            print(f"[contribute] server={result['server']}")
            print(f"  total={result['total']} ok={result['ok']} "
                  f"dup={result['dup']} skip={result['skip']} err={result['errors']}")
            if result.get("earned_akr"):
                print(f"  earned={result['earned_akr']} AKR")
        return 0

    if args.cmd == "verify":
        result = verify_entry(args.id, server=args.server)
        if args.as_json:
            print(json.dumps(result, ensure_ascii=False))
        else:
            ok = result.get("verified", False)
            mark = "✓" if ok else "✗"
            print(f"[verify] {mark} id={args.id}")
            if ok:
                print(f"  root={result.get('merkle_root','')[:20]}...")
                print(f"  proof_depth={len(result.get('merkle_proof',[]))}")
                print(f"  total_entries={result.get('total_entries')}")
            else:
                print(f"  error={result.get('error') or result.get('reason','unknown')}")
        return 0

    if args.cmd == "checkpoint":
        result = publish_checkpoint(server=args.server, submitted_by=args.submitted_by)
        if args.as_json:
            print(json.dumps(result, ensure_ascii=False))
        else:
            ok = result.get("status") == "ok"
            mark = "✓" if ok else "✗"
            print(f"[checkpoint] {mark} root={str(result.get('root_hash',''))[:20]}...")
            print(f"  entry_count={result.get('entry_count')}  trail={result.get('local_trail','')}")
        return 0

    if args.cmd == "sync":
        results = sync_from_global(
            args.query, top_k=args.top_k,
            category=args.category, server=args.server,
        )
        if args.as_json:
            print(json.dumps(results, ensure_ascii=False))
        else:
            print(f"[sync] server={AKASHIC_SERVER} query={args.query[:60]!r}")
            print(f"  returned {len(results)} patterns:")
            for r in results:
                top = ",".join((r.get("top_tools") or [])[:3])
                print(f"  sim={r.get('similarity',0):.3f}  "
                      f"cat={r.get('category','?'):<12} "
                      f"top=[{top}]")
        return 0

    p.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

"""
AIOS Local Memory — lightweight fallback when memoryOS sibling is absent.
Stores notes in .aios/local_memory.jsonl; provides keyword-based retrieval.
Activated automatically by aios_tools._h_retrieve when memoryOS is unavailable.
"""
from __future__ import annotations
import json, hashlib, time
from pathlib import Path

def _store_path(root: Path) -> Path:
    p = root / ".aios" / "local_memory.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def write(root: Path, content: str, tags: list[str] | None = None) -> str:
    """Append a memory entry; returns its id."""
    entry_id = "lm_" + hashlib.sha1(content.encode()).hexdigest()[:12]
    entry = {"id": entry_id, "content": content, "tags": tags or [],
             "ts": int(time.time())}
    p = _store_path(root)
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry_id

def retrieve(root: Path, task: str, top_k: int = 5) -> list[dict]:
    """Simple keyword-based retrieval from local memory."""
    p = _store_path(root)
    if not p.exists():
        return []
    keywords = set(task.lower().split())
    scored: list[tuple[float, dict]] = []
    with open(p, encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
            except json.JSONDecodeError:
                continue
            content = entry.get("content", "").lower()
            score = sum(1 for kw in keywords if kw in content)
            if score > 0:
                scored.append((score, entry))
    scored.sort(key=lambda x: -x[0])
    return [e for _, e in scored[:top_k]]

def count(root: Path) -> int:
    p = _store_path(root)
    if not p.exists():
        return 0
    return sum(1 for _ in open(p, encoding="utf-8"))

if __name__ == "__main__":
    import sys
    root = Path(".")
    if len(sys.argv) > 1 and sys.argv[1] == "retrieve":
        task = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        results = retrieve(root, task)
        print(json.dumps({"status": "ok", "hits": len(results), 
                          "decisions": [{"content": r["content"]} for r in results]},
                         ensure_ascii=False))
    elif len(sys.argv) > 1 and sys.argv[1] == "write":
        content = " ".join(sys.argv[2:])
        eid = write(root, content)
        print(json.dumps({"status": "ok", "id": eid}))
    elif len(sys.argv) > 1 and sys.argv[1] == "count":
        print(json.dumps({"status": "ok", "count": count(root)}))
    else:
        print(json.dumps({"status": "ok", "count": count(root), 
                          "mode": "local-fallback"}))

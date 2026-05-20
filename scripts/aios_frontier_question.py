#!/usr/bin/env python3
"""ASC-0211 L3 routine #3 — Frontier-question generator.

Looks at:
1. Peer state files (project_user_agent_*, project_claude_agent_*) in the
   AIOS memory store.
2. Reference memos that *have not been cited* by any recent contract.

Generates 1-3 questions the peers are *not* asking but probably should
— either because a reference memo's topic hasn't been wired into action,
or because one peer's named blindspot intersects another peer's known
knowledge (asymmetric ignorance).

Output: aios.memory_draft_review_request.v1 packets, status=draft,
auto_accept=False. Same draft-first invariant as discomfort_inject.

Cite: this routine is part of [[project_aios_peer_agent_frame]]'s L3
Transcendence Engine. founder's "숨길 자유" principle preserved — we
only read public memo content; no inference about hidden state.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MEMORY_DIR = Path(
    "/home/user/.claude/projects/-home-user-workspaces-jaewon-myworld/memory"
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _memo_name(path: Path) -> str:
    """Slug used in [[link]]s — strip .md, replace _ with -, leading directory."""
    return path.stem.replace("_", "-")


def list_reference_memos(memory_dir: Path) -> list[Path]:
    return sorted(memory_dir.glob("reference_*.md"))


def list_peer_state(memory_dir: Path) -> list[Path]:
    return sorted(memory_dir.glob("project_user_agent*.md")) + \
           sorted(memory_dir.glob("project_claude_agent*.md"))


def contract_text_corpus(contracts_dir: Path) -> str:
    """Concatenate all contract text (lowercased) — used for naive citation check."""
    out: list[str] = []
    for p in contracts_dir.glob("ASC-*.md"):
        try:
            out.append(p.read_text(encoding="utf-8", errors="replace").lower())
        except Exception:
            continue
    return "\n".join(out)


def uncited_reference_memos(memory_dir: Path, contracts_corpus: str) -> list[Path]:
    """Reference memos whose slug never appears in any contract."""
    uncited = []
    for memo in list_reference_memos(memory_dir):
        slug = _memo_name(memo).lower()
        slug_alt = memo.stem.lower()  # also check underscore form
        if slug not in contracts_corpus and slug_alt not in contracts_corpus:
            uncited.append(memo)
    return uncited


def extract_topic_summary(memo: Path) -> str:
    """Best-effort one-line topic of a memo — frontmatter `description` if present."""
    try:
        text = memo.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return memo.stem
    m = re.search(r"^description:\s*(.+)$", text, re.M)
    if m:
        desc = m.group(1).strip()
        if desc:
            return desc[:160]
    # fallback: first non-frontmatter line
    body = text.split("---", 2)[-1] if text.startswith("---") else text
    for line in body.splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            return s[:160]
    return memo.stem


def build_questions_for_uncited(
    memos: list[Path],
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Generate questions for reference memos with no contract citation."""
    out: list[dict[str, Any]] = []
    for memo in memos[:limit]:
        topic = extract_topic_summary(memo)
        question = (
            f"We studied {memo.stem} ({topic[:120]}). "
            f"No contract cites it yet. What concrete decision or change "
            f"would this knowledge force *if we let it*?"
        )
        out.append({
            "type": "uncited_reference",
            "memo": memo.name,
            "memo_slug": _memo_name(memo),
            "question": question,
        })
    return out


def build_questions_for_peer_blindspots(memory_dir: Path) -> list[dict[str, Any]]:
    """Generic asymmetry questions from peer state files."""
    out: list[dict[str, Any]] = []
    for peer_file in list_peer_state(memory_dir):
        try:
            text = peer_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        # Find named blindspots section heuristically — H2/H3 mentioning blindspot or limit
        if re.search(r"(?im)^##+\s*.*(blindspot|named limit|못 보는|frontier)", text):
            peer_id = peer_file.stem.replace("project_", "").replace("_agent_", "@")
            out.append({
                "type": "peer_blindspot",
                "memo": peer_file.name,
                "peer": peer_id,
                "question": (
                    f"{peer_id} has named blindspots in {peer_file.name}. "
                    f"What is the *smallest* concrete experiment in the next 7 days "
                    f"that would actually narrow one of them? — and which peer can run it?"
                ),
            })
    return out


def build_draft_packet(q: dict[str, Any]) -> dict[str, Any]:
    req_id = "frontier-" + uuid.uuid4().hex[:12]
    return {
        "schema_version": "aios.memory_draft_review_request.v1",
        "request_id": req_id,
        "dispatch_id": req_id,
        "contract_id": "ASC-0211",
        "contract_path": "docs/contracts/ASC-0211-aios-cognitive-prosthesis-layer.md",
        "target_repo": "memoryOS",
        "agent": "aios_frontier_question@ASC-0211",
        "goal": f"Frontier question — {q['type']} on {q.get('memo','peer')}",
        "source_artifact": "scripts/aios_frontier_question.py",
        "draft_id": f"frontier:{q['type']}:{uuid.uuid4().hex[:6]}",
        "return_to": f".aios/outbox/memoryOS/{req_id}.memoryOS.result.json",
        "review_policy": {"auto_accept": False, "draft_first": True},
        "draft": {
            "type": "question",
            "origin": "aios_frontier_question",
            "status": "draft",
            "confidence": 0.4,
            "content": q["question"],
            "raw_refs": [
                "scripts/aios_frontier_question.py",
                f"memory://{q.get('memo','peer-state')}",
            ],
            "provenance": {
                "source": "aios_frontier_question",
                "kind": q["type"],
                "memo": q.get("memo"),
                "peer": q.get("peer"),
                "memo_slug": q.get("memo_slug"),
                "generated_at": _now_iso(),
            },
            "project": "AIOS",
        },
        "scope": {"allowed_files": [], "forbidden_files": [".env"]},
        "created_at": _now_iso(),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="ASC-0211 L3 routine #3 — frontier-question generator")
    p.add_argument("--memory-dir", type=Path, default=DEFAULT_MEMORY_DIR)
    p.add_argument("--contracts-dir", type=Path, default=REPO_ROOT / "docs" / "contracts")
    p.add_argument("--out-dir", type=Path,
                   default=REPO_ROOT / ".aios" / "inbox" / "memoryOS")
    p.add_argument("--limit-uncited", type=int, default=3,
                   help="max questions from uncited reference memos")
    p.add_argument("--include-peer-blindspots", action="store_true",
                   help="also generate generic peer blindspot questions")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    corpus = contract_text_corpus(args.contracts_dir)
    uncited = uncited_reference_memos(args.memory_dir, corpus)
    qs: list[dict[str, Any]] = []
    qs.extend(build_questions_for_uncited(uncited, args.limit_uncited))
    if args.include_peer_blindspots:
        qs.extend(build_questions_for_peer_blindspots(args.memory_dir))

    drafts = [build_draft_packet(q) for q in qs]

    written: list[str] = []
    if not args.dry_run:
        args.out_dir.mkdir(parents=True, exist_ok=True)
        for d in drafts:
            p2 = args.out_dir / f"{d['request_id']}.memoryOS.json"
            p2.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
            written.append(p2.as_posix())

    out = {
        "schema_version": "aios.frontier_question.v1",
        "uncited_count": len(uncited),
        "uncited_memos": [m.name for m in uncited],
        "generated": len(drafts),
        "written": written,
        "dry_run": args.dry_run,
        "drafts": drafts if args.dry_run else None,
    }
    if args.json:
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        print(f"uncited reference memos: {len(uncited)}")
        for m in uncited:
            print(f"  - {m.name}")
        print(f"questions generated: {len(qs)}")
        for d in drafts:
            print(f"  [{d['draft']['provenance']['kind']}] {d['draft']['content']}")
        if args.dry_run:
            print("(dry-run: no files written)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

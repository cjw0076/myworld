#!/usr/bin/env python3
"""Star Radar — AIOS absorbs good ideas from the GitHub ecosystem.

Founder directive: track trending projects (star-history-style momentum) and
absorb the good ideas into AIOS. This is the absorption thesis as an organ:

  GitHub high-momentum repos (recent + fast-growing) → LOCAL LLM distills each
  project's reusable IDEA + how AIOS could absorb it → absorption-candidate
  records for operator review → MemoryOS reference memory / CapabilityOS candidate.

Draft-first: it EMITS candidates; it never auto-accepts into MemoryOS/CapabilityOS.

Schema: aios.star_radar.v1
Usage: python scripts/aios_star_radar.py [--since 2026-03-01] [--min-stars 2000]
       [--query "agent OR llm"] [--limit 8] [--json]
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

import aios_capability_base as base

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "aios.star_radar.v1"
GH_SEARCH = "https://api.github.com/search/repositories"


def build_query(since: str, min_stars: int, extra: str | None) -> str:
    q = f"created:>{since} stars:>{min_stars}"
    if extra:
        q += f" {extra}"
    return q


def parse_repos(payload: dict) -> list[dict]:
    out: list[dict] = []
    for r in payload.get("items", []) or []:
        out.append({
            "full_name": r.get("full_name"),
            "stars": r.get("stargazers_count", 0),
            "created_at": (r.get("created_at") or "")[:10],
            "description": (r.get("description") or "").strip(),
            "topics": r.get("topics") or [],
            "url": r.get("html_url"),
        })
    return out


def fetch_trending(since: str, min_stars: int, extra: str | None, limit: int) -> list[dict]:
    q = build_query(since, min_stars, extra)
    url = f"{GH_SEARCH}?{urllib.parse.urlencode({'q': q, 'sort': 'stars', 'order': 'desc', 'per_page': limit})}"
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "aios-star-radar"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return parse_repos(json.loads(resp.read()))


def distill_prompt(repo: dict) -> str:
    return (
        "당신은 personal AI operating system(AIOS: 메모리/능력라우팅/발산비평/실행 + 컨트롤플레인)의 "
        "흡수 엔진이다. 다음 GitHub 트렌딩 프로젝트에서 (1) 재사용 가능한 핵심 아이디어 1줄, "
        "(2) AIOS가 이를 어떻게 흡수/차용할 수 있는지(어느 OS/조직에, 무엇으로) 1줄. 과장 없이, 없으면 'low fit'.\n"
        f"repo: {repo['full_name']} (★{repo['stars']}, {repo['created_at']})\n"
        f"desc: {repo['description']}\n"
        f"topics: {', '.join(repo['topics'][:8])}"
    )


def distill(repo: dict) -> dict:
    text, served, _ = base.generate(distill_prompt(repo))
    return {**repo, "absorption": text.strip(), "distilled_by": served}


def load_seen(radar_dir: Path) -> set[str]:
    """Repos already distilled in prior radar receipts — so periodic tracking
    only spends the LLM on genuinely NEW projects."""
    seen: set[str] = set()
    if not radar_dir.exists():
        return seen
    for fp in radar_dir.glob("receipt-*.json"):
        try:
            r = json.loads(fp.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        for c in r.get("candidates", []):
            if c.get("full_name"):
                seen.add(c["full_name"])
    return seen


def run(since: str, min_stars: int, extra: str | None, limit: int, skip_seen: bool = True) -> dict:
    repos = fetch_trending(since, min_stars, extra, limit)
    seen = load_seen(ROOT / ".aios" / "star_radar") if skip_seen else set()
    fresh = [r for r in repos if r["full_name"] not in seen]
    candidates = [distill(r) for r in fresh]
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": time.strftime("%Y-%m-%d"),
        "query": build_query(since, min_stars, extra),
        "candidates": candidates,
        "skipped_seen": sorted(r["full_name"] for r in repos if r["full_name"] in seen),
        "note": "draft-first — operator reviews before any MemoryOS/CapabilityOS promotion",
    }


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--since", default="2026-03-01", help="created-after date (momentum proxy)")
    p.add_argument("--min-stars", type=int, default=2000)
    p.add_argument("--query", default=None, help="extra GitHub query terms (e.g. 'agent OR llm')")
    p.add_argument("--limit", type=int, default=8)
    p.add_argument("--no-skip-seen", action="store_true", help="re-distill repos seen in prior runs")
    p.add_argument("--json", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    receipt = run(args.since, args.min_stars, args.query, args.limit, skip_seen=not args.no_skip_seen)
    base.write_receipt("star_radar", receipt)
    if args.json:
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
    else:
        print(f"=== Star Radar ({receipt['query']}) — {len(receipt['candidates'])} new, "
              f"{len(receipt['skipped_seen'])} already seen ===")
        for c in receipt["candidates"]:
            print(f"\n★{c['stars']} {c['full_name']} — {c['description'][:70]}")
            print(f"  {c['absorption']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Skill Catalog — a unified CapabilityOS index of every skill in the AIOS workspace.

Absorbed from a strong 2026-06-07 ecosystem signal (mattpocock/skills ~119k,
garrytan/gstack ~107k, antigravity-awesome-skills ~39k): a curated .claude/skills
directory is a high-value shareable/installable product. AIOS already has skills
spread across repos (myworld operator harness, uri, hivemind); this indexes them
all into one catalog so they're discoverable and routable across agent CLIs —
the foundation of a shareable AIOS skill library + CapabilityOS routing.

Scans every SKILL.md under the workspace (node_modules excluded) and parses its
frontmatter (name, description).

Schema: aios.skill_catalog.v1
Usage: python scripts/aios_skill_catalog.py [--root .] [--json]
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "aios.skill_catalog.v1"
_FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---", re.S)


def parse_skill(text: str) -> dict | None:
    m = _FRONTMATTER.match(text)
    if not m:
        return None
    fm = m.group(1)
    name = re.search(r"^name:\s*(.+?)\s*$", fm, re.M)
    if not name:
        return None
    desc = ""
    dm = re.search(r"^description:\s*(.*)$", fm, re.M)
    if dm:
        inline = dm.group(1).strip().lstrip(">|-").strip()
        if inline:
            desc = inline
        else:  # folded scalar: collect following indented lines
            lines = fm[dm.end():].splitlines()
            folded = []
            for ln in lines[1:] if not inline else lines:
                if ln.strip() and (ln.startswith(" ") or ln.startswith("\t")):
                    folded.append(ln.strip())
                elif ln.strip() == "":
                    continue
                else:
                    break
            desc = " ".join(folded)
    return {"name": name.group(1).strip(), "description": desc[:300]}


def scan_skills(root: Path) -> list[dict]:
    out: list[dict] = []
    for fp in sorted(root.rglob("SKILL.md")):
        if "node_modules" in fp.parts:
            continue
        try:
            parsed = parse_skill(fp.read_text(encoding="utf-8"))
        except OSError:
            continue
        if not parsed:
            continue
        rel = fp.relative_to(root)
        repo = rel.parts[0] if rel.parts[0] in {"uri", "hivemind", "memoryOS", "CapabilityOS", "GenesisOS"} else "myworld"
        out.append({**parsed, "repo": repo, "path": rel.as_posix()})
    return out


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument("--json", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    skills = scan_skills(args.root.resolve())
    catalog = {"schema_version": SCHEMA_VERSION, "count": len(skills), "skills": skills}
    if args.json:
        print(json.dumps(catalog, ensure_ascii=False, indent=2))
    else:
        print(f"=== AIOS Skill Catalog — {len(skills)} skills ===")
        for repo in sorted({s["repo"] for s in skills}):
            print(f"\n[{repo}]")
            for s in [x for x in skills if x["repo"] == repo]:
                print(f"  /{s['name']} — {s['description'][:90]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

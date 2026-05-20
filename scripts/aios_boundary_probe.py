#!/usr/bin/env python3
"""ASC-0211 L3 routine #4 — Boundary probe via GenesisOS.

Takes a piece of current work (a contract path or arbitrary text), feeds
it to GenesisOS's critic CLI, and translates the resulting
`prison_signatures` + `escape_vectors` into memoryOS draft packets so a
peer can review whether AIOS is locked into a single frame.

Also produces cross-domain transfer candidates — short suggestions for
*which other field's solved-shape* could apply to the current work.
This is the boundary-probe arm of [[project_aios_peer_agent_frame]]'s
L3 engine and the closest enactment of [[project_genesisos_true_role]]
("cross-domain knowledge transfer engine").

Output: aios.memory_draft_review_request.v1 packets, draft-first,
auto_accept=False.

Usage:
    python scripts/aios_boundary_probe.py --target docs/contracts/ASC-0211-*.md --json
    python scripts/aios_boundary_probe.py --text-file /tmp/decision.txt --dry-run
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
GENESIS_ROOT = REPO_ROOT / "GenesisOS"


CROSS_DOMAIN_FRAMES = [
    {
        "domain": "biology",
        "shape": "homeostasis — self-correcting feedback loops, no central commander",
        "transfer_hint": "Does this decision rely on a *commander* loop (founder/operator) where a *feedback* loop would scale better?",
    },
    {
        "domain": "civil engineering",
        "shape": "bridge load-testing — capacity verified by traffic, not inspection",
        "transfer_hint": "Are we verifying via documentation (inspection) when we should verify via real load (a second consumer)?",
    },
    {
        "domain": "neuroscience",
        "shape": "complementary learning systems — fast hippocampus + slow cortex consolidation",
        "transfer_hint": "Is there a fast/slow split being collapsed? (e.g., dream cycle vs in-session memory)",
    },
    {
        "domain": "economics",
        "shape": "principal-agent problem — incentive misalignment between owner and operator",
        "transfer_hint": "Whose incentives are we modeling implicitly here? Does the peer agent we're 'serving' actually want what we're optimizing for?",
    },
    {
        "domain": "ecology",
        "shape": "successional stages — pioneer species enable later climax community",
        "transfer_hint": "Are we trying to install the climax community directly, skipping the pioneer (rough/dirty/temporary) stage that builds substrate?",
    },
    {
        "domain": "linguistics",
        "shape": "pidgin → creole — restricted contact language stabilizes into full grammar",
        "transfer_hint": "Is our current contract/protocol a pidgin between two systems that needs to creolize into a proper grammar before scaling?",
    },
    {
        "domain": "control theory",
        "shape": "observer/controller separation — distinct module estimates state vs decides action",
        "transfer_hint": "Are observer and controller responsibilities collapsed into one peer in this design?",
    },
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def run_genesis_critic(text: str) -> dict[str, Any]:
    """Call GenesisOS critic CLI; returns parsed JSON or error envelope."""
    if not (GENESIS_ROOT / "genesisos").exists():
        return {"ok": False, "error": "GenesisOS not installed (genesisos/ missing)"}
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write(text)
        tmp = f.name
    try:
        r = subprocess.run(
            [sys.executable, "-m", "genesisos.cli", "critic",
             "--text", tmp, "--json"],
            cwd=str(GENESIS_ROOT),
            capture_output=True, text=True, check=False,
        )
        if r.returncode != 0:
            return {"ok": False, "returncode": r.returncode,
                    "stderr": r.stderr.strip()[:500]}
        try:
            return {"ok": True, "result": json.loads(r.stdout)}
        except json.JSONDecodeError:
            return {"ok": True, "raw": r.stdout.strip()[:1000]}
    finally:
        Path(tmp).unlink(missing_ok=True)


def signature_to_draft(target_id: str, sig: dict[str, Any]) -> dict[str, Any]:
    """Translate a single GenesisOS prison_signature to a draft packet."""
    sig_name = sig.get("signature", "unknown")
    description = sig.get("description") or sig.get("rationale") or ""
    content = (
        f"Prison signature against {target_id}: {sig_name}. "
        f"{description.strip()[:200]} "
        f"Negation: try the opposite frame for the next decision in this thread."
    )
    return _build_packet("prison_signature", content, target_id, {"signature": sig_name})


def cross_domain_drafts(target_id: str, n: int = 2, seed: int | None = None) -> list[dict[str, Any]]:
    """Pick N cross-domain frames and turn each into a probe draft."""
    import random
    rng = random.Random(seed if seed is not None else 0xA105)
    frames = rng.sample(CROSS_DOMAIN_FRAMES, min(n, len(CROSS_DOMAIN_FRAMES)))
    out = []
    for frame in frames:
        content = (
            f"Cross-domain probe against {target_id} via {frame['domain']}: "
            f"{frame['shape']}. {frame['transfer_hint']}"
        )
        out.append(_build_packet("cross_domain_probe", content, target_id, {
            "domain": frame["domain"],
            "shape": frame["shape"],
        }))
    return out


def _build_packet(kind: str, content: str, target_id: str,
                  extra_provenance: dict[str, Any]) -> dict[str, Any]:
    req_id = "probe-" + uuid.uuid4().hex[:12]
    return {
        "schema_version": "aios.memory_draft_review_request.v1",
        "request_id": req_id,
        "dispatch_id": req_id,
        "contract_id": "ASC-0211",
        "contract_path": "docs/contracts/ASC-0211-aios-cognitive-prosthesis-layer.md",
        "target_repo": "memoryOS",
        "agent": "aios_boundary_probe@ASC-0211",
        "goal": f"Boundary probe ({kind}) against {target_id}",
        "source_artifact": "scripts/aios_boundary_probe.py",
        "draft_id": f"probe:{kind}:{uuid.uuid4().hex[:6]}",
        "return_to": f".aios/outbox/memoryOS/{req_id}.memoryOS.result.json",
        "review_policy": {"auto_accept": False, "draft_first": True},
        "draft": {
            "type": "question",
            "origin": "aios_boundary_probe",
            "status": "draft",
            "confidence": 0.4,
            "content": content,
            "raw_refs": ["scripts/aios_boundary_probe.py"],
            "provenance": {
                "source": "aios_boundary_probe",
                "kind": kind,
                "target_id": target_id,
                "generated_at": _now_iso(),
                **extra_provenance,
            },
            "project": "AIOS",
        },
        "scope": {"allowed_files": [], "forbidden_files": [".env"]},
        "created_at": _now_iso(),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="ASC-0211 L3 routine #4 — boundary probe via GenesisOS")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--target", type=Path,
                   help="contract file to probe (its full text fed to critic)")
    g.add_argument("--text-file", type=Path,
                   help="arbitrary text file to probe")
    p.add_argument("--cross-domain-n", type=int, default=2,
                   help="how many cross-domain probes to generate")
    p.add_argument("--skip-genesis", action="store_true",
                   help="don't call GenesisOS critic; only emit cross-domain probes")
    p.add_argument("--out-dir", type=Path,
                   default=REPO_ROOT / ".aios" / "inbox" / "memoryOS")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    if args.target:
        target_text = args.target.read_text(encoding="utf-8", errors="replace")
        target_id = args.target.stem
    else:
        target_text = args.text_file.read_text(encoding="utf-8", errors="replace")
        target_id = args.text_file.stem

    drafts: list[dict[str, Any]] = []
    critic_result: dict[str, Any] = {}

    if not args.skip_genesis:
        critic_result = run_genesis_critic(target_text)
        if critic_result.get("ok") and "result" in critic_result:
            for sig in critic_result["result"].get("prison_signatures", [])[:3]:
                drafts.append(signature_to_draft(target_id, sig))

    drafts.extend(cross_domain_drafts(target_id, args.cross_domain_n))

    written: list[str] = []
    if not args.dry_run:
        args.out_dir.mkdir(parents=True, exist_ok=True)
        for d in drafts:
            pf = args.out_dir / f"{d['request_id']}.memoryOS.json"
            pf.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
            written.append(pf.as_posix())

    out = {
        "schema_version": "aios.boundary_probe.v1",
        "target": target_id,
        "genesis_critic": critic_result.get("ok"),
        "generated": len(drafts),
        "written": written,
        "dry_run": args.dry_run,
        "drafts": drafts if args.dry_run else None,
    }
    if args.json:
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        print(f"target: {target_id}")
        print(f"genesis critic ok: {critic_result.get('ok')}")
        if critic_result.get("ok") and critic_result.get("result"):
            sigs = critic_result["result"].get("prison_signatures", [])
            print(f"  prison_signatures from critic: {len(sigs)}")
        print(f"drafts generated: {len(drafts)}")
        for d in drafts:
            kind = d["draft"]["provenance"]["kind"]
            content = d["draft"]["content"]
            print(f"  [{kind}] {content}")
        if args.dry_run:
            print("(dry-run: no files written)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

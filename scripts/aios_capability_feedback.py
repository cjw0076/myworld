#!/usr/bin/env python3
"""aios capability-feedback — closes the CapabilityOS observation loop.

The 2026-05-17 internal audit found: helper invocations are logged richly to
`.aios/helpers/observations.jsonl` (every run, with verified outcomes from
aios_verify), but `recommend` never reads them — the helper catalog cards
ship with no `observation_count`, so routing runs blind to usage history.
The feedback loop existed in code but was not closed.

This organ closes it: it folds the observation log back into the catalog —
per helper, the invocation count and the verified-good count are written
onto the card. CapabilityOS `recommend` (which reads `observation_count`
from the catalog) then ranks by what has actually been used and verified.

CapabilityOS stays recommendation-only — it reads the catalog; this
myworld-side organ maintains it. Idempotent.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CATALOG_REL = ".aios/helpers/catalog.json"
OBSERVATIONS_REL = ".aios/helpers/observations.jsonl"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def cmd_run(root: Path, json_mode: bool) -> int:
    catalog_path = root / CATALOG_REL
    obs_path = root / OBSERVATIONS_REL
    if not catalog_path.exists():
        print("error: helper catalog not found", file=sys.stderr)
        return 2

    # aggregate observations per helper
    counts: dict[str, dict[str, int]] = {}
    if obs_path.exists():
        for line in obs_path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue
            hid = row.get("helper_id")
            if not hid:
                continue
            c = counts.setdefault(hid, {"invocations": 0, "verified_good": 0, "verified_bad": 0})
            c["invocations"] += 1
            if row.get("verified") is True:
                c["verified_good"] += 1
            elif row.get("verified") is False:
                c["verified_bad"] += 1

    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    folded = []
    for card in catalog.get("capabilities", []):
        hid = card.get("id")
        c = counts.get(hid)
        if not c:
            continue
        # observation_count is what CapabilityOS recommend reads to rank by usage
        card["observation_count"] = c["invocations"]
        card["verified_good_count"] = c["verified_good"]
        card["verified_bad_count"] = c["verified_bad"]
        card["observations_folded_at"] = now_iso()
        folded.append({"helper": hid, **c})

    catalog_path.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    summary = {
        "schema": "aios.capability_feedback.v1",
        "ran_at": now_iso(),
        "helpers_folded": len(folded),
        "detail": folded,
        "note": "observation history folded into helper catalog observation_count; "
                "CapabilityOS recommend now ranks by actual verified usage",
    }
    if json_mode:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        for f in folded:
            print(f"  {f['helper']}: {f['invocations']} invocations "
                  f"({f['verified_good']} verified-good, {f['verified_bad']} bad)")
        print(f"-- folded observations for {len(folded)} helper(s) into the catalog")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="AIOS capability feedback — close the observation loop")
    p.add_argument("--root", default=".")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    return cmd_run(Path(args.root).resolve(), args.json)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env bash
set -euo pipefail

ROOT="${AIOS_COEVOLUTION_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
WORK_DIR="$ROOT/.aios/primitives/coevolution"
MEMORY_ROOT="$WORK_DIR/memory_root"
SCOUT_JSON="$WORK_DIR/doc_scout.latest.json"
INGEST_JSON="$WORK_DIR/memory_ingest.latest.json"

mkdir -p "$WORK_DIR" "$MEMORY_ROOT"
cd "$ROOT"

if [[ "${AIOS_COEVOLUTION_TEST_MODE:-0}" == "1" ]]; then
  cat >"$SCOUT_JSON" <<'JSON'
{"schema_version":"aios.doc_scout.v1","top_tasks":[{"path":"myworld/docs/AIOS_DEFINITION.md","domain":"myworld","score":1,"signals":{"counts":{"aios":1},"line_samples":{"aios":[1]}},"line_span":[1,1],"candidate_task":"test signal"}],"scout_run_id":"test"}
JSON
else
  python scripts/aios_doc_scout.py --root /home/user/workspaces/jaewon --json >"$SCOUT_JSON"
fi

if [[ "${AIOS_COEVOLUTION_TEST_MODE:-0}" == "1" ]]; then
  cat >"$INGEST_JSON" <<'JSON'
{"schema_version":"ASC-0008.doc_radar_ingest.v1","dry_run":false,"memory_objects":{"new_count":1,"skipped_count":0},"warnings":[]}
JSON
else
  (
    cd "$ROOT/memoryOS"
    python -m memoryos.cli --root "$MEMORY_ROOT" ingest-doc-radar "$SCOUT_JSON" --json >"$INGEST_JSON"
  )
fi

python - "$SCOUT_JSON" "$INGEST_JSON" <<'PY'
import json
import sys
from pathlib import Path

scout = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
ingest = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
top_tasks = scout.get("top_tasks") or []
memory = ingest.get("memory_objects") or {}
imported = memory.get("new_count", memory.get("created", 0))
skipped = memory.get("skipped_count", memory.get("skipped", 0))
warnings = len(ingest.get("warnings") or [])
print(f"memory_pulse stage=done scout_signals={len(top_tasks)} imported={imported} skipped={skipped} warnings={warnings}")
PY

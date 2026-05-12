#!/usr/bin/env bash
set -euo pipefail

ROOT="${AIOS_COEVOLUTION_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
WORK_DIR="$ROOT/.aios/primitives/coevolution"
DISPATCH_JSON="$WORK_DIR/dispatch_status.latest.json"
RECOMMEND_JSON="$WORK_DIR/hive_routing_recommendation.json"

mkdir -p "$WORK_DIR"
cd "$ROOT"

if [[ "${AIOS_COEVOLUTION_TEST_MODE:-0}" == "1" ]]; then
  cat >"$DISPATCH_JSON" <<'JSON'
{"dispatches":[{"dispatch_id":"asc-test","status":"sent","contract_id":"ASC-TEST"}]}
JSON
  cat >"$RECOMMEND_JSON" <<'JSON'
{"contract":"capabilityos.recommendations.v1","recommendations":[{"id":"cap_hivemind_execution_harness","score":10}],"recommendation_only":true}
JSON
else
  python scripts/aios_dispatch.py status --json >"$DISPATCH_JSON"
  (
    cd "$ROOT/CapabilityOS"
    python -m capabilityos.cli recommend \
      --task "hivemind execution harness routing for current AIOS state" \
      --observations-inbox "$ROOT/.aios/outbox" \
      --radar "$ROOT/docs/AIOS_TASK_RADAR.md" \
      --json >"$RECOMMEND_JSON"
  )
fi

python - "$DISPATCH_JSON" "$RECOMMEND_JSON" "$ROOT/docs/AIOS_TASK_RADAR.md" <<'PY'
import json
import sys
from pathlib import Path

dispatch = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
recommend = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
radar_path = Path(sys.argv[3])
statuses = [str(row.get("status", "")) for row in dispatch.get("dispatches", [])]
in_flight = sum(1 for status in statuses if status in {"created", "sent", "collected"})
radar_hive = 0
if radar_path.exists():
    radar_hive = sum(1 for line in radar_path.read_text(encoding="utf-8", errors="replace").splitlines() if "hive" in line.lower())
top = (recommend.get("recommendations") or [{}])[0].get("id", "none")
print(f"hive_pulse stage=done dispatch_in_flight={in_flight} radar_hive_lines={radar_hive} top_route={top}")
PY

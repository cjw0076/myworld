#!/usr/bin/env bash
set -euo pipefail

ROOT="${AIOS_COEVOLUTION_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
WORK_DIR="$ROOT/.aios/primitives/coevolution"
OBS_JSON="$WORK_DIR/capability_observations.latest.json"
AUDIT_JSON="$WORK_DIR/capability_audit.latest.json"

mkdir -p "$WORK_DIR"

if [[ "${AIOS_COEVOLUTION_TEST_MODE:-0}" == "1" ]]; then
  cat >"$OBS_JSON" <<'JSON'
{"contract":"capabilityos.observations.v1","recommendation_only":true,"result_files":1,"observations_count":1,"gaps":[]}
JSON
  cat >"$AUDIT_JSON" <<'JSON'
{"contract":"capabilityos.audit.v1","status":"ok","recommendation_only":true,"execution_enabled":[]}
JSON
else
  (
    cd "$ROOT/CapabilityOS"
    python -m capabilityos.cli observe-results --inbox "$ROOT/.aios/outbox" --json >"$OBS_JSON"
    python -m capabilityos.cli audit --json >"$AUDIT_JSON"
  )
fi

python - "$OBS_JSON" "$AUDIT_JSON" <<'PY'
import json
import sys
from pathlib import Path

obs = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
audit = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
print(
    "capability_pulse "
    f"stage=done result_files={obs.get('result_files', 0)} "
    f"observations={obs.get('observations_count', 0)} "
    f"gaps={len(obs.get('gaps') or [])} "
    f"recommendation_only={str(audit.get('recommendation_only')).lower()} "
    f"audit_status={audit.get('status')}"
)
PY

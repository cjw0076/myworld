#!/usr/bin/env bash
# GenesisOS pulse — runs every INTERVAL seconds (set by arm.sh / systemd / cron).
# Reads recent AIOS self_check events, invokes genesis critic on failures,
# and writes challenges to .aios/genesis_challenges/.
#
# This closes the gap: GenesisOS was invoked manually only (last: 2026-05-20).
# Now it runs on every pulse loop cycle and challenges the current AIOS state.
set -euo pipefail

ROOT="${AIOS_COEVOLUTION_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
WORK_DIR="$ROOT/.aios/primitives/coevolution"
GENESIS_OUT_DIR="$ROOT/.aios/genesis_challenges"
GENESIS_ROOT="$ROOT/GenesisOS"
EVENTS_LOG="$ROOT/.aios/primitives/events.jsonl"

mkdir -p "$WORK_DIR" "$GENESIS_OUT_DIR"
cd "$ROOT"

# --- build a snapshot of recent AIOS health to give genesis context ---
SNAPSHOT_FILE="$WORK_DIR/genesis_health_snapshot.txt"

if [[ "${AIOS_COEVOLUTION_TEST_MODE:-0}" == "1" ]]; then
  echo "TEST MODE: AIOS has 0 real failures and dispatch is healthy." > "$SNAPSHOT_FILE"
else
  python3 - "$EVENTS_LOG" > "$SNAPSHOT_FILE" <<'PY'
import json, sys
from pathlib import Path

log = Path(sys.argv[1])
if not log.exists():
    print("events.jsonl not found")
    sys.exit(0)

lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
recent = []
for line in reversed(lines[-500:]):  # last 500 events
    line = line.strip()
    if not line:
        continue
    try:
        e = json.loads(line)
        if e.get("name") == "aios-self-check":
            payload = e.get("payload", {}).get("line", "")
            recent.append(payload)
    except Exception:
        pass
    if len(recent) >= 20:
        break

failures = [r for r in recent if "FAILURE_REAL" in r or "DAEMON_DEAD" in r or "PARSE_BROKEN" in r]
passed = [r for r in recent if "pass complete" in r]

print(f"Recent AIOS self_check (last 20 events):")
for r in recent[:10]:
    print(f"  {r}")
print(f"\nFailure events: {len(failures)}")
print(f"Pass events: {len(passed)}")
if failures:
    print(f"\nFailure details:")
    for f in failures[:5]:
        print(f"  {f}")
PY
fi

# --- invoke genesis critic on the health snapshot ---
CHALLENGE_OUT="$GENESIS_OUT_DIR/auto_$(date +%Y%m%dT%H%M%S).json"

if [[ ! -d "$GENESIS_ROOT" ]]; then
  echo "GenesisOS not found at $GENESIS_ROOT — skipping"
  exit 0
fi

( cd "$GENESIS_ROOT" && python3 -m genesisos.cli critic \
    --text "$SNAPSHOT_FILE" \
    --json ) \
  > "$CHALLENGE_OUT" 2>/dev/null \
  && echo "genesis_pulse: challenge written to $CHALLENGE_OUT" \
  || echo "genesis_pulse: critic failed (continuing)"

# --- emit event to primitive bus ---
python3 - "$CHALLENGE_OUT" "$ROOT/.aios/primitives/events.jsonl" <<'PY'
import json, sys
from pathlib import Path
from datetime import datetime, timezone

challenge_path = Path(sys.argv[1])
events_path = Path(sys.argv[2])
events_path.parent.mkdir(parents=True, exist_ok=True)

challenge = {}
try:
    challenge = json.loads(challenge_path.read_text(encoding="utf-8"))
except Exception:
    pass

record = {
    "schema_version": "aios.primitive_event.v1",
    "kind": "genesis_pulse",
    "name": "aios-genesis-pulse",
    "ts_iso": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    "payload": {
        "challenge_path": str(challenge_path),
        "confidence": challenge.get("confidence"),
        "prison_signature_count": len(challenge.get("prison_signatures", [])),
        "soft_block": challenge.get("soft_block", False),
    }
}

with events_path.open("a", encoding="utf-8") as f:
    f.write(json.dumps(record, ensure_ascii=False) + "\n")
print(json.dumps(record, ensure_ascii=False))
PY

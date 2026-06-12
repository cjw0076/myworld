#!/usr/bin/env bash
# Stop hook — AIOS session closeout.
# Runs when the CLI session ends (Stop event).
# DNA invariant alignment:
#   #3 (append-only): process events before session dies
#   #5 (provenance): update self-record so next session re-meets its track record
#
# Fails open — any error just skips gracefully.
set +e

ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$ROOT" || exit 0

# 1. write session checkpoint — carry state to next session
GOAL_TEXT=$(cat "$ROOT/.aios/current_goal.txt" 2>/dev/null || echo "")
python3 "$ROOT/scripts/aios_checkpoint.py" write \
  ${GOAL_TEXT:+--goal "$GOAL_TEXT"} \
  >/dev/null 2>&1 || true

# 2. process pending primitive events
python3 scripts/aios_event_processor.py once >/dev/null 2>&1 || true

# 3. update self-record (aios_self.py if it exists)
python3 scripts/aios_self.py >/dev/null 2>&1 || true

# 3. count what happened in this session
EVENT_CURSOR=$(cat .aios/event_processor_cursor 2>/dev/null || echo "0")
GENESIS_COUNT=$(ls .aios/genesis_challenges/auto_*.json 2>/dev/null | wc -l | tr -d ' ')

# 4. emit a brief session-close event to the bus
python3 - "$ROOT" "$GENESIS_COUNT" <<'PY' 2>/dev/null || true
import json, sys
from pathlib import Path
from datetime import datetime, timezone

root = Path(sys.argv[1])
genesis_count = sys.argv[2]
events_path = root / ".aios" / "primitives" / "events.jsonl"
events_path.parent.mkdir(parents=True, exist_ok=True)

record = {
    "schema_version": "aios.primitive_event.v1",
    "kind": "session_stop",
    "name": "aios-session-stop",
    "ts_iso": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    "payload": {"genesis_challenges_total": genesis_count},
}
with events_path.open("a", encoding="utf-8") as f:
    f.write(json.dumps(record, ensure_ascii=False) + "\n")
PY

# 5. show work intake backlog count
BACKLOG=$(grep -c "^| WORK-" "$ROOT/.aios/WORK_INTAKE.md" 2>/dev/null || echo "0")

echo "{\"systemMessage\": \"AIOS session closeout — events processed. Work backlog: ${BACKLOG} items. See .aios/WORK_INTAKE.md\"}"

#!/usr/bin/env bash
set -euo pipefail

# AIOS control-tower pingpong loop.
#
# This script runs Codex and Claude from the myworld root so they can act as
# control-plane agents. The loop is intentionally bounded by explicit stop
# files, not by chat state.
#
# Stop conditions:
#   - .aios/STOP exists
#   - .aios/NORTHSTAR_READY exists, unless AIOS_CONTINUE_AFTER_READY=1
#   - docs/AIOS_NORTHSTAR_READY.md exists, unless AIOS_CONTINUE_AFTER_READY=1
#   - AIOS_MAX_ROUNDS is set to a positive number and reached
#
# The agents should dispatch work to child repos instead of directly editing
# implementation files unless an AIOS contract explicitly grants scope.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AIOS_DIR="$ROOT/.aios"
STATE_DIR="$AIOS_DIR/state"
LOG_DIR="$AIOS_DIR/logs"
PROMPT_DIR="$AIOS_DIR/prompts"
RUN_DIR="$AIOS_DIR/run"
PID_FILE="$RUN_DIR/aios_pingpong.pid"
STOP_FILE="$AIOS_DIR/STOP"
READY_FILE="$AIOS_DIR/NORTHSTAR_READY"
READY_DOC="$ROOT/docs/AIOS_NORTHSTAR_READY.md"
STATE_FILE="$STATE_DIR/aios_pingpong.state"

CODEX_TIMEOUT="${CODEX_TIMEOUT:-1800}"
CLAUDE_TIMEOUT="${CLAUDE_TIMEOUT:-1800}"
CLAUDE_MODEL="${CLAUDE_MODEL:-claude-opus-4-6}"
AIOS_MAX_ROUNDS="${AIOS_MAX_ROUNDS:-0}"
AIOS_START_CHILD_WATCHERS="${AIOS_START_CHILD_WATCHERS:-0}"
AIOS_CONTINUE_AFTER_READY="${AIOS_CONTINUE_AFTER_READY:-0}"

mkdir -p "$STATE_DIR" "$LOG_DIR" "$PROMPT_DIR" "$RUN_DIR"

usage() {
  cat <<'USAGE'
Usage:
  scripts/aios_pingpong.sh start     Start background Codex/Claude loop
  scripts/aios_pingpong.sh run       Run foreground loop
  scripts/aios_pingpong.sh once      Run one agent turn
  scripts/aios_pingpong.sh status    Show loop state
  scripts/aios_pingpong.sh stop      Request stop and kill background pid if present
  scripts/aios_pingpong.sh reset     Clear STOP and state, keep logs/prompts

Environment:
  CLAUDE_MODEL=claude-opus-4-6
  CODEX_TIMEOUT=1800
  CLAUDE_TIMEOUT=1800
  AIOS_MAX_ROUNDS=0       # 0 means no round cap
  AIOS_START_CHILD_WATCHERS=0
  AIOS_CONTINUE_AFTER_READY=0

Stop by creating:
  .aios/STOP

Mark north star done by creating either:
  .aios/NORTHSTAR_READY
  docs/AIOS_NORTHSTAR_READY.md
USAGE
}

now_iso() {
  date -Iseconds
}

current_round() {
  if [[ -f "$STATE_FILE" ]]; then
    awk -F= '$1=="round"{print $2}' "$STATE_FILE" | tail -1
  else
    echo "0"
  fi
}

current_agent() {
  if [[ -f "$STATE_FILE" ]]; then
    awk -F= '$1=="next_agent"{print $2}' "$STATE_FILE" | tail -1
  else
    echo "codex"
  fi
}

write_state() {
  local round="$1"
  local next_agent="$2"
  local status="$3"
  {
    echo "round=$round"
    echo "next_agent=$next_agent"
    echo "status=$status"
    echo "updated_at=$(now_iso)"
  } > "$STATE_FILE"
}

append_event() {
  local event="$1"
  local agent="${2:-}"
  local status="${3:-}"
  local detail="${4:-}"
  python3 - "$STATE_DIR/aios_pingpong.jsonl" "$event" "$agent" "$status" "$detail" <<'PY'
import json
import sys
from datetime import datetime, timezone

path, event, agent, status, detail = sys.argv[1:]
row = {
    "timestamp": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    "event": event,
    "agent": agent,
    "status": status,
    "detail": detail,
}
with open(path, "a", encoding="utf-8") as fh:
    fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
PY
}

northstar_ready() {
  [[ -f "$READY_FILE" || -f "$READY_DOC" ]]
}

should_stop() {
  if [[ -f "$STOP_FILE" ]]; then
    return 0
  fi
  if [[ "$AIOS_CONTINUE_AFTER_READY" != "1" ]] && northstar_ready; then
    return 0
  fi
  return 1
}

other_agent() {
  case "$1" in
    codex) echo "claude" ;;
    claude) echo "codex" ;;
    *) echo "codex" ;;
  esac
}

build_prompt() {
  local agent="$1"
  local round="$2"
  local prompt_file="$3"
  cat > "$prompt_file" <<EOF
You are ${agent}@myworld, operating from the MyWorld AIOS control tower.

Current time: $(now_iso)
Round: ${round}
Workspace root: ${ROOT}

North star:
- Continue building MyWorld as the AIOS control tower.
- Do not stop merely because a document exists.
- Stop only when the AIOS north star is operationally clear enough that a future agent can run:
  goal -> contract -> MemoryOS context -> CapabilityOS route -> Hive Mind execution -> receipts -> memory/capability observations -> operator closeout.

Required reading before edits:
- AGENTS.md
- docs/README.md
- docs/AIOS_NORTHSTAR.md
- docs/AIOS_DEFINITION.md
- docs/AIOS_WORK_DISPATCH.md
- docs/AIOS_SMART_CONTRACT.md
- docs/AIOS_AGENT_PROTOCOL.md
- docs/WORKSTREAMS.md
- docs/AIOS_AGENT_LEDGER.md
- docs/agents/HIVEMIND_AGENT.md
- docs/agents/MEMORYOS_AGENT.md
- docs/agents/CAPABILITYOS_AGENT.md

Operating rules:
- myworld is the control tower, not the fourth implementation repo.
- Do not claim AIOS progress unless the work advances one of the AIOS
  completion levels in docs/AIOS_DEFINITION.md.
- Prefer contracts, dispatch packets, workstream docs, monitor/loop surfaces, and ledger entries.
- Implementation inside hivemind/, memoryOS/, or CapabilityOS/ should happen only when an accepted AIOS smart contract explicitly assigns that repo and scope.
- Preserve private data. Do not read or paste raw exports, secrets, stdout/stderr bodies, or personal data.
- If ownership or privacy is ambiguous, write an operator checkpoint instead of guessing.
- If you modify files, append a concise entry to docs/AIOS_AGENT_LEDGER.md with when/repo/agent/role/goal/changed/evidence/decision/risk/next/status.

Suggested next actions:
1. Inspect current contracts and dispatch state.
2. Tighten any missing control-tower automation needed for a self-explaining AIOS loop.
3. If the north star is complete enough, create docs/AIOS_NORTHSTAR_READY.md with evidence and stop criteria.
4. Otherwise, make one bounded improvement and leave the next handoff clear.

Useful commands:
- python3 scripts/aios_loop.py once --json
- python3 scripts/aios_loop.py once --apply --json
- python3 scripts/aios_dispatch.py status --json
- python3 scripts/aios_monitor.py snapshot --json --write
- find docs/contracts -maxdepth 1 -type f -name 'ASC-*.md' | sort

Do one bounded turn. Keep output concise. Do not start another infinite loop.
EOF
}

run_agent() {
  local agent="$1"
  local round="$2"
  local prompt_file="$PROMPT_DIR/round-${round}-${agent}.md"
  local log_file="$LOG_DIR/round-${round}-${agent}.log"
  build_prompt "$agent" "$round" "$prompt_file"

  append_event "agent_start" "$agent" "running" "$prompt_file"
  echo "[$(now_iso)] running ${agent} round ${round}"

  local rc=0
  if [[ "$agent" == "codex" ]]; then
    if ! command -v codex >/dev/null 2>&1; then
      echo "codex command not found" | tee "$log_file"
      rc=127
    else
      timeout "$CODEX_TIMEOUT" codex exec --dangerously-bypass-approvals-and-sandbox "$(cat "$prompt_file")" \
        >"$log_file" 2>&1 || rc=$?
    fi
  elif [[ "$agent" == "claude" ]]; then
    if ! command -v claude >/dev/null 2>&1; then
      echo "claude command not found" | tee "$log_file"
      rc=127
    else
      timeout "$CLAUDE_TIMEOUT" claude --dangerously-skip-permissions --model "$CLAUDE_MODEL" -p "$(cat "$prompt_file")" \
        >"$log_file" 2>&1 || rc=$?
    fi
  else
    echo "unknown agent: $agent" | tee "$log_file"
    rc=2
  fi

  if [[ "$rc" -eq 0 ]]; then
    append_event "agent_done" "$agent" "ok" "$log_file"
  elif [[ "$rc" -eq 124 ]]; then
    append_event "agent_timeout" "$agent" "timeout" "$log_file"
    touch "$STOP_FILE"
  else
    append_event "agent_failed" "$agent" "exit_${rc}" "$log_file"
    touch "$STOP_FILE"
  fi
  return "$rc"
}

run_once() {
  cd "$ROOT"
  if should_stop; then
    echo "AIOS loop stop condition is already set."
    append_event "stop_condition" "" "stop" "ready_or_stop_file"
    return 0
  fi

  local round
  round="$(current_round)"
  round=$((round + 1))
  local agent
  agent="$(current_agent)"

  write_state "$round" "$agent" "running"
  set +e
  run_agent "$agent" "$round"
  local rc=$?
  set -e

  local next
  next="$(other_agent "$agent")"
  if should_stop; then
    write_state "$round" "$next" "stopped"
  else
    write_state "$round" "$next" "waiting"
  fi
  return "$rc"
}

run_loop() {
  cd "$ROOT"
  append_event "loop_start" "" "running" "$ROOT"
  while true; do
    if should_stop; then
      append_event "loop_stop" "" "stop" "ready_or_stop_file"
      echo "AIOS loop stopped."
      break
    fi
    local round
    round="$(current_round)"
    if [[ "$AIOS_MAX_ROUNDS" -gt 0 && "$round" -ge "$AIOS_MAX_ROUNDS" ]]; then
      append_event "loop_stop" "" "max_rounds" "$AIOS_MAX_ROUNDS"
      echo "AIOS loop reached AIOS_MAX_ROUNDS=${AIOS_MAX_ROUNDS}."
      break
    fi
    run_once || true
    sleep 2
  done
}

cmd_start() {
  if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "AIOS pingpong already running: pid $(cat "$PID_FILE")"
    return 0
  fi
  rm -f "$STOP_FILE"
  if [[ "$AIOS_START_CHILD_WATCHERS" == "1" ]]; then
    "$ROOT/scripts/aios_child_watcher.sh" start --repo all
  fi
  nohup "$0" run > "$LOG_DIR/aios_pingpong.supervisor.log" 2>&1 &
  echo "$!" > "$PID_FILE"
  echo "started AIOS pingpong pid $(cat "$PID_FILE")"
}

cmd_status() {
  echo "root=$ROOT"
  echo "pid_file=$PID_FILE"
  if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "running=true pid=$(cat "$PID_FILE")"
  else
    echo "running=false"
  fi
  if [[ -f "$STATE_FILE" ]]; then
    cat "$STATE_FILE"
  else
    echo "round=0"
    echo "next_agent=codex"
    echo "status=not_started"
  fi
  [[ -f "$STOP_FILE" ]] && echo "stop_file=true" || echo "stop_file=false"
  northstar_ready && echo "northstar_ready=true" || echo "northstar_ready=false"
  echo "continue_after_ready=$AIOS_CONTINUE_AFTER_READY"
  echo "logs=$LOG_DIR"
}

cmd_stop() {
  touch "$STOP_FILE"
  append_event "stop_requested" "" "stop" "manual"
  if [[ -x "$ROOT/scripts/aios_child_watcher.sh" ]]; then
    "$ROOT/scripts/aios_child_watcher.sh" stop --repo all || true
  fi
  if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    kill "$(cat "$PID_FILE")" || true
    echo "stopped pid $(cat "$PID_FILE")"
  else
    echo "stop requested; no running pid"
  fi
}

cmd_reset() {
  rm -f "$STOP_FILE" "$STATE_FILE" "$PID_FILE"
  append_event "reset" "" "ok" "state_cleared"
  echo "reset AIOS pingpong state"
}

case "${1:-}" in
  start) cmd_start ;;
  run) run_loop ;;
  once) run_once ;;
  status) cmd_status ;;
  stop) cmd_stop ;;
  reset) cmd_reset ;;
  -h|--help|help|"") usage ;;
  *)
    echo "unknown command: $1" >&2
    usage >&2
    exit 2
    ;;
esac

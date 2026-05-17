#!/usr/bin/env bash
set -euo pipefail

# Child-repo AIOS watcher.
#
# Reads myworld/.aios/inbox/<repo>/*.json, runs the assigned agent from inside
# the target repo, and writes myworld/.aios/outbox/<repo>/*.result.json.
#
# This is the bridge between the myworld control tower and repo-local agents.
# It does not choose goals. It only executes accepted dispatch packets.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AIOS_DIR="$ROOT/.aios"
INBOX_DIR="$AIOS_DIR/inbox"
OUTBOX_DIR="$AIOS_DIR/outbox"
LOG_DIR="$AIOS_DIR/logs"
PROMPT_DIR="$AIOS_DIR/prompts"
RUN_DIR="$AIOS_DIR/run"
STATE_DIR="$AIOS_DIR/state"
STOP_FILE="$AIOS_DIR/STOP"

CODEX_TIMEOUT="${CODEX_TIMEOUT:-1800}"
CLAUDE_TIMEOUT="${CLAUDE_TIMEOUT:-1800}"
GEMINI_TIMEOUT="${GEMINI_TIMEOUT:-1800}"
LOCAL_TIMEOUT="${LOCAL_TIMEOUT:-600}"
CLAUDE_MODEL="${CLAUDE_MODEL:-claude-opus-4-6}"
WATCH_INTERVAL="${WATCH_INTERVAL:-5}"
AIOS_CHILD_AGENT_FALLBACKS="${AIOS_CHILD_AGENT_FALLBACKS:-1}"
AIOS_CHILD_PREFER_PROVIDER_BEFORE_LOCAL="${AIOS_CHILD_PREFER_PROVIDER_BEFORE_LOCAL:-1}"

mkdir -p "$OUTBOX_DIR" "$LOG_DIR" "$PROMPT_DIR" "$RUN_DIR" "$STATE_DIR"

usage() {
  cat <<'USAGE'
Usage:
  scripts/aios_child_watcher.sh once --repo <repo>
  scripts/aios_child_watcher.sh run --repo <repo>
  scripts/aios_child_watcher.sh start --repo <repo|all>
  scripts/aios_child_watcher.sh stop --repo <repo|all>
  scripts/aios_child_watcher.sh status

Repos:
  hivemind
  memoryOS
  CapabilityOS
  GenesisOS

Environment:
  CLAUDE_MODEL=claude-opus-4-6
  CODEX_TIMEOUT=1800
  CLAUDE_TIMEOUT=1800
  GEMINI_TIMEOUT=1800
  LOCAL_TIMEOUT=600
  WATCH_INTERVAL=5
  AIOS_CHILD_AGENT_FALLBACKS=1
  AIOS_CHILD_PREFER_PROVIDER_BEFORE_LOCAL=1

Global stop file:
  .aios/STOP
USAGE
}

now_iso() {
  date -Iseconds
}

append_event() {
  local event="$1"
  local repo="${2:-}"
  local status="${3:-}"
  local detail="${4:-}"
  python3 - "$STATE_DIR/child_watchers.jsonl" "$event" "$repo" "$status" "$detail" <<'PY'
import json
import sys
from datetime import datetime, timezone

path, event, repo, status, detail = sys.argv[1:]
row = {
    "timestamp": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    "event": event,
    "repo": repo,
    "status": status,
    "detail": detail,
}
with open(path, "a", encoding="utf-8") as fh:
    fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
PY
}

repo_path() {
  case "$1" in
    hivemind) echo "$ROOT/hivemind" ;;
    memoryOS) echo "$ROOT/memoryOS" ;;
    CapabilityOS) echo "$ROOT/CapabilityOS" ;;
    GenesisOS) echo "$ROOT/GenesisOS" ;;
    *) return 1 ;;
  esac
}

validate_repo() {
  repo_path "$1" >/dev/null || {
    echo "unsupported repo: $1" >&2
    exit 2
  }
}

json_get() {
  local file="$1"
  local expr="$2"
  python3 - "$file" "$expr" <<'PY'
import json
import sys

path, expr = sys.argv[1:]
data = json.load(open(path, encoding="utf-8"))
cur = data
for part in expr.split("."):
    if not part:
        continue
    if isinstance(cur, dict):
        cur = cur.get(part, "")
    else:
        cur = ""
if isinstance(cur, (dict, list)):
    print(json.dumps(cur, ensure_ascii=False))
elif cur is None:
    print("")
else:
    print(str(cur))
PY
}

packet_result_path() {
  local packet="$1"
  local repo="$2"
  local dispatch_id
  dispatch_id="$(json_get "$packet" "dispatch_id")"
  local return_to
  return_to="$(json_get "$packet" "return_to")"
  if [[ -n "$return_to" ]]; then
    echo "$ROOT/$return_to"
  else
    echo "$OUTBOX_DIR/$repo/${dispatch_id}.${repo}.result.json"
  fi
}

git_status_short() {
  local dir="$1"
  if [[ -d "$dir/.git" ]]; then
    git -C "$dir" status --short --untracked-files=all || true
  fi
}

related_dirty_status() {
  local repo="$1"
  local status_file="$2"
  local packet="$3"
  python3 - "$repo" "$status_file" "$packet" <<'PY'
import json
import sys
from pathlib import Path

repo, status_file, packet_path = sys.argv[1:]
packet = json.load(open(packet_path, encoding="utf-8"))
allowed = packet.get("scope", {}).get("allowed_files") or []
normalized = []
for raw in allowed:
    value = str(raw).strip().strip("`")
    value = value.replace("` read-only", "").replace(" read-only", "").strip()
    if value.startswith(f"{repo}/"):
        value = value[len(repo) + 1 :]
    if value:
        normalized.append(value.rstrip("/"))

for line in Path(status_file).read_text(encoding="utf-8", errors="replace").splitlines():
    if not line.strip():
        continue
    path = line[3:].strip() if len(line) > 3 else line.strip()
    for allowed_path in normalized:
        if path == allowed_path or path.startswith(f"{allowed_path}/"):
            print(line)
            break
PY
}

build_prompt() {
  local repo="$1"
  local packet="$2"
  local prompt_file="$3"
  local contract_id dispatch_id goal target_agent contract_path allowed forbidden
  contract_id="$(json_get "$packet" "contract_id")"
  dispatch_id="$(json_get "$packet" "dispatch_id")"
  goal="$(json_get "$packet" "goal")"
  target_agent="$(json_get "$packet" "agent")"
  contract_path="$(json_get "$packet" "contract_path")"
  allowed="$(json_get "$packet" "scope.allowed_files")"
  forbidden="$(json_get "$packet" "scope.forbidden_files")"

  cat > "$prompt_file" <<EOF
You are ${target_agent}@${repo}, invoked by the myworld AIOS child watcher.

Current time: $(now_iso)
MyWorld root: ${ROOT}
Target repo: ${repo}
Target repo path: $(repo_path "$repo")
Contract: ${contract_id}
Dispatch: ${dispatch_id}
Contract path: ${contract_path}

Goal:
${goal}

Required reading:
- ${ROOT}/AGENTS.md
- ${ROOT}/docs/AIOS_NORTHSTAR.md
- ${ROOT}/docs/AIOS_DEFINITION.md
- ${ROOT}/docs/AIOS_SHARED_LANGUAGE.md
- ${ROOT}/docs/AIOS_WORK_DISPATCH.md
- ${ROOT}/docs/AIOS_SMART_CONTRACT.md
- ${ROOT}/docs/AIOS_AGENT_PROTOCOL.md
- ${ROOT}/${contract_path}
- Repo-local AGENTS.md or README.md if present

Scope:
Allowed files JSON:
${allowed}

Forbidden files JSON:
${forbidden}

Operating rules:
- Start with a semantic_handshake: name the contract, target repo, confirmed
  AIOS terms from ${ROOT}/docs/AIOS_SHARED_LANGUAGE.md, and ambiguous_terms.
  If ambiguous_terms is not empty, stop at a checkpoint.
- Work from inside the target repo.
- Do not claim AIOS progress unless the work advances one of the AIOS
  completion levels in ${ROOT}/docs/AIOS_DEFINITION.md.
- Respect repo-local AGENTS.md and existing worklogs.
- Do only the slice owned by ${repo}.
- Do not touch forbidden paths.
- Do not paste private raw exports, secrets, stdout/stderr bodies, or local-only data.
- If the dispatch is already satisfied, verify and write a concise result.
- If ownership/scope is ambiguous, stop and explain the checkpoint instead of broadening scope.
- Leave a repo-local worklog entry when the repo has an AGENT_WORKLOG or equivalent.
- The watcher will write the outbox JSON; your stdout can be a concise human summary.

Do one bounded turn. Do not start another watcher or infinite loop.
EOF
}

write_result() {
  local result_path="$1"
  local repo="$2"
  local packet="$3"
  local status="$4"
  local exit_code="$5"
  local prompt_file="$6"
  local log_file="$7"
  local before_file="$8"
  local after_file="$9"
  local attempts_file="${10}"
  local control_condition="${11:-}"
  mkdir -p "$(dirname "$result_path")"
  python3 - "$result_path" "$repo" "$packet" "$status" "$exit_code" "$prompt_file" "$log_file" "$before_file" "$after_file" "$attempts_file" "$control_condition" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

result_path, repo, packet_path, status, exit_code, prompt_file, log_file, before_file, after_file, attempts_file, control_condition = sys.argv[1:]
packet = json.load(open(packet_path, encoding="utf-8"))

def read_lines(path: str) -> list[str]:
    p = Path(path)
    if not p.exists():
        return []
    return [line.rstrip("\n") for line in p.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()]

before = read_lines(before_file)
after = read_lines(after_file)
attempts = []
attempts_path = Path(attempts_file)
if attempts_path.exists():
    for line in attempts_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        attempts.append(json.loads(line))
changed = after
result_status = "passed" if status == "done" else status
new_changes = sorted(set(after) - set(before))
orphan_work_detected = int(exit_code) != 0 and bool(new_changes) and control_condition != "pending_concurrent_work"
failed_categories = [
    item.get("failure_category")
    for item in attempts
    if item.get("exit_code") != 0 and item.get("failure_category")
]
failure_category = failed_categories[0] if failed_categories else ("none" if int(exit_code) == 0 else "child_agent_failed")
stop_conditions = [] if int(exit_code) == 0 else [failure_category]
local_final_without_verifier = bool(
    attempts
    and attempts[-1].get("agent") == "local"
    and int(attempts[-1].get("exit_code") or 0) == 0
)
if control_condition:
    result_status = "held" if control_condition == "pending_concurrent_work" else result_status
    failure_category = control_condition
    stop_conditions = [control_condition]
if local_final_without_verifier and int(exit_code) == 0:
    result_status = "held"
    failure_category = "local_llm_used_as_final_acceptor_without_verifier"
    stop_conditions = [failure_category]
if orphan_work_detected and "orphan_work_detected" not in stop_conditions:
    stop_conditions.append("orphan_work_detected")
row = {
    "schema_version": "aios.dispatch.result.v1",
    "executed_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    "target_repo": repo,
    "dispatch_id": packet.get("dispatch_id"),
    "contract_id": packet.get("contract_id"),
    "agent_assigned": packet.get("agent"),
    "agent_executed": "aios_child_watcher",
    "agent_attempts": attempts,
    "fallback_used": len(attempts) > 1,
    "final_agent": attempts[-1].get("agent") if attempts else packet.get("agent"),
    "failure_category": failure_category,
    "final_failure_category": attempts[-1].get("failure_category") if attempts else failure_category,
    "executed_reason": "child_repo_packet",
    "status": result_status,
    "exit_code": int(exit_code),
    "packet": str(Path(packet_path).as_posix()),
    "prompt_ref": str(Path(prompt_file).as_posix()),
    "log_ref": str(Path(log_file).as_posix()),
    "evidence": [
        {
            "kind": "child_agent_exit",
            "status": result_status,
            "exit_code": int(exit_code),
            "log_ref": str(Path(log_file).as_posix()),
        },
        {
            "kind": "git_status_delta",
            "before_count": len(before),
            "after_count": len(after),
        },
    ],
    "git_status_before_count": len(before),
    "git_status_after_count": len(after),
    "changed_files": changed[:200],
    "pending_concurrent_work": control_condition == "pending_concurrent_work",
    "local_final_without_verifier": local_final_without_verifier,
    "orphan_work_detected": orphan_work_detected,
    "orphan_work_files": new_changes[:200] if orphan_work_detected else [],
    "stop_conditions_triggered": stop_conditions,
    "privacy": {
        "raw_prompt_included": False,
        "stdout_included": False,
        "stderr_included": False,
        "full_log_included": False,
    },
    "next": "collect_from_myworld",
}
Path(result_path).write_text(json.dumps(row, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
}

write_memory_draft_review_result() {
  local result_path="$1"
  local repo="$2"
  local packet="$3"
  mkdir -p "$(dirname "$result_path")"
  python3 - "$result_path" "$repo" "$packet" "$ROOT" <<'PY'
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

result_path, repo, packet_path, root_path = sys.argv[1:]
root = Path(root_path)
result = Path(result_path)
packet_abs = Path(packet_path).resolve()
packet = json.load(open(packet_path, encoding="utf-8"))
draft = packet.get("draft") if isinstance(packet.get("draft"), dict) else {}
raw_refs = draft.get("raw_refs") if isinstance(draft.get("raw_refs"), list) else []
provenance = draft.get("provenance") if isinstance(draft.get("provenance"), dict) else {}
missing = []
if not packet.get("dispatch_id"):
    missing.append("dispatch_id_missing")
if not packet.get("source_artifact"):
    missing.append("source_artifact_missing")
if not packet.get("draft_id"):
    missing.append("draft_id_missing")
if not (raw_refs or provenance):
    missing.append("provenance_missing")

import_json_path = Path(f"{result_path}.memoryos-import.json")
log_path = Path(f"{result_path}.memoryos-import.log")
import_result = {}
import_rc = 1 if missing else 0
import_failure = ""
if not missing:
    repo_dir = root / "memoryOS"
    cmd = [
        sys.executable,
        "-m",
        "memoryos.cli",
        "--root",
        str(repo_dir),
        "drafts",
        "import-review-request",
        str(packet_abs),
        "--json",
    ]
    completed = subprocess.run(cmd, cwd=repo_dir, capture_output=True, text=True, check=False)
    import_rc = completed.returncode
    log_path.write_text((completed.stderr or "") + (completed.stdout if completed.returncode else ""), encoding="utf-8")
    if completed.returncode == 0:
        try:
            import_result = json.loads(completed.stdout)
            import_json_path.write_text(json.dumps(import_result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        except json.JSONDecodeError:
            import_rc = 1
            import_failure = "memoryos_import_invalid_json"
    else:
        import_failure = "memoryos_import_failed"

status = "passed" if not missing and import_rc == 0 else "held"
failure_category = (
    "none"
    if status == "passed"
    else "memory_draft_review_request_incomplete"
    if missing
    else import_failure or "memoryos_import_failed"
)
review_decision = import_result.get("review_action") or "needs_more_evidence"
imported_counts = import_result.get("imported_counts") if isinstance(import_result.get("imported_counts"), dict) else {}
memory_mutated = any(int(imported_counts.get(key, 0) or 0) > 0 for key in ("source_artifacts", "memory_objects", "hyperedges", "reviews"))
row = {
    "schema_version": "aios.dispatch.result.v1",
    "executed_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    "target_repo": repo,
    "dispatch_id": packet.get("dispatch_id") or packet.get("request_id"),
    "contract_id": packet.get("contract_id") or "MEMORY-DRAFT-REVIEW",
    "agent_assigned": packet.get("agent"),
    "agent_executed": "aios_child_watcher.memory_draft_review_adapter",
    "agent_attempts": [
        {
            "agent": "memoryOS-review-adapter",
            "exit_code": import_rc,
            "failure_category": failure_category,
            "status": "done" if status == "passed" else "held",
            "log_ref": "" if status == "passed" else log_path.as_posix(),
        }
    ],
    "fallback_used": False,
    "final_agent": "memoryOS-review-adapter",
    "failure_category": failure_category,
    "final_failure_category": failure_category,
    "executed_reason": "memory_draft_review_request",
    "status": status,
    "exit_code": import_rc,
    "packet": str(Path(packet_path).as_posix()),
    "prompt_ref": "",
    "log_ref": "" if status == "passed" else log_path.as_posix(),
    "evidence": [
        {
            "kind": "memory_draft_review_request",
            "status": status,
            "source_artifact": packet.get("source_artifact"),
            "draft_id": packet.get("draft_id"),
            "draft_type": draft.get("type"),
            "review_decision": review_decision,
            "auto_accept": bool((packet.get("review_policy") or {}).get("auto_accept")),
            "memory_object_id": import_result.get("memory_object_id"),
            "source_artifact_id": import_result.get("source_artifact_id"),
            "review_id": import_result.get("review_id"),
            "import_result_ref": import_json_path.as_posix() if import_result else "",
        }
    ],
    "review_request": {
        "schema_version": packet.get("schema_version"),
        "request_id": packet.get("request_id"),
        "source_artifact": packet.get("source_artifact"),
        "draft_id": packet.get("draft_id"),
        "draft_type": draft.get("type"),
        "origin": draft.get("origin"),
        "confidence": draft.get("confidence"),
        "review_decision": review_decision,
        "memory_mutated": memory_mutated,
        "memory_object_id": import_result.get("memory_object_id"),
        "source_artifact_id": import_result.get("source_artifact_id"),
        "review_id": import_result.get("review_id"),
        "import_result_ref": import_json_path.as_posix() if import_result else "",
        "next_owner": "memoryOS",
        "next_action": "operator_review_memory_draft",
    },
    "changed_files": [],
    "pending_concurrent_work": False,
    "local_final_without_verifier": False,
    "orphan_work_detected": False,
    "orphan_work_files": [],
    "stop_conditions_triggered": missing,
    "privacy": {
        "raw_prompt_included": False,
        "stdout_included": False,
        "stderr_included": False,
        "full_log_included": False,
    },
    "next": "collect_from_myworld",
}
result.write_text(json.dumps(row, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
}

failure_category() {
  local rc="$1"
  local log_file="$2"
  if [[ "$rc" -eq 0 ]]; then
    echo "none"
  elif [[ "$rc" -eq 124 ]]; then
    echo "timeout"
  elif grep -Eiq 'rate[ _-]?limit|hit your limit|usage limit|quota|too many requests|429|resets?[[:space:]]+[0-9]|provider[ _-]?backpressure|limit exceeded' "$log_file" 2>/dev/null; then
    echo "provider_backpressure"
  elif [[ "$rc" -eq 127 ]]; then
    echo "command_missing"
  elif grep -Eiq 'pin[ _-]?(required|denied|failed|invalid|wrong)|invalid[ _-]?pin|wrong[ _-]?pin|틀렸습니다' "$log_file" 2>/dev/null; then
    echo "pin_required_noninteractive"
  elif grep -Eiq 'access[ _-]?denied|permission[ _-]?denied|unauthorized|authentication|auth[ _-]?required|auth[ _-]?method|set an auth method|missing.*(api[ _-]?)?key|invalid[ _-]?(api[ _-]?)?key|gemini_api_key|google_genai|invalid[ _-]?pin|wrong[ _-]?pin|provider.*denied|접근[[:space:]]*거부|권한[[:space:]]*없|인증[[:space:]]*(필요|실패)|틀렸습니다' "$log_file" 2>/dev/null; then
    echo "provider_access_denied"
  else
    echo "child_agent_failed"
  fi
}

fallback_order_for() {
  case "$1" in
    codex) echo "claude gemini local" ;;
    claude) echo "codex gemini local" ;;
    gemini) echo "claude codex local" ;;
    local) echo "codex claude gemini" ;;
    *) echo "codex claude gemini local" ;;
  esac
}

agent_was_tried() {
  local candidate="$1"
  local tried_agents="$2"
  [[ " $tried_agents " == *" $candidate "* ]]
}

first_untried_default_fallback() {
  local assigned_agent="$1"
  local tried_agents="$2"
  local candidate
  for candidate in $(fallback_order_for "$assigned_agent") codex claude gemini local; do
    if ! agent_was_tried "$candidate" "$tried_agents"; then
      echo "$candidate"
      return 0
    fi
  done
  echo ""
}

provider_command_available() {
  local agent="$1"
  case "$agent" in
    codex|claude|gemini) command -v "$agent" >/dev/null 2>&1 ;;
    local) [[ -n "${AIOS_LOCAL_AGENT_COMMAND:-}" || -d "$ROOT/hivemind" ]] ;;
    *) return 1 ;;
  esac
}

capability_route_fallback_agent() {
  local assigned_agent="$1"
  local repo="$2"
  local category="$3"
  local route_file="$4"
  local tried_agents="${5:-}"
  local capabilityos_dir="$ROOT/CapabilityOS"
  if [[ ! -f "$capabilityos_dir/capabilityos/cli.py" ]]; then
    first_untried_default_fallback "$assigned_agent" "$tried_agents"
    return 0
  fi
  if (
    cd "$capabilityos_dir" && \
      python3 -m capabilityos.cli provider-route \
        --task "child watcher provider fallback for ${repo} after ${category}" \
        --assigned-agent "$assigned_agent" \
        --observations-inbox "$OUTBOX_DIR" \
        --json
  ) >"$route_file" 2>"$route_file.stderr"; then
    local routed
    routed="$(python3 - "$route_file" "$assigned_agent" "$tried_agents" <<'PY'
import json
import sys

path, assigned, tried_raw = sys.argv[1:]
tried = {item for item in tried_raw.split() if item}
try:
    data = json.load(open(path, encoding="utf-8"))
except (OSError, json.JSONDecodeError):
    print("")
    raise SystemExit(0)
if data.get("contract") != "capabilityos.provider_route.v1":
    print("")
    raise SystemExit(0)
for agent in data.get("fallback_agents") or []:
    agent = str(agent)
    if agent in {"codex", "claude", "gemini", "local"} and agent != assigned and agent not in tried:
        print(agent)
        break
PY
)"
    if [[ -n "$routed" ]]; then
      if [[ "$routed" == "local" && "$AIOS_CHILD_PREFER_PROVIDER_BEFORE_LOCAL" == "1" ]]; then
        local default_candidate
        default_candidate="$(first_untried_default_fallback "$assigned_agent" "$tried_agents")"
        if [[ -n "$default_candidate" && "$default_candidate" != "local" ]] && provider_command_available "$default_candidate"; then
          echo "$default_candidate"
          return 0
        fi
      fi
      echo "$routed"
      return 0
    fi
  fi
  first_untried_default_fallback "$assigned_agent" "$tried_agents"
}

run_agent_once() {
  local agent="$1"
  local repo_dir="$2"
  local prompt_file="$3"
  local log_file="$4"
  local rc=0
  if [[ "$agent" == "codex" ]]; then
    if ! command -v codex >/dev/null 2>&1; then
      echo "codex command not found" > "$log_file"
      rc=127
    else
      (cd "$repo_dir" && timeout "$CODEX_TIMEOUT" codex exec --dangerously-bypass-approvals-and-sandbox "$(cat "$prompt_file")") \
        >"$log_file" 2>&1 || rc=$?
    fi
  elif [[ "$agent" == "claude" ]]; then
    if ! command -v claude >/dev/null 2>&1; then
      echo "claude command not found" > "$log_file"
      rc=127
    else
      (cd "$repo_dir" && timeout "$CLAUDE_TIMEOUT" claude --dangerously-skip-permissions --model "$CLAUDE_MODEL" -p "$(cat "$prompt_file")") \
        >"$log_file" 2>&1 || rc=$?
    fi
  elif [[ "$agent" == "gemini" ]]; then
    if ! command -v gemini >/dev/null 2>&1; then
      echo "gemini command not found" > "$log_file"
      rc=127
    else
      (cd "$repo_dir" && timeout "$GEMINI_TIMEOUT" gemini --approval-mode plan -p "$(cat "$prompt_file")") \
        >"$log_file" 2>&1 || rc=$?
    fi
  elif [[ "$agent" == "local" ]]; then
    if [[ -n "${AIOS_LOCAL_AGENT_COMMAND:-}" ]]; then
      (cd "$repo_dir" && timeout "$LOCAL_TIMEOUT" bash -lc "$AIOS_LOCAL_AGENT_COMMAND" < "$prompt_file") \
        >"$log_file" 2>&1 || rc=$?
    elif [[ -d "$ROOT/hivemind" ]]; then
      (
        cd "$ROOT/hivemind"
        python3 -m hivemind.hive --root "$ROOT/hivemind" provider-loop prepare --provider local --prompt "$(cat "$prompt_file")" --json
        python3 -m hivemind.hive --root "$ROOT/hivemind" provider-loop tick --json
      ) >"$log_file" 2>&1 || rc=$?
    else
      echo "local provider requires AIOS_LOCAL_AGENT_COMMAND or hivemind provider-loop" > "$log_file"
      rc=127
    fi
  else
    echo "unsupported packet agent: $agent" > "$log_file"
    rc=2
  fi
  return "$rc"
}

append_attempt() {
  local attempts_file="$1"
  local agent="$2"
  local rc="$3"
  local category="$4"
  local log_file="$5"
  python3 - "$attempts_file" "$agent" "$rc" "$category" "$log_file" <<'PY'
import json
import sys

attempts_file, agent, rc, category, log_file = sys.argv[1:]
row = {
    "agent": agent,
    "exit_code": int(rc),
    "status": "done" if int(rc) == 0 else "failed",
    "failure_category": category,
    "log_ref": log_file,
}
with open(attempts_file, "a", encoding="utf-8") as fh:
    fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
PY
}

run_packet() {
  local repo="$1"
  local packet="$2"
  local result_path
  result_path="$(packet_result_path "$packet" "$repo")"
  if [[ -f "$result_path" ]]; then
    return 0
  fi

  local schema_version
  schema_version="$(json_get "$packet" "schema_version")"
  if [[ "$schema_version" == "aios.memory_draft_review_request.v1" ]]; then
    write_memory_draft_review_result "$result_path" "$repo" "$packet"
    append_event "packet_done" "$repo" "passed" "$result_path"
    return 0
  fi

  local repo_dir
  repo_dir="$(repo_path "$repo")"
  if [[ ! -d "$repo_dir" ]]; then
    echo "repo directory not found: $repo_dir" >&2
    return 2
  fi

  local dispatch_id agent safe_id prompt_file log_file before_file after_file lock_file attempts_file
  dispatch_id="$(json_get "$packet" "dispatch_id")"
  agent="$(json_get "$packet" "agent")"
  safe_id="${dispatch_id}.${repo}"
  prompt_file="$PROMPT_DIR/${safe_id}.child.prompt.md"
  log_file="$LOG_DIR/${safe_id}.child.log"
  before_file="$LOG_DIR/${safe_id}.git.before"
  after_file="$LOG_DIR/${safe_id}.git.after"
  lock_file="$RUN_DIR/${safe_id}.running"
  attempts_file="$LOG_DIR/${safe_id}.attempts.jsonl"

  if [[ -f "$lock_file" ]]; then
    return 0
  fi
  touch "$lock_file"

  build_prompt "$repo" "$packet" "$prompt_file"
  git_status_short "$repo_dir" > "$before_file"
  append_event "packet_start" "$repo" "running" "$packet"
  rm -f "$attempts_file"

  local related_before
  related_before="$(related_dirty_status "$repo" "$before_file" "$packet")"
  if [[ -n "$related_before" ]]; then
    cp "$before_file" "$after_file"
    append_event "pending_concurrent_work" "$repo" "held" "$related_before"
    write_result "$result_path" "$repo" "$packet" "held" "1" "$prompt_file" "$LOG_DIR/${safe_id}.child.log" "$before_file" "$after_file" "$attempts_file" "pending_concurrent_work"
    append_event "packet_done" "$repo" "held" "$result_path"
    rm -f "$lock_file"
    return 0
  fi

  local rc=0 category fallback_agent fallback_log_file route_file current_agent tried_agents attempt_index
  run_agent_once "$agent" "$repo_dir" "$prompt_file" "$log_file" || rc=$?
  category="$(failure_category "$rc" "$log_file")"
  append_attempt "$attempts_file" "$agent" "$rc" "$category" "$log_file"
  current_agent="$agent"
  tried_agents="$agent"
  attempt_index=0

  while [[ "$rc" -ne 0 && "$AIOS_CHILD_AGENT_FALLBACKS" == "1" && ( "$category" == "provider_access_denied" || "$category" == "provider_backpressure" || "$category" == "pin_required_noninteractive" ) ]]; do
    attempt_index=$((attempt_index + 1))
    route_file="$LOG_DIR/${safe_id}.fallback-${attempt_index}.provider_route.json"
    fallback_agent="$(capability_route_fallback_agent "$current_agent" "$repo" "$category" "$route_file" "$tried_agents")"
    if [[ -z "$fallback_agent" ]] || agent_was_tried "$fallback_agent" "$tried_agents"; then
      break
    fi
    fallback_log_file="$LOG_DIR/${safe_id}.${fallback_agent}.fallback.child.log"
    append_event "packet_fallback_start" "$repo" "$category" "$fallback_agent"
    rc=0
    run_agent_once "$fallback_agent" "$repo_dir" "$prompt_file" "$fallback_log_file" || rc=$?
    category="$(failure_category "$rc" "$fallback_log_file")"
    append_attempt "$attempts_file" "$fallback_agent" "$rc" "$category" "$fallback_log_file"
    log_file="$fallback_log_file"
    current_agent="$fallback_agent"
    tried_agents="$tried_agents $fallback_agent"
  done

  git_status_short "$repo_dir" > "$after_file"
  local status
  if [[ "$rc" -eq 0 ]]; then
    status="done"
  elif [[ "$rc" -eq 124 ]]; then
    status="timeout"
  else
    status="failed"
  fi
  write_result "$result_path" "$repo" "$packet" "$status" "$rc" "$prompt_file" "$log_file" "$before_file" "$after_file" "$attempts_file"
  append_event "packet_done" "$repo" "$status" "$result_path"
  rm -f "$lock_file"
  return 0
}

run_once() {
  local repo="$1"
  validate_repo "$repo"
  mkdir -p "$INBOX_DIR/$repo" "$OUTBOX_DIR/$repo"
  local packet
  packet="$(find "$INBOX_DIR/$repo" -maxdepth 1 -type f -name '*.json' | sort | while read -r candidate; do
    result="$(packet_result_path "$candidate" "$repo")"
    if [[ ! -f "$result" ]]; then
      echo "$candidate"
      break
    fi
  done)"
  if [[ -z "$packet" ]]; then
    echo "no pending packet for $repo"
    return 0
  fi
  echo "running packet for $repo: $packet"
  run_packet "$repo" "$packet"
}

run_loop() {
  local repo="$1"
  validate_repo "$repo"
  append_event "watcher_start" "$repo" "running" ""
  while [[ ! -f "$STOP_FILE" ]]; do
    run_once "$repo" || true
    sleep "$WATCH_INTERVAL"
  done
  append_event "watcher_stop" "$repo" "stopped" "$STOP_FILE"
}

pid_file_for() {
  echo "$RUN_DIR/child-watcher-$1.pid"
}

start_repo() {
  local repo="$1"
  validate_repo "$repo"
  local pid_file
  pid_file="$(pid_file_for "$repo")"
  if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
    echo "$repo watcher already running: pid $(cat "$pid_file")"
    return 0
  fi
  nohup "$0" run --repo "$repo" > "$LOG_DIR/child-watcher-$repo.supervisor.log" 2>&1 &
  echo "$!" > "$pid_file"
  echo "started $repo watcher pid $(cat "$pid_file")"
}

stop_repo() {
  local repo="$1"
  validate_repo "$repo"
  local pid_file
  pid_file="$(pid_file_for "$repo")"
  if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
    kill "$(cat "$pid_file")" || true
    echo "stopped $repo watcher pid $(cat "$pid_file")"
  else
    echo "$repo watcher not running"
  fi
}

status_all() {
  for repo in hivemind memoryOS CapabilityOS GenesisOS; do
    local pid_file running inbox_count outbox_count pending_count
    mkdir -p "$INBOX_DIR/$repo" "$OUTBOX_DIR/$repo"
    pid_file="$(pid_file_for "$repo")"
    if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
      running="true pid=$(cat "$pid_file")"
    else
      running="false"
    fi
    inbox_count="$(find "$INBOX_DIR/$repo" -maxdepth 1 -type f -name '*.json' 2>/dev/null | wc -l | tr -d ' ')"
    outbox_count="$(find "$OUTBOX_DIR/$repo" -maxdepth 1 -type f -name '*.json' 2>/dev/null | wc -l | tr -d ' ')"
    pending_count="$(
      find "$INBOX_DIR/$repo" -maxdepth 1 -type f -name '*.json' 2>/dev/null | while read -r candidate; do
        result="$(packet_result_path "$candidate" "$repo")"
        [[ -f "$result" ]] || echo "$candidate"
      done | wc -l | tr -d ' '
    )"
    echo "$repo running=$running inbox=$inbox_count outbox=$outbox_count pending=$pending_count"
  done
}

repo_arg=""
command="${1:-}"
shift || true
while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      repo_arg="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

case "$command" in
  once)
    [[ -n "$repo_arg" ]] || { echo "--repo required" >&2; exit 2; }
    run_once "$repo_arg"
    ;;
  run)
    [[ -n "$repo_arg" ]] || { echo "--repo required" >&2; exit 2; }
    run_loop "$repo_arg"
    ;;
  start)
    [[ -n "$repo_arg" ]] || { echo "--repo required" >&2; exit 2; }
    if [[ "$repo_arg" == "all" ]]; then
      start_repo hivemind
      start_repo memoryOS
      start_repo CapabilityOS
      start_repo GenesisOS
    else
      start_repo "$repo_arg"
    fi
    ;;
  stop)
    [[ -n "$repo_arg" ]] || { echo "--repo required" >&2; exit 2; }
    if [[ "$repo_arg" == "all" ]]; then
      stop_repo hivemind
      stop_repo memoryOS
      stop_repo CapabilityOS
      stop_repo GenesisOS
    else
      stop_repo "$repo_arg"
    fi
    ;;
  status)
    status_all
    ;;
  -h|--help|help|"")
    usage
    ;;
  *)
    echo "unknown command: $command" >&2
    usage >&2
    exit 2
    ;;
esac

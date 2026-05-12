#!/usr/bin/env bash
# AIOS self-check pulse: detects conditions that need operator attention
# and emits them as monitor events. Runs ONE pass per invocation; loop
# wrapping is the monitor command around it.
#
# Conditions watched:
#   1. proposed contracts aging without GO       → "PROPOSED_AGING"
#   2. dialogue docs with pending TURN           → "DIALOGUE_STUCK"
#   3. memory drafts stuck > 4h                  → "DRAFTS_BACKLOG"
#   4. co-evolution pulses dead                  → "PULSE_DEAD"
#   5. failed-result count vs passing delta      → "FAILURE_REAL"
#   6. uri goal_inbox unprocessed                → "GOAL_INBOX_BACKLOG"
#   7. round controller daemon dead              → "DAEMON_DEAD"

set -uo pipefail
ROOT="${AIOS_ROOT:-/home/user/workspaces/jaewon/myworld}"
cd "$ROOT" || { echo "self_check error=cd_failed"; exit 1; }

now_epoch=$(date +%s)
attention_count=0

# 1. proposed contracts aging
proposed_files=$(grep -lE '^status: proposed$' docs/contracts/ASC-*.md 2>/dev/null)
proposed_aging=0
proposed_oldest_minutes=0
for f in $proposed_files; do
  mtime=$(stat -c %Y "$f")
  age=$(( (now_epoch - mtime) / 60 ))
  if [ "$age" -gt 30 ]; then
    proposed_aging=$((proposed_aging + 1))
    if [ "$age" -gt "$proposed_oldest_minutes" ]; then
      proposed_oldest_minutes=$age
    fi
  fi
done
if [ "$proposed_aging" -gt 0 ]; then
  attention_count=$((attention_count+1))
  echo "self_check PROPOSED_AGING count=$proposed_aging oldest_minutes=$proposed_oldest_minutes"
fi

# 2. dialogue docs with pending TURN
dialogue_pending=0
for f in docs/discoveries/*-dialogue.md; do
  [ -f "$f" ] || continue
  if grep -q "PENDING\|placeholder\|pending TURN\|pending\)$" "$f" 2>/dev/null; then
    mtime=$(stat -c %Y "$f")
    age_h=$(( (now_epoch - mtime) / 3600 ))
    if [ "$age_h" -gt 1 ]; then
      dialogue_pending=$((dialogue_pending+1))
    fi
  fi
done
if [ "$dialogue_pending" -gt 0 ]; then
  attention_count=$((attention_count+1))
  echo "self_check DIALOGUE_STUCK count=$dialogue_pending"
fi

# 3. memory drafts stuck > 4h
draft_count=$(cd memoryOS && python -m memoryos --root . drafts list --json 2>/dev/null | python -c "
import json, sys, datetime
try:
    drafts = json.load(sys.stdin)
    now = datetime.datetime.now(datetime.timezone.utc)
    stuck = 0
    for d in drafts:
        ts = d.get('captured_at', '')
        if not ts: continue
        try:
            dt = datetime.datetime.fromisoformat(ts.replace('Z','+00:00'))
            if dt.tzinfo is None: dt = dt.replace(tzinfo=datetime.timezone.utc)
            hours = (now - dt).total_seconds() / 3600
            if hours > 4: stuck += 1
        except: pass
    print(stuck)
except: print(0)
" 2>/dev/null)
cd "$ROOT"
if [ "${draft_count:-0}" -gt 5 ]; then
  attention_count=$((attention_count+1))
  echo "self_check DRAFTS_BACKLOG count=$draft_count"
fi

# 4. co-evolution pulses dead
dead_pulses=$(python scripts/aios_primitives.py monitor list --json 2>/dev/null | python -c "
import json, sys
try:
    d = json.load(sys.stdin)
    dead = sum(1 for m in d if m.get('name','').startswith('aios-') and 'pulse' in m['name'] and not m.get('alive'))
    print(dead)
except: print(0)
")
if [ "${dead_pulses:-0}" -gt 0 ]; then
  attention_count=$((attention_count+1))
  echo "self_check PULSE_DEAD count=$dead_pulses"
fi

# 5. failed-result count
failed_total=$(grep -lE '"status":\s*"failed"' .aios/outbox/*/*.json 2>/dev/null | wc -l)
failed_recovered=$(grep -lE '"fallback_used":\s*true' .aios/outbox/*/*.json 2>/dev/null | wc -l)
real_failures=$((failed_total - failed_recovered))
if [ "$real_failures" -gt 2 ]; then
  attention_count=$((attention_count+1))
  echo "self_check FAILURE_REAL count=$real_failures total=$failed_total recovered=$failed_recovered"
fi

# 6. goal_inbox unprocessed
goal_inbox_count=$(find .aios/goal_inbox -name "*.json" -type f 2>/dev/null | wc -l)
if [ "$goal_inbox_count" -gt 0 ]; then
  # only attention if there's no recent processor receipt
  last_processor=$(ls -t .aios/primitives/goal_inbox_run/*.json 2>/dev/null | head -1)
  if [ -z "$last_processor" ]; then
    attention_count=$((attention_count+1))
    echo "self_check GOAL_INBOX_BACKLOG count=$goal_inbox_count processor=never"
  fi
fi

# 7. round controller daemon
controller_status=$(python scripts/aios_round_controller.py status 2>&1 | grep "running" | head -1)
if ! echo "$controller_status" | grep -q "running=true"; then
  attention_count=$((attention_count+1))
  echo "self_check DAEMON_DEAD status=$controller_status"
fi

# Summary line (always, so monitor knows pulse fired)
echo "self_check pass complete attention=$attention_count"

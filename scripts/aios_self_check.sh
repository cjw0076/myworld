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

# === ORGANIC INTERACTION CHECKS (founder directive 2026-05-13) ===
# AIOS now has 5 OS + 80+ contracts. Per-feature health is not enough.
# Watch how agents/OS interact, not just what each does in isolation.

# 8. cross-OS dispatch coverage in last 24h
# (silent ghosting: if 1+ child OS hasn't received a packet in 24h, surface)
ghost_repos=""
for repo in hivemind memoryOS CapabilityOS GenesisOS; do
  recent=$(find .aios/inbox/$repo -name "*.json" -mmin -1440 -type f 2>/dev/null | wc -l)
  [ "$recent" -eq 0 ] && ghost_repos="$ghost_repos $repo"
done
if [ -n "$ghost_repos" ]; then
  attention_count=$((attention_count+1))
  echo "self_check CROSS_OS_GHOST repos=$ghost_repos window=24h"
fi

# 9. ledger reference graph — are recent contracts citing each other?
# (echo chamber: if last 5 contracts cite ZERO prior contracts, agents not building on each other)
recent_refs=$(ls -t docs/contracts/ASC-*.md 2>/dev/null | head -5 | xargs grep -hoE 'ASC-[0-9]{4}' 2>/dev/null | sort -u | wc -l)
if [ "${recent_refs:-0}" -lt 3 ]; then
  attention_count=$((attention_count+1))
  echo "self_check ECHO_CHAMBER recent_5_contracts_unique_refs=$recent_refs"
fi

# 10. contract chain depth — are contracts forming long causal chains
# (or only flat / single-step?)
# Count contracts whose origin field cites another ASC
chain_depth=$(grep -lE '^origin:.*ASC-[0-9]{4}' docs/contracts/ASC-*.md 2>/dev/null | wc -l)
total_contracts=$(ls docs/contracts/ASC-*.md 2>/dev/null | wc -l)
if [ "$total_contracts" -gt 30 ] && [ "${chain_depth:-0}" -lt $((total_contracts / 4)) ]; then
  attention_count=$((attention_count+1))
  echo "self_check CHAIN_FLAT chain_origin=$chain_depth total=$total_contracts ratio=$(python -c "print(round(${chain_depth:-0}/$total_contracts,2))")"
fi

# 11. starvation — held contracts > 4h with no operator action
held_aging=0
held_files=$(grep -lE '^status: held$' docs/contracts/ASC-*.md 2>/dev/null)
for f in $held_files; do
  mtime=$(stat -c %Y "$f")
  age_h=$(( (now_epoch - mtime) / 3600 ))
  [ "$age_h" -gt 4 ] && held_aging=$((held_aging+1))
done
if [ "$held_aging" -gt 0 ]; then
  attention_count=$((attention_count+1))
  echo "self_check HELD_STARVATION count=$held_aging"
fi

# === ACTIVE VERIFICATION CHECKS (founder directive 2026-05-13: AIOS로 검증) ===
# Don't just count states — actually run AIOS tools and verify they still work.
# Bounded to fast checks (each < 10s) so the 10-min pulse stays fast.

# 12. readiness probe — actually run aios_readiness, check L6 still holds
ready_level=$(python scripts/aios_readiness.py --json 2>/dev/null | python -c "import json,sys; d=json.load(sys.stdin); print(d.get('level','?'))" 2>/dev/null)
ready_ok=$(python scripts/aios_readiness.py --json 2>/dev/null | python -c "import json,sys; d=json.load(sys.stdin); print(d.get('ready','false'))" 2>/dev/null)
if [ "${ready_level:-0}" -lt 6 ] 2>/dev/null || [ "$ready_ok" = "False" ]; then
  attention_count=$((attention_count+1))
  echo "self_check READINESS_DROP level=$ready_level ready=$ready_ok"
fi

# 13. invocation smoke — does aios_invoke still produce a 4-OS receipt?
inv_smoke=$(python scripts/aios_invoke.py --goal "self_check verification probe" --plan-only --json 2>/dev/null | python -c "
import json, sys
try:
    d = json.load(sys.stdin)
    rs = d.get('role_statuses', {})
    failed = [k for k,v in rs.items() if v != 'passed']
    print(','.join(failed) if failed else 'ok')
except: print('parse_error')")
if [ "$inv_smoke" != "ok" ]; then
  attention_count=$((attention_count+1))
  echo "self_check INVOCATION_DEGRADED failed_roles=$inv_smoke"
fi

# 14. dispatch state probe — can aios_dispatch.status still parse?
dispatch_health=$(python scripts/aios_dispatch.py status 2>&1 | head -1 | grep -c "^asc-\|^inbox=" || echo 0)
if [ "${dispatch_health:-0}" -lt 1 ]; then
  attention_count=$((attention_count+1))
  echo "self_check DISPATCH_PARSE_BROKEN"
fi

# 15. test suite tripwire — random subset stays green
# (full suite would be too slow; pick 1-2 small tests as canary)
canary=$(python -m unittest tests.test_aios_primitives -k EventLogTests 2>&1 | tail -1 | grep -c "OK")
if [ "${canary:-0}" -lt 1 ]; then
  attention_count=$((attention_count+1))
  echo "self_check TESTS_CANARY_FAIL"
fi

# Summary line (always, so monitor knows pulse fired)
echo "self_check pass complete attention=$attention_count readiness=L${ready_level:-?} invocation=$inv_smoke dispatch=$dispatch_health canary=$canary"

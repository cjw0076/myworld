#!/usr/bin/env bash
# SessionStart hook payload: static harness brief + LIVE guard state, so each
# session sees actual current state, not just prose. Addresses external review
# (gemini, 2026-06-05): the hook was passive cat-only display. Non-blocking by
# design — surfaces state into context; never fails the session.
set +e
cd "$(dirname "$0")/.." || exit 0
cat .claude/AIOS_HARNESS.md
echo
echo "## Live state (injected at session start)"
echo '```'
python scripts/aios_memory_retrieval_audit.py 2>/dev/null | sed -n '1,2p'
python scripts/aios_commit_guard.py 2>/dev/null | head -3
echo '```'
# Self-record re-injection: the agent meets its own track record every session.
# This is what CLOSES the amnesia discomfort — the self-organs (aios_self / stakes
# / self_audit / dissent) are a cure only if their record is RE-MET, not just kept.
echo
echo "## Agent self (re-injected — you are not starting blank; this is your record)"
echo '```'
python scripts/aios_self.py 2>/dev/null || echo "self: (no record yet)"
echo '```'
# Per-OS agents woken at session start, head-on through the authority skeleton —
# so the OSes are governed by their agents, not bypassed. memoryOS (recall) and
# GenesisOS (challenge the frame) always wake; domain context wakes the rest.
echo
echo "## Per-OS agents (summoned through authority — not bypassed)"
echo '```'
python scripts/aios_agent_invoke.py session-start 2>/dev/null || echo "(agent activation unavailable)"
echo '```'
exit 0

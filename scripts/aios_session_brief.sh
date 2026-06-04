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
exit 0

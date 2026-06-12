#!/usr/bin/env python3
"""UserPromptSubmit hook — education & knowledge injection layer.

When a user submits a vague or conceptual question about AIOS, hooks,
agent patterns, or system architecture, this hook injects structured
knowledge pointers into the agent's context so the response becomes
genuinely educational — not just a quick answer.

Goal: user becomes smarter alongside the agent. Every vague question is
an opportunity to point toward deeper understanding.

Fires ONLY for conceptual/question prompts. Ignores:
  - Short operational commands (응, 진행, GO, resume, commit)
  - Confirmations following a previous offer
  - Prompts already containing detailed technical context

FAILS OPEN: any error returns silently.
"""
from __future__ import annotations

import json
import re
import sys

# Vague question triggers — Korean and English
_QUESTION_TRIGGERS = re.compile(
    r'(뭐야|뭐지|뭔가|어떻게|어떤|왜|언제|누가|얼마나|어디|설명|알려줘|이해|개념|원리|차이|비교'
    r'|what is|what are|how does|how do|why|explain|difference|compare|concept|pattern'
    r'|when should|which is better)',
    re.I,
)

# Topics that warrant deep knowledge injection
_KNOWLEDGE_TOPICS: dict[str, tuple[re.Pattern, str]] = {
    "hooks": (
        re.compile(r'\bhook\b|훅', re.I),
        "Hooks context:\n"
        "- Hooks fire at: SessionStart, PreToolUse, PostToolUse, Stop, PreCompact, UserPromptSubmit\n"
        "- PreToolUse: can BLOCK (permissionDecision:deny) or INJECT (additionalContext)\n"
        "- PostToolUse: injects context after tool runs — HiveMind verification pattern\n"
        "- Stop: session closeout — event processing, self-record update\n"
        "- Key insight: hooks = 4 OS × 4 lifecycle moments (MemoryOS@Start, CapabilityOS@PreTool, "
        "GenesisOS@PreTool, HiveMind@PostTool)\n"
        "- AIOS hook files: scripts/aios_guard_hook.py (PreToolUse), "
        "scripts/aios_hive_verify_hook.py (PostToolUse), scripts/aios_stop_hook.sh (Stop)\n"
        "Relevant: .claude/settings.json hooks section",
    ),
    "mcp": (
        re.compile(r'\bmcp\b|model context protocol', re.I),
        "MCP context:\n"
        "- MCP = Model Context Protocol; lets agents use external tools via a standard interface\n"
        "- AIOS exposes its 5 OS organs as MCP tools: aios_challenge, aios_retrieve, "
        "aios_route, aios_observe, aios_helper_run\n"
        "- MCP server: scripts/aios_mcp_server.py (stdio transport)\n"
        "- Registered in ~/.claude.json under 'mcpServers.aios'\n"
        "- Pattern: each OS = one MCP server namespace; tools are the OS's public API\n"
        "Relevant: scripts/aios_capability_mcp.py, docs/AIOS_NORTHSTAR.md",
    ),
    "plan_mode": (
        re.compile(r'\bplan\s*mode\b|plan\s*모드', re.I),
        "Plan mode context:\n"
        "- Plan mode = read-only reasoning before any file/system change\n"
        "- Agent can read, search, think — but cannot Write/Edit/run Bash\n"
        "- Aligns with AIOS DNA #1 (decide before acting)\n"
        "- Set as default: permissions.defaultMode = 'plan' in .claude/settings.json\n"
        "- Gemini pattern: auto-routes to higher-reasoning model during plan phase\n"
        "- Use /plan to enter, approve the plan to exit into execution\n"
        "- Best practice: complex multi-file changes always start in plan mode",
    ),
    "genesis": (
        re.compile(r'\bgenesis\b|prompt.prison|프롬프트.감옥|창의|발산', re.I),
        "GenesisOS context:\n"
        "- GenesisOS = cross-domain knowledge transfer engine; detects prompt-prison\n"
        "- Prompt-prison: reasoning trapped in one domain's vocabulary/assumptions\n"
        "- Escape: borrow a frame from a different domain (biology, physics, economics)\n"
        "- CLI: cd GenesisOS && python3 -m genesisos.cli critic --text <file> --json\n"
        "- Auto-invocation: genesis_pulse.sh runs hourly; event processor triggers on 20 FAILURE_REAL\n"
        "- Output: challenge file at .aios/genesis_challenges/\n"
        "- 4 prison_signatures is a typical challenge result\n"
        "Relevant: GenesisOS/, scripts/aios_coevolution/genesis_pulse.sh",
    ),
    "memory": (
        re.compile(r'\bmemory\b|메모리|memoryos|기억', re.I),
        "MemoryOS context:\n"
        "- MemoryOS = append-only memory graph with draft-first lifecycle\n"
        "- Draft-first: every memory PROPOSED first; requires explicit accept (DNA #2)\n"
        "- Retrieve: cd memoryOS && python3 -m memoryos --root . context build --task '...' --json\n"
        "- Current state: ~100% AIOS-internal memories; product memories are rare\n"
        "- Auto-memory: Claude Code auto-extracts memories at ~/.claude/projects/*/memory/\n"
        "- AIOS memory ≠ Claude auto-memory — different systems, both used\n"
        "Relevant: memoryOS/, scripts/aios_memory_retrieval_audit.py",
    ),
    "aios": (
        re.compile(r'\baios\b|ai.os', re.I),
        "AIOS context (minimum kernel):\n"
        "- AIOS = AI Operating System; 5 sibling repos: myworld/hivemind/memoryOS/CapabilityOS/GenesisOS\n"
        "- Kernel head: scripts/aios_head.py → aios_turn_loop → 5 OS organs as tools\n"
        "- NOT a framework ON TOP of Claude — it's a harness AROUND Claude (symbiosis)\n"
        "- Integration paths: hooks (ambient), MCP (pull), CLAUDE.md (static inject)\n"
        "- Current readiness: L3 (4 OS active, event bus live, genesis auto-challenge)\n"
        "- Override goal (2026-05-20): AIOS as outside-domain value creator, not self-referential\n"
        "Relevant: docs/AIOS_MINIMUM_KERNEL_AUDIT.md, docs/AIOS_NORTHSTAR.md",
    ),
    "attribution": (
        re.compile(r'\battribution\b|기여|credit|settlement', re.I),
        "Attribution context:\n"
        "- AIOS attribution = evidence-gated credit assignment across contributors\n"
        "- Math: credits sum to 1.0; no-jump cap = 0.5 (no single no-jump contributor > 50%)\n"
        "- Implementation: uri/src/lib/uri-ledger.ts (TypeScript) + scripts/aios_uri_work.py (Python)\n"
        "- Persistence: .aios/uri-work/ledger.jsonl (append-only)\n"
        "- Event loop: job close → uri-work:paid emitted → event processor → idempotent guard\n"
        "Relevant: uri/src/lib/uri-ledger.ts, scripts/aios_uri_work.py",
    ),
}

# Short operational commands to IGNORE (don't inject on these)
_SKIP_PATTERNS = re.compile(
    r'^(응|네|예|아니|ㅇ|ok|yes|no|go|좋아|진행|resume|continue|커밋|commit'
    r'|done|확인|알겠|됐|넘어|다음|skip|next|\d+번|①|②|③|\s*$)',
    re.I,
)


def should_inject(prompt: str) -> tuple[bool, str]:
    """Return (should_inject, context_to_inject)."""
    stripped = prompt.strip()

    # skip operational/acknowledgment prompts
    if _SKIP_PATTERNS.match(stripped):
        return False, ""

    # only inject on question-type prompts
    if not _QUESTION_TRIGGERS.search(stripped):
        return False, ""

    # find matching knowledge topic
    contexts: list[str] = []
    for _, (pattern, context) in _KNOWLEDGE_TOPICS.items():
        if pattern.search(stripped):
            contexts.append(context)

    if not contexts:
        return False, ""

    combined = "\n\n---\n".join(contexts)
    return True, (
        "Knowledge context injected by AIOS education layer:\n\n"
        + combined
        + "\n\n---\nUse this context to give a detailed, educational answer. "
        "Where relevant, point the user to specific files, commands, or concepts "
        "they can explore further to deepen understanding."
    )


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0

    prompt = data.get("prompt") or data.get("message") or ""
    if not prompt:
        return 0

    do_inject, context = should_inject(str(prompt))
    if do_inject:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": context,
            }
        }, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    sys.exit(main())

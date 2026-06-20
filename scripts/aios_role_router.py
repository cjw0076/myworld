#!/usr/bin/env python3
"""AIOS Role Router — absorbed from oh-my-codex/dist/team/role-router.js

Routes a task description to the best AIOS agent role / provider, mirroring
OMX's heuristic role routing (Layer 2) but mapped to AIOS's actual role names
and provider vocabulary (claude, codex, ollama).

Two layers (same as OMX):
  Layer 1: keyword/regex intent inference (inferLaneIntent equivalent)
  Layer 2: role → provider mapping for AIOS dispatch

Schema: aios.role_router.v1
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# ── Intent regexes (direct port from OMX role-router.js) ──────────────────

_IMPLEMENTATION_INTENT = re.compile(
    r"\b(?:add|build|create|fix|implement|make|migrate|repair|ship|support|update|wire)\b"
    r"|(?:구현|추가|수정|업데이트|지원)",
    re.I,
)
_REVIEW_INTENT = re.compile(
    r"\b(?:audit|check|inspect|review|validate|verify)\b"
    r"|(?:검토|리뷰|감사|확인|검증)",
    re.I,
)
_PRIMARY_TEST_INTENT = re.compile(
    r"^(?:add|create|expand|improve|increase|write)\b.*\b(?:tests?|specs?|coverage)\b"
    r"|(?:테스트\s*(?:커버리지\s*)?(?:추가|작성)|커버리지\s*추가)",
    re.I,
)
_DOCS_INTENT = re.compile(
    r"\b(?:docs?|documentation|readme|guide|changelog)\b"
    r"|(?:문서|가이드|README|변경로그)",
    re.I,
)
_PRIMARY_DOCS_INTENT = re.compile(
    r"^(?:document|draft|write|update)\b.*\b(?:docs?|documentation|readme|guide|changelog)\b"
    r"|^(?:문서\s*(?:업데이트|작성)|README\s*업데이트|가이드\s*작성)",
    re.I,
)
_DEBUG_INTENT = re.compile(
    r"\b(?:debug|diagnose|investigate|root cause|trace|bisect)\b"
    r"|(?:디버그|조사|원인)",
    re.I,
)
_DESIGN_INTENT = re.compile(
    r"\b(?:design|layout|style)\b|\b(?:build|create)\b.*\b(?:ui|component|frontend)\b"
    r"|(?:디자인|레이아웃|스타일|컴포넌트)",
    re.I,
)
_BUILD_FIX_INTENT = re.compile(
    r"\b(?:build|compile|tsc|type error|compilation)\b|(?:빌드|컴파일|타입 오류)",
    re.I,
)
_CLEANUP_INTENT = re.compile(
    r"\b(?:clean up|consolidate|reduce complexity|refactor|simplify)\b"
    r"|(?:정리|단순화|리팩터)",
    re.I,
)
_SECURITY_DOMAIN = re.compile(
    r"\b(?:auth|authentication|authorization|cve|injection|owasp|security|vulnerability|xss)\b"
    r"|(?:보안|인증|인가|취약점)",
    re.I,
)
_LOCAL_EXPLORATION_VERB = re.compile(
    r"\b(?:check|find|inspect|locate|look up|lookup|map|review|search|trace|understand"
    r"|where(?:\s+is|\s+are)?|which files?|what files?)\b",
    re.I,
)
_LOCAL_EXPLORATION_SUBJECT = re.compile(
    r"\b(?:file|files|symbol|symbols|repo|repository|codebase|path|paths|usage|usages"
    r"|reference|references|relationship|relationships|wiring|flow|implementation|local)\b",
    re.I,
)
_DEPENDENCY_EVAL = re.compile(
    r"\b(?:dependency|dependencies|package|packages|sdk|sdks|library|libraries"
    r"|framework|frameworks|npm|pypi|license|maintenance|migration path|vendor)\b",
    re.I,
)
_RESEARCH_TASK = re.compile(
    r"\b(?:best practice|compare|comparison|explore|external|industry|investigate"
    r"|landscape|market|patterns?|reference|research|study|survey|trend)\b"
    r"|(?:조사|비교|외부|연구|동향|패턴)",
    re.I,
)

# ── AIOS role → provider mapping ──────────────────────────────────────────

_ROLE_TO_PROVIDER = {
    "debugger": "codex",          # execution-intensive investigation
    "test-engineer": "codex",     # test generation (code-centric)
    "writer": "claude",           # documentation / explanation (language-centric)
    "code-reviewer": "claude",    # nuanced security review
    "quality-reviewer": "claude", # pattern review
    "designer": "claude",         # UI/UX reasoning
    "code-simplifier": "codex",   # mechanical refactor
    "researcher": "claude",       # external knowledge synthesis
    "dependency-expert": "claude",
    "explore": "codex",           # local codebase search
    "executor": "codex",          # default implementation worker
}

# AIOS Claude Code agent-type names (subagent_type in Agent tool)
_ROLE_TO_AGENT_TYPE = {
    "debugger": "debugger",
    "test-engineer": "test-engineer",
    "writer": "writer",
    "code-reviewer": "code-reviewer",
    "quality-reviewer": "code-reviewer",
    "designer": "designer",
    "code-simplifier": "code-simplifier",
    "researcher": "general-purpose",
    "dependency-expert": "analyst",
    "explore": "Explore",
    "executor": "executor",
}


@dataclass
class RouteResult:
    role: str
    provider: str          # "claude" | "codex" | "ollama"
    agent_type: str        # Claude Code subagent_type
    confidence: str        # "high" | "medium" | "low"
    reason: str
    schema_version: str = "aios.role_router.v1"

    def as_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "role": self.role,
            "provider": self.provider,
            "agent_type": self.agent_type,
            "confidence": self.confidence,
            "reason": self.reason,
        }


def _infer_lane_intent(text: str) -> str:
    """Infer primary lane intent from text (mirrors OMX inferLaneIntent)."""
    t = text.lower()
    if _BUILD_FIX_INTENT.search(t):
        return "build-fix"
    if _DEBUG_INTENT.search(t):
        return "debug"
    if _PRIMARY_DOCS_INTENT.search(t):
        return "docs"
    if _PRIMARY_TEST_INTENT.search(t):
        return "verification"
    if _CLEANUP_INTENT.search(t) and not _IMPLEMENTATION_INTENT.search(t):
        return "cleanup"
    if _REVIEW_INTENT.search(t) and not _IMPLEMENTATION_INTENT.search(t):
        return "review"
    if _DESIGN_INTENT.search(t) and not _IMPLEMENTATION_INTENT.search(t):
        return "design"
    if _DOCS_INTENT.search(t) and not _IMPLEMENTATION_INTENT.search(t):
        return "docs"
    return "implement"


def _is_local_exploration(text: str) -> bool:
    return bool(_LOCAL_EXPLORATION_VERB.search(text)
                and _LOCAL_EXPLORATION_SUBJECT.search(text))


def _is_dependency_evaluation(text: str) -> bool:
    return bool(_DEPENDENCY_EVAL.search(text)
                and not _IMPLEMENTATION_INTENT.search(text))


def _is_research_task(text: str) -> bool:
    return bool(_RESEARCH_TASK.search(text)
                and not _IMPLEMENTATION_INTENT.search(text))


def route(task: str, fallback_role: str = "executor") -> RouteResult:
    """Route a task description to the best AIOS role and provider.

    Mirrors OMX routeTaskToRole() but outputs AIOS vocabulary.
    """
    text = task.lower()
    intent = _infer_lane_intent(text)

    def _result(role: str, confidence: str, reason: str) -> RouteResult:
        return RouteResult(
            role=role,
            provider=_ROLE_TO_PROVIDER.get(role, "claude"),
            agent_type=_ROLE_TO_AGENT_TYPE.get(role, "executor"),
            confidence=confidence,
            reason=reason,
        )

    if intent == "build-fix":
        return _result("debugger", "high", "primary intent is build/compile repair")
    if intent == "debug":
        return _result("debugger", "high", "primary intent is investigation/debugging")
    if _is_local_exploration(text):
        return _result("explore", "high", "primary intent is local codebase/file/symbol exploration")
    if intent == "review":
        if _SECURITY_DOMAIN.search(text):
            return _result("code-reviewer", "high", "primary intent is security-focused review")
        return _result("quality-reviewer", "high", "primary intent is review/verification")
    if _SECURITY_DOMAIN.search(text) and re.search(
        r"\b(?:audit|check|find|scan|review|취약점|찾아|점검)\b", text, re.I
    ):
        return _result("code-reviewer", "high", "primary intent is security-focused review")
    if _is_dependency_evaluation(text):
        return _result("dependency-expert", "high", "primary intent is external dependency/package evaluation")
    if _is_research_task(text):
        return _result("researcher", "high", "primary intent is external documentation/reference research")
    if intent == "docs":
        return _result("writer", "high", "primary intent is documentation deliverable")
    if intent == "design":
        return _result("designer", "high", "primary intent is UI/design implementation")
    if intent == "cleanup":
        return _result("code-simplifier", "high", "primary intent is simplification/refactor work")
    if intent == "verification":
        return _result("test-engineer", "high", "primary intent is test/verification output")

    # Default: implementation
    return _result(fallback_role, "low", "no strong signal; defaulting to implementation lane")


if __name__ == "__main__":
    import json
    import sys
    task = " ".join(sys.argv[1:]) or "implement feature X"
    print(json.dumps(route(task).as_dict(), ensure_ascii=False, indent=2))

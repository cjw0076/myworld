#!/usr/bin/env python3
"""aios_capture_args — privacy-scrubbing for arg-aware tool-call capture (Phase A deepening).

Founder GO (2026-06-25): capture structured tool-call args, not just names, so the CLS
corpus can (a) distinguish productive repetition from stuck retries — `Bash×12` of
distinct git commands vs 12 identical retries — and (b) carry a tool-call FORMAT signal
for the QLoRA. The non-negotiable privacy invariants (DNA #7) still hold: secrets, private
paths (_from_desktop / dain / minyoung), .env, and content bodies NEVER get stored.

Two products, both privacy-safe:
  - call_signature(tool, args): a non-reversible hash of the FULL raw call, computed in
    memory and stored as a hash only — lets repeat/doom detection see identical-vs-distinct
    consecutive calls without persisting any content.
  - arg_skeleton(args): the structural shape (keys + value types/lengths), with sensitive
    keys / private markers / secret-looking values / long bodies redacted — enough to learn
    tool-call format, nothing sensitive retained.

This module persists NOTHING itself; it is a pure transform the capture layer calls.
"""
from __future__ import annotations

import hashlib
import json
import re

# arg keys whose VALUE is sensitive regardless of content
_SENSITIVE_KEY_RE = re.compile(
    r"(api[_-]?key|secret|token|password|passwd|credential|authorization|bearer|"
    r"access[_-]?key|private[_-]?key|session[_-]?id|cookie)", re.I)

# arg keys that carry free-text BODIES — keep shape, never the body
_BODY_KEYS = {"command", "old_string", "new_string", "content", "prompt", "body",
              "code", "query", "text", "message", "input", "stdin", "patch", "diff"}

# substrings marking private-gated content (must never be stored)
_PRIVATE_MARKERS = ("_from_desktop", "/dain/", "/minyoung/", "/dain", "/minyoung",
                    ".env", "minyoung", "dain")

# value patterns that look like secrets
_SECRET_VALUE_RE = re.compile(
    r"(sk-[A-Za-z0-9]{8,}|ghp_[A-Za-z0-9]{8,}|AKIA[0-9A-Z]{12,}|"
    r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}|xox[baprs]-[A-Za-z0-9-]{8,}|"
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----|[A-Fa-f0-9]{40,})")

_MAX_SAFE_STR = 40   # strings longer than this are reduced to their length only


def _has_private_marker(s: str) -> bool:
    low = s.lower()
    return any(m in low for m in _PRIVATE_MARKERS)


def scrub_value(key: str, v, max_str: int = _MAX_SAFE_STR):
    """Privacy-scrub a single value, preserving STRUCTURE not content."""
    if isinstance(v, dict):
        return {k: scrub_value(k, vv, max_str) for k, vv in v.items()}
    if isinstance(v, list):
        return [scrub_value(key, vv, max_str) for vv in v[:20]]   # cap list length
    if isinstance(v, bool) or v is None or isinstance(v, (int, float)):
        return v                                                  # non-string scalars are safe
    s = str(v)
    if _SENSITIVE_KEY_RE.search(key or ""):
        return "<redacted:sensitive-key>"
    if _has_private_marker(s):
        return "<redacted:private>"
    if _SECRET_VALUE_RE.search(s):
        return "<redacted:secret>"
    if (key in _BODY_KEYS) or len(s) > max_str:
        return f"<str:{len(s)}>"                                  # shape only, no body
    return s                                                      # short, safe enum/flag


def arg_skeleton(args: dict | None) -> dict:
    """Structural, privacy-scrubbed skeleton of a tool call's args — safe to persist."""
    if not isinstance(args, dict):
        return {}
    return {k: scrub_value(k, v) for k, v in args.items()}


_SLUG_RE = re.compile(r"[A-Za-z0-9_.:-]{1,40}")        # no '/', no spaces
_SECRET_PREFIX_RE = re.compile(r"^(sk-|ghp_|xox|AKIA|eyJ)")


def safe_metadata_token(s: str) -> str:
    """Allowlist a single metadata token (dataset name / tool_freq key) for egress.
    Returns the token if it is a clean slug carrying no private marker or secret shape,
    else "" — so a poisoned memory can't ride a slug-shaped secret (`sk-LIVE-…`, no
    spaces, passes a naive char-class strip) or a private path (`/dain/private`) along.
    A 'dash-broken' secret like sk-LIVE-9f3a evades the entropy regex, so prefix-match too."""
    t = str(s)
    if not t or not _SLUG_RE.fullmatch(t):
        return ""
    if _has_private_marker(t) or _SECRET_VALUE_RE.search(t) or _SECRET_PREFIX_RE.search(t):
        return ""
    return t


def safe_summary(category: str, tools=None, loop_type: str | None = None) -> str:
    """Canonical privacy gate (DNA #7 / P0) for ANY text sent to the GLOBAL Akashic.
    The only string that may leave the device for the shared corpus — structural
    metadata, NEVER the raw goal/prompt/output. Every outbound global call site
    (contribute / sync / predict, in aios_agent_system, aios_memory, aios_agent_behavior)
    must route its `content`/`query`/`context` through THIS function. The worker embeds
    whatever it receives via a third-party model, so raw text must never reach it; rich
    semantic recall is the LOCAL private vault's job (no network)."""
    parts = [f"category:{category or 'unknown'}"]
    if tools:
        # cap at 3 (was 10): the server embeds this string, so the VECTOR must not encode
        # a richer tool fingerprint than the visible top_tools egress (≤3). Keeps the
        # embedded fingerprint consistent with the k-anon egress promise (review item 5).
        parts.append("tools:" + ",".join(str(t) for t in list(tools)[:3]))
    if loop_type:
        parts.append(f"pattern:{loop_type}")
    return " ".join(parts)


def call_signature(tool: str, args: dict | None) -> str:
    """Non-reversible hash of the FULL raw call (tool + args). Computed transiently;
    only the hash is stored. Identical calls → identical signature; distinct calls →
    distinct signature — that is all repeat/doom detection needs, with zero content kept."""
    try:
        canon = json.dumps(args or {}, sort_keys=True, ensure_ascii=False, default=str)
    except Exception:  # noqa: BLE001
        canon = repr(args)
    return hashlib.sha256(f"{tool}\x00{canon}".encode("utf-8", "replace")).hexdigest()[:16]


def has_stuck_repeat(signatures: list[str], threshold: int = 4) -> bool:
    """True if the SAME call signature repeats consecutively >= threshold times — a
    genuine stuck retry (distinct calls have distinct signatures, so productive
    repetition of one tool with different args does NOT trip this). This is the
    arg-aware replacement for the name-only doom heuristic."""
    if not signatures:
        return False
    run = 1
    for i in range(1, len(signatures)):
        run = run + 1 if signatures[i] == signatures[i - 1] else 1
        if run >= threshold:
            return True
    return False


if __name__ == "__main__":
    # self-check (ponytail: money/security path leaves a runnable check)
    sk = arg_skeleton({"api_key": "sk-livesecret123456789", "file_path": "/home/u/_from_desktop/x",
                       "command": "git status && cat secret", "limit": 5, "flag": "json"})
    assert sk["api_key"] == "<redacted:sensitive-key>", sk
    assert sk["file_path"] == "<redacted:private>", sk
    assert sk["command"].startswith("<str:"), sk
    assert sk["limit"] == 5 and sk["flag"] == "json", sk
    a = call_signature("Bash", {"command": "git status"})
    b = call_signature("Bash", {"command": "git diff"})
    assert a != b and a == call_signature("Bash", {"command": "git status"})
    assert has_stuck_repeat([a, a, a, a]) and not has_stuck_repeat([a, b, a, b])
    print("ok")

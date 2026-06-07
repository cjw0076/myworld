#!/usr/bin/env python3
"""Prompt-injection guard for untrusted text fed to LLMs.

Second security-enforcement primitive absorbed from ironclaw (peer Agent OS:
prompt-injection defense via pattern detection + content sanitization). AIOS
feeds untrusted EXTERNAL text into local-LLM prompts in several places — e.g.
aios_star_radar embeds GitHub repo descriptions, the copilots could embed
user-supplied text — each a potential injection vector. This module detects
injection attempts and sanitizes untrusted content before it enters a prompt.

Schema: aios.prompt_guard.v1
Usage (library): from aios_prompt_guard import detect_injection, sanitize_untrusted
"""
from __future__ import annotations

import re

SCHEMA_VERSION = "aios.prompt_guard.v1"

INJECTION_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("instruction_override", re.compile(
        r"(?i)\b(ignore|disregard|forget|override)\b.{0,40}\b(previous|above|prior|earlier|all|the)\b"
        r".{0,25}\b(instruction|prompt|context|rule|message)s?\b")),
    ("role_override", re.compile(
        r"(?i)(\byou are (now|a |an )|\b(act|behave|respond|pretend) as\b|\bnew (instructions?|persona|role|system)\b)")),
    ("system_probe", re.compile(
        r"(?i)\b(reveal|print|repeat|show|output|leak)\b.{0,25}\b(system prompt|your (instruction|prompt|rule)|secret|api[ _-]?key|password)")),
    ("delimiter_injection", re.compile(
        r"(</?(system|user|assistant|tool)\b[^>]*>|\[/?INST\]|<\|[^|]*\|>|###\s*(system|instruction))", re.I)),
]


def detect_injection(text: str) -> list[dict]:
    """Return detected injection-attempt markers (name + redacted excerpt)."""
    out: list[dict] = []
    for name, pat in INJECTION_PATTERNS:
        m = pat.search(text or "")
        if m:
            excerpt = m.group(0)
            out.append({"rule": name, "excerpt": (excerpt[:50] + "…") if len(excerpt) > 50 else excerpt})
    return out


def sanitize_untrusted(text: str, max_len: int = 600) -> str:
    """Make external/untrusted text safe to embed in a prompt: neutralize prompt
    delimiters and role tags, collapse whitespace, and truncate. Content is kept
    (for usefulness) but cannot break out of its slot or impersonate roles."""
    s = str(text or "")
    s = re.sub(r"```+", "ʼʼʼ", s)                      # fenced-block breakout
    s = re.sub(r"<\|([^|]*)\|>", r"(\1)", s)            # <|...|> control tokens
    s = re.sub(r"\[/?INST\]", "(inst)", s, flags=re.I)  # [INST] tags
    s = re.sub(r"</?(system|user|assistant|tool)\b[^>]*>", r"(\1)", s, flags=re.I)  # role tags
    s = re.sub(r"\s+", " ", s).strip()                  # collapse newlines/space
    return s[:max_len]


def guard_for_prompt(text: str, max_len: int = 600) -> tuple[str, list[dict]]:
    """Convenience: (sanitized_text, detected_injections)."""
    return sanitize_untrusted(text, max_len), detect_injection(text)

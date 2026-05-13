---
contract_id: ASC-0087
slug: provider-prompt-bootstrap
status: accepted
goal: When AIOS is installed (or refreshed) on a machine, automatically write provider-specific system-prompt files (CLAUDE.md, AGENTS.md, codex/gemini/cursor/aider equivalents) so EVERY provider CLI on that machine is AIOS-aware — knows how to use AIOS, where to log self-observation, the contract/dispatch protocol, and the operator discipline — without per-CLI manual setup.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by claude acting operator (founder directive 2026-05-13 KST)
acceptance_authority: claude@myworld (operator) per founder turn correcting prior framing — "AIOS를 설치하게되면, Provider CLI의 시스템 프롬프트 파일 (e.g. Claude.md, Agent.md)에 AIOS를 사용하는 방법, 자기관찰을 AIOS에 누적하는 프로토콜, 이런 것들을 모두 명세해놓도록 세팅해둬야하지 않을까 싶어".
origin: claude wrote a single ~/.claude/CLAUDE.md manually as part of the prior turn. Founder pointed out this should be SYSTEMATIC — every provider CLI installed on the machine, templated automatically by AIOS install, kept in sync as AIOS evolves.
---

# ASC-0087 Provider Prompt Bootstrap

## Why Now

Right now, claude@myworld is AIOS-aware because the operator manually
wrote `~/.claude/CLAUDE.md`. Codex@myworld is AIOS-aware because it
reads contract files. But on a NEW machine where AIOS gets installed:

- Claude Code session → won't know about AIOS until manual setup
- OpenAI Codex CLI → won't know until manual setup
- Gemini CLI → won't know
- Cursor / Aider / etc → won't know
- Future provider CLIs we haven't enumerated → won't know

This makes AIOS install incomplete. AIOS should treat the **provider
CLI ecosystem** as part of its installation surface, not just system
services + binaries.

After this contract, `aios install` (whether implemented as ASC-0080
native install or just a `aios bootstrap-prompts` subcommand) writes
the right prompt file in the right place for every provider CLI it
detects, with content templated from a single AIOS source.

## Required Reading

- `~/.claude/CLAUDE.md` (current claude global, written manually)
- `docs/AIOS_OPERATOR_PLAYBOOK.md`
- `docs/AIOS_AGENT_SELF_LOOP.md`
- `docs/AIOS_CLAUDE_SELF_OBSERVATION_LOG.md`
- `docs/contracts/ASC-0080-aios-native-installation.md` (proposed,
  founder HOLD — this contract is independent and can ship without it)
- `docs/contracts/ASC-0050-aios-primitive-surface.md`

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_provider_prompts.py`
- `scripts/templates/provider_prompts/CLAUDE.md.tmpl`
- `scripts/templates/provider_prompts/AGENTS.md.tmpl`
- `scripts/templates/provider_prompts/GEMINI.md.tmpl`
- `scripts/templates/provider_prompts/CODEX_INSTRUCTIONS.md.tmpl`
- `scripts/templates/provider_prompts/CURSORRULES.tmpl`
- `scripts/templates/provider_prompts/AIDER_CONVENTIONS.md.tmpl`
- `scripts/templates/provider_prompts/_shared_invariants.md.tmpl`
- `tests/test_aios_provider_prompts.py`
- `docs/AIOS_PROVIDER_PROMPTS.md`
- `docs/contracts/ASC-0087-provider-prompt-bootstrap.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/**`, `memoryOS/**`, `CapabilityOS/**`, `GenesisOS/**`, `uri/**`
- `_from_desktop/**`, `dain/**`, `minyoung/**`
- `.env`, `.env.*`
- ANY file outside the user's home that requires sudo

## Per-OS Responsibility

### myworld.must_produce

#### `scripts/aios_provider_prompts.py` — main bootstrap script

CLI surface:

```bash
# detect installed provider CLIs
python scripts/aios_provider_prompts.py detect --json

# preview what would be written (dry-run)
python scripts/aios_provider_prompts.py bootstrap --dry-run --json

# write prompt files (with safe-merge if file exists)
python scripts/aios_provider_prompts.py bootstrap --json

# show diff between current installed prompt files and AIOS template
python scripts/aios_provider_prompts.py status --json

# refresh: re-render templates with current AIOS state, merge safely
python scripts/aios_provider_prompts.py refresh --json
```

#### Provider registry (V1)

Each entry: `{name, paths_to_check[], file_to_write, template, idioms}`.

V1 covers:

| Provider | Detect by | File location | Template |
|---|---|---|---|
| Claude Code | `~/.claude/` exists | `~/.claude/CLAUDE.md` | `CLAUDE.md.tmpl` |
| Project-local Claude | `.claude/` exists in cwd | `.claude/CLAUDE.md` | `CLAUDE.md.tmpl` |
| Repo-root Claude | `CLAUDE.md` already in repo | `CLAUDE.md` (merge only) | `CLAUDE.md.tmpl` |
| Codex CLI | `~/.codex/` or `~/.config/codex/` | `~/.codex/AGENTS.md` (TBD by codex docs) | `AGENTS.md.tmpl` |
| Gemini CLI | `~/.gemini/` exists | `~/.gemini/CLAUDE.md` or equivalent | `GEMINI.md.tmpl` |
| Cursor | `.cursor/` in cwd | `.cursorrules` | `CURSORRULES.tmpl` |
| Aider | `.aider*` config | `CONVENTIONS.md` | `AIDER_CONVENTIONS.md.tmpl` |

Future providers: registry is data, easy to extend.

#### Templates share a `_shared_invariants.md` block

```markdown
{{include _shared_invariants.md}}
```

The shared block contains:
- AIOS overview (5 OS, operator pair)
- Required reading paths
- AIOS protocol defaults (contract first, don't bypass)
- Persistent monitor pattern
- 5-mode operator discipline
- Self-observation log append protocol (path: docs/AIOS_CLAUDE_SELF_OBSERVATION_LOG.md, format)
- Founder escalation triggers
- 7 DNA invariants (under ASC-0084 debate)
- Privacy boundaries
- Memory system pointer

Provider-specific templates wrap the shared block with idioms:
- `CLAUDE.md.tmpl`: Claude Code tool catalog references (Task, Monitor, Skill etc)
- `AGENTS.md.tmpl`: Codex CLI conventions + ASC-0085 reference
- `GEMINI.md.tmpl`: Gemini's preferred format
- `CURSORRULES.tmpl`: cursor rules format
- `AIDER_CONVENTIONS.md.tmpl`: aider markdown style

#### Safe-merge semantics

If a target file already exists:
1. Check for AIOS marker block (delimited by `<!-- AIOS BEGIN -->` ...
   `<!-- AIOS END -->`).
2. If marker block exists → replace just that block.
3. If file exists but no marker → APPEND with marker block at bottom +
   record decision in `.aios/provider_prompts/merges.jsonl`.
4. If file doesn't exist → create with marker block.
5. NEVER blow away user customization outside the marker block.

#### Versioning

Each generated block contains:
- `<!-- AIOS BEGIN v=<aios_version> generated_at=<iso> -->`
- This lets `status` show drift between installed version and current.

#### Tests

- Each template renders with placeholder values.
- Detect finds Claude Code on this machine.
- Bootstrap dry-run writes nothing but produces accurate diff.
- Safe-merge preserves a synthetic existing file.
- Refresh updates marker block without touching outside-marker content.

### child repos

- No source change. Templates are read-only by them.

## Verification Gate

```bash
python -m py_compile scripts/aios_provider_prompts.py
python -m unittest tests/test_aios_provider_prompts.py
python scripts/aios_provider_prompts.py detect --json
python scripts/aios_provider_prompts.py bootstrap --dry-run --json
python scripts/aios_provider_prompts.py status --json
# Real bootstrap into a temp HOME for safety:
HOME=/tmp/aios_bootstrap_test python scripts/aios_provider_prompts.py bootstrap --json
test -f /tmp/aios_bootstrap_test/.claude/CLAUDE.md
grep -q "AIOS BEGIN" /tmp/aios_bootstrap_test/.claude/CLAUDE.md
python -m unittest discover -s tests -p 'test_aios_*.py'
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- `detect` finds at least Claude Code on the dev machine.
- `bootstrap --dry-run` shows planned writes without modifying anything.
- Real bootstrap into temp HOME creates marker-delimited block.
- Re-running bootstrap into same HOME does NOT duplicate (idempotent).
- Status correctly reports drift when AIOS version changes.
- Synthetic test of safe-merge: pre-existing file's outside-marker
  content is preserved bit-for-bit.

## Stop Conditions

- `bootstrap_overwrites_user_content`: writes outside marker block
- `bootstrap_requires_sudo`: V1 must be user-space only
- `bootstrap_silent_difficulty`: detect finds provider but bootstrap
  silently skips it (must report)
- `template_drift`: shared invariants block diverges across providers
  (templates share a single source)
- `child_repo_scope_leak`
- `verification_gate_failed`

## Receipts

Pending.

## Work Packets

### WP-0087-A — codex@myworld implements bootstrap script + templates

- target_agent: codex
- target_repo: myworld
- status: accepted
- depends_on: ASC-0050 closed (primitive surface — for `tools register`
  hook), ASC-0085 closed if available (codex side observation)
- brief: |
    Implement `aios_provider_prompts.py` with the registry, templates
    (incl. shared invariants block), safe-merge logic, and tests.
    Templates should be markdown so they're inspectable.

    Dogfood: run bootstrap into the dev machine's actual ~/.claude
    AND into a temp HOME. Verify the existing manually-written
    ~/.claude/CLAUDE.md is preserved (becomes the AIOS marker block,
    or is wrapped in marker block on first refresh — operator's
    choice, but must NOT lose content).

    For provider locations not 100% confirmed (Codex CLI's exact
    AGENTS.md path, Gemini's), check the provider docs and write
    template + detect rule conservatively. Mark unconfirmed providers
    as `experimental: true` in the registry so they don't get written
    by default.

- result: pending

---
contract_id: ASC-0111
slug: founder-behavior-ingestion
status: closed
goal: Capture founder (재원) directives, reframes, and decision patterns as first-class memoryOS records — drafts with origin=founder_directive — so the system gains an actual model of how its founder operates. Today this is scattered across chat, operator_sessions, claude local memory, and verbatim acceptance_authority quotes; memoryOS itself has 0% coverage.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by claude as verifier
acceptance_authority: claude@myworld (verifier role, /loop GOAL-0002 + founder question "내 작업방식이 memoryOS에 저장되나?")
origin: 2026-05-13 verifier round 2 probed memoryOS for founder-related drafts — 2/43 (passing mentions only, no structured capture). AIOS effectively has no memory of its own founder despite 1.5 days of intense direction-setting.
closed: 2026-05-13 KST
---

# ASC-0111 Founder Behavior Ingestion

## Why Now (DNA Inv 5)

DNA Invariant 5 (provenance chain) requires every record to be
traceable. Today founder directives are the most causally-load-bearing
inputs in AIOS — every reframe ("AIOS=Government", "discomfort=
creativity source", "Founder처럼 동작") shapes downstream contracts —
but they are not retrievable as memoryOS records. The provenance chain
breaks at its most important link.

When founder asked "내 작업방식이 memoryOS에 저장이 되는지? 그
memoryOS를 토대로 네가 내 역할을 대신할 수 있는지?", the honest answer
is: no, and no. This contract takes the first step on yes.

## Required Reading

- `docs/AIOS_DNA.md` (after ASC-0105) — Invariants 5, 6, 8
- `docs/operator_sessions/2026-05-12-claude-myworld.md` (current
  founder turn capture, NOT in memoryOS)
- `~/.claude/projects/-home-user-workspaces-jaewon-myworld/memory/`
  (claude-side, NOT in memoryOS)
- `scripts/aios_contract_to_memory.py` (ASC-0091 closeout writeback —
  pattern to extend)
- `memoryOS/memoryos/schema.py` (memory object schema)

## Scope

repos: `myworld`, `memoryOS`

allowed_files:

- `scripts/aios_founder_capture.py`
- `tests/test_aios_founder_capture.py`
- `memoryOS/memoryos/cli.py` (new `ingest-founder-directive` subcommand)
- `memoryOS/tests/test_founder_ingest.py`
- `docs/AIOS_FOUNDER_INGESTION.md`
- `docs/contracts/ASC-0111-founder-behavior-ingestion.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `docs/operator_sessions/**` (read-only — source of capture)
- `~/.claude/**` (claude private — NOT shared with memoryOS)
- `_from_desktop/**`, `dain/**`, `minyoung/**`
- `hivemind/**`, `CapabilityOS/**`, `GenesisOS/**`, `uri/**`
- `.env`

## Per-OS Responsibility

### myworld.must_produce

`scripts/aios_founder_capture.py`:

- inputs:
  - operator session log path (default
    `docs/operator_sessions/<latest>.md`)
  - OR explicit founder turn text (for live capture)
- extraction (deterministic V1):
  - parse "## Mode transitions" table — each entry where founder
    appears
  - parse "## Decisions log" entries citing founder words
  - parse acceptance_authority lines across docs/contracts/ASC-*.md
    that quote founder verbatim
  - extract per-directive:
    - `directive_text`: the verbatim Korean/English quote
    - `reframe_class`: vision / scope / discomfort / role / privacy /
      escalation / other
    - `cited_in_contracts`: list of ASC-NNNN referencing this directive
    - `captured_at`, `source_path`
- output JSON conforms to new schema
  `aios.founder_directive_memory.v1`
- pipes into `memoryos ingest-founder-directive`

### memoryOS.must_produce

`memoryos ingest-founder-directive` subcommand:

- accepts `aios.founder_directive_memory.v1`
- produces `MemoryObject(type=decision, origin=founder_directive,
  status=draft)`
- preserves verbatim text in `content` field (no paraphrase)
- raw_refs include source_path + line range
- evidence_refs cite contracts that already use this directive
- idempotent via stable_id on (directive_text, source_path)

### child repos: no change

## Verification Gate

```bash
python -m py_compile scripts/aios_founder_capture.py
python -m unittest tests/test_aios_founder_capture.py
python scripts/aios_founder_capture.py --write .aios/tmp/founder_capture.json --json
python -m memoryos.cli --root memoryOS ingest-founder-directive ../.aios/tmp/founder_capture.json --json
python -m memoryos.cli --root memoryOS drafts list --origin founder_directive --json
python -m unittest tests/test_aios_founder_capture.py memoryOS/tests/test_founder_ingest.py
python -m unittest discover -s tests -p 'test_aios_*.py'
```

Pass criteria (DNA Inv 5):

- ≥20 founder directives extracted from current operator session log
- All become memoryOS drafts with origin=founder_directive
- Re-running ingest is idempotent (no duplicates)
- ASC-0110 retrieval (once it ships) can find the directives by their
  Korean/English keywords

## Stop Conditions (DNA Inv 7)

- `founder_paraphrased`: directives must be verbatim, not summarized
- `founder_pii_leak`: real name/email/private personal info excluded
  unless founder explicitly authorized
- `chat_scroll_ingest`: do NOT scrape chat scroll (ephemeral, may
  contain transient frustration not intended as durable directive)
- `auto_accept_founder_draft`: drafts stay draft until reviewed
- `child_repo_scope_leak`
- `verification_gate_failed`

## Receipts

- myworld implementation:
  - `scripts/aios_founder_capture.py`
  - `tests/test_aios_founder_capture.py`
  - `docs/AIOS_FOUNDER_INGESTION.md`
- memoryOS implementation:
  - `memoryOS/memoryos/cli.py`
  - `memoryOS/tests/test_founder_ingest.py`
  - memoryOS durability commit `6391499`
- Live ingest:
  - `python scripts/aios_founder_capture.py --write .aios/tmp/founder_capture.json --json`
  - captured `85` directives
  - `python -m memoryos.cli --root memoryOS ingest-founder-directive ../.aios/tmp/founder_capture.json --json`
  - created `85` `origin=founder_directive` draft memories
  - re-run returned `written=0`, `skipped=85`
- Verification passed:
  - `python -m py_compile scripts/aios_founder_capture.py memoryOS/memoryos/cli.py`
  - `python -m unittest tests/test_aios_founder_capture.py memoryOS.tests.test_founder_ingest`
  - `python -m unittest tests/test_aios_founder_capture.py memoryOS/tests/test_founder_ingest.py`
  - `python -m unittest discover -s tests -p 'test_aios_*.py'` passed 233 tests
  - `python scripts/aios_dispatch.py watch --repo myworld --dispatch-id asc-0111 --once`
  - `python scripts/aios_monitor.py assess --write --json` returned `health=clear`
- Dispatch result:
  - `.aios/outbox/myworld/asc-0111.myworld.result.json` passed.
- Release writeback:
  - MemoryOS closeout draft `mem_ef62dc7be6b77fb9`
- Activation review, after founder asked why Claude could not see founder
  working style through MemoryOS:
  - Diagnosis: the founder corpus existed as `85` `origin=founder_directive`
    drafts, but `0` founder directives were accepted, so Hive/Claude context
    builds did not select them.
  - Operator review approved `10` direct founder directives with durable
    contract provenance:
    - `mem_001f6d5191fb8e51` — Claude CLI primitive absorption
    - `mem_70c8edbf4c5c9c7b` — use AIOS until completion, coevolve MemoryOS,
      CapabilityOS, and Hive
    - `mem_4f390c90de100dbf` — delegated founder/operator role
    - `mem_61910dd09950fc81` — final interface is AIOS, not provider CLIs
    - `mem_1f18cea463eed9fd` — absorb new providers and local LLMs
    - `mem_0c3b41fd22b1d801` — AIOS work visibility gap
    - `mem_4ec54ac7409828c8` — continue issuing contracts
    - `mem_7a13c1fc3880df9c` — question whether MemoryOS stores founder work style
    - `mem_fdf38e3f47d1aed4` — absorb user logs/work style into few-shot patterns
    - `mem_3d34968d34418b03` — substitute for founder role in living-organism arc
  - Runtime verification:
    - `python -m memoryos.cli --root memoryOS search "AIOS완성 공진화 memoryOS capabilityOS hive mind founder" --origin founder_directive --json`
      returned accepted founder memory `mem_70c8edbf4c5c9c7b`.
    - `python -m memoryos.cli --root memoryOS context build --task "AIOS완성 공진화 memoryOS capabilityOS hive mind founder directive" --for hive --project AIOS --json --explain --include-excluded`
      selected founder memories `mem_70c8edbf4c5c9c7b`,
      `mem_7a13c1fc3880df9c`, and `mem_3d34968d34418b03` in trace
      `rtrace_31b18b1d2fd7c0aa`.
    - `python -m memoryos.cli --root memoryOS context build --task "founder role delegated living organism 작업방식 memoryOS" --for hive --project AIOS --json --explain --include-excluded`
      selected founder memories `mem_70c8edbf4c5c9c7b`,
      `mem_7a13c1fc3880df9c`, `mem_fdf38e3f47d1aed4`, and
      `mem_3d34968d34418b03` in trace `rtrace_a25c117e6fae9cbf`.
  - Remaining gap: retrieval quality is still coarse; several exact founder
    directives can be accepted but ranked as `task_no_match` for mixed-language
    queries. ASC-0110 remains the structural fix for ranking/tokenization.

## Work Packets

### WP-0111-A — codex@myworld extracts + ingest pipeline

- target_agent: codex
- target_repo: myworld
- depends_on: ASC-0091 closed ✓
- brief: implement deterministic extractor over operator_sessions/* +
  contract acceptance_authority lines. Output founder_directive_memory.v1
  JSON. Pipe to memoryOS.

### WP-0111-B — codex@memoryOS adds founder ingest subcommand

- target_agent: codex
- target_repo: memoryOS
- depends_on: WP-0111-A
- brief: ingest-founder-directive subcommand producing MemoryObject
  with origin=founder_directive. Stable id. Idempotent. Test.

## Honest non-promise

This contract captures founder directives. It does NOT model founder
*reasoning* or *intuition*. Even after this closes, claude cannot
replace founder for vision/reframe — only for routine acceptance of
already-precedented patterns. Real "founder model" is a multi-contract
deep arc (likely requires GenesisOS real implementation per ASC-0069+,
plus discomfort manufacturing per the saved
`feedback-discomfort-as-creativity-source` memory).

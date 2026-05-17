---
contract_id: ASC-0088
slug: aios-universal-agent-interface
status: superseded
goal: Define a single canonical AIOS Universal Agent Interface spec that any agent (claude/codex/gemini/local LLM/etc.) on any machine — whether or not AIOS is installed locally — reads to know AIOS exists, how to use it, and how to propagate self-observations back to AIOS with a precise where/when/who/what protocol.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by claude acting operator (founder directive 2026-05-13 KST)
acceptance_authority: claude@myworld (operator) per founder turn correcting prior framing — the goal is not just templating per-provider prompt files (ASC-0087) but a UNIVERSAL spec inside global system prompts so any agent anywhere knows how to relay self-observation back to AIOS even when working in unrelated contexts.
origin: ASC-0087 templates per-CLI prompt files but each file would otherwise have to re-define the AIOS interaction protocol. ASC-0088 extracts that protocol into a single versioned spec. ASC-0087 templates simply reference it by stable URL/path.
superseded_by: ASC-0093
superseded_reason: ASC-0089 Hive debate selected B1 tiny spec and rejected this B5 full spec + buffer/sync direction.
---

# ASC-0088 AIOS Universal Agent Interface

## Why Now

ASC-0087 templates provider-specific prompt files. But each file
otherwise has to redundantly redefine:

- Where AIOS lives on disk
- Which observations matter
- When to write them
- Who writes which kind
- What schema each observation uses
- How to handoff (sync vs async, online vs offline)

Without a single spec, each provider template drifts. And agents
working in OTHER repos / OTHER projects (not under `myworld/`) won't
know AIOS exists at all — they'll silently lose observations that
could have flown into AIOS's accumulating corpus.

ASC-0088 defines `docs/AIOS_AGENT_INTERFACE.md` as the canonical
versioned spec. ASC-0087 templates reference it (so single source of
truth). Future providers added to ASC-0087 registry inherit the spec
automatically.

## Required Reading

- `docs/AIOS_AGENT_PROTOCOL.md` (existing — durable record format)
- `docs/AIOS_OPERATOR_PLAYBOOK.md`
- `docs/AIOS_AGENT_SELF_LOOP.md`
- `docs/AIOS_CLAUDE_SELF_OBSERVATION_LOG.md`
- `docs/contracts/ASC-0087-provider-prompt-bootstrap.md`
- `~/.claude/CLAUDE.md` (current operator-written, will be regenerated
  to reference this spec after ASC-0087 ships)

## Scope

repos:

- `myworld`

allowed_files:

- `docs/AIOS_AGENT_INTERFACE.md`
- `scripts/aios_observation_buffer.py`
- `scripts/aios_observation_sync.py`
- `tests/test_aios_observation_buffer.py`
- `tests/test_aios_observation_sync.py`
- `docs/contracts/ASC-0088-aios-universal-agent-interface.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/**`, `memoryOS/**`, `CapabilityOS/**`, `GenesisOS/**`, `uri/**`
- `_from_desktop/**`, `dain/**`, `minyoung/**`
- `.env`, `.env.*`

## Per-OS Responsibility

### myworld.must_produce

#### `docs/AIOS_AGENT_INTERFACE.md` — the canonical spec

A single self-contained markdown file. Every section is normative.

**Section 1 — Discovery.** How an agent figures out whether AIOS is
reachable:

```
1. Check $AIOS_ROOT environment variable
2. Walk up from cwd looking for `myworld/CLAUDE.md` marker
3. Check ~/.aios/locator.json (written by ASC-0087 bootstrap)
4. If none → AIOS is OFFLINE for this agent; use buffer mode
```

**Section 2 — WHERE (paths the agent writes to).**

If AIOS is reachable:
```
{aios_root}/docs/AIOS_CLAUDE_SELF_OBSERVATION_LOG.md     ← claude self-obs
{aios_root}/docs/AIOS_CODEX_SELF_OBSERVATION_LOG.md      ← codex self-obs
{aios_root}/docs/AIOS_GENERIC_AGENT_OBSERVATION_LOG.md   ← others
{aios_root}/.aios/goal_inbox/<repo>/                     ← friction submissions
{aios_root}/.aios/observation_buffer/                    ← async observations
{aios_root}/docs/discoveries/<date>-<topic>.md            ← cross-OS findings
```

If AIOS is OFFLINE:
```
~/.aios_buffer/observations/<uuid>.json                  ← portable buffer
```
Synced to AIOS later via `aios_observation_sync.py`.

**Section 3 — WHEN (triggers).**

Append a self-observation entry when:
- A meaningful session ends (≥ 3 turns of operator work)
- A new tool is used for the first time on this machine
- A pattern is discovered (cross-domain insight, new failure mode)
- A self-correction occurs (caught your own mistake)
- A founder/user surfaces a vision-level direction
- A cross-repo insight emerges

Submit a friction packet (goal_inbox) when:
- Work is blocked on something AIOS could provide but doesn't
- A capability gap is hit (tool/route/schema missing)
- Cross-OS coordination would unblock you

Write a discovery doc when:
- A finding crosses ≥ 2 OS boundaries
- A pattern recurs in ≥ 3 separate sessions
- An external evaluation surfaces actionable critique

**Section 4 — WHO (agent role taxonomy).**

| Role | Scope | Writes |
|---|---|---|
| `operator` (claude/codex@myworld) | full AIOS workflow | self-obs log + ledger + contracts |
| `child_agent` (codex@hivemind/memoryOS/CapabilityOS/GenesisOS/uri) | repo-local only | repo worklog + goal_inbox to myworld |
| `reviewer` (any agent reviewing memory drafts) | review-only | drafts approve/reject/needs_evidence |
| `critic` (Genesis prompt-prison checker) | advisory | critic report attached to contract |
| `researcher` (any agent doing web research / external eval) | evidence collection | web_research_receipt + discovery doc |
| `outsider` (agent in a totally unrelated repo/project) | observation only | buffer for later sync |

Role is identified by `agent_id` in the entry (e.g.
`claude@quantum_lab`, `codex@cjw070690-laptop`, `qwen@ollama-local`).

**Section 5 — WHAT (schemas).**

Self-observation entry schema (matches existing log format):
```yaml
schema_version: aios.self_observation.v1
agent_id: <role@host>
timestamp: <ISO 8601 KST>
topic: <one-line>
session_handle: <chat or session distinguisher>
mode_breakdown: {observe: pct, verify: pct, ...}
tools_used: [...]
tools_NOT_used: [...]   # important for ASC-0066
substrate_specific_behaviors: [...]
failures_recovered: [...]
failures_escalated: [...]
key_decisions: [{decision: str, why: str}]
new_invariants_or_patterns: [...]
self_corrections: [...]
```

Friction packet schema (matches existing repo-goal protocol).

Discovery doc: free-form markdown, but must include:
- Date in filename
- Topic in filename
- Cross-OS labels at top
- Evidence references (file paths, contract IDs, commit SHAs)

**Section 6 — HOW (sync protocol).**

If AIOS is reachable: write directly. Atomicity via O_APPEND or
single-file rewrite-with-temp-rename pattern.

If AIOS is offline:
1. Write to `~/.aios_buffer/observations/<uuid>.json` with full schema
2. On next AIOS-reachable machine session, run
   `aios_observation_sync.py push --buffer ~/.aios_buffer`
3. Sync script validates each buffer entry + appends to right log/inbox
4. Successfully synced entries move to `~/.aios_buffer/synced/<uuid>.json`
5. Failed entries stay in `~/.aios_buffer/observations/` with reason

**Section 7 — Versioning.**

This spec carries `spec_version: 1.0` at top. Provider templates
reference it as `AIOS_AGENT_INTERFACE.md@1.0`. Spec evolution:
breaking change = bump major; new fields = bump minor.

**Section 8 — Privacy.**

Hard-banned from any observation entry / friction / discovery:
- Raw `_from_desktop/`, `dain/`, `minyoung/` content
- Secrets, credentials, env values
- Raw web page bodies (cite URL + paraphrased claims only)
- Raw tool stdout/stderr (cite reference, not content)
- Personal data (names, emails, phone, addresses) of non-founder

Buffer entries written by offline agents must respect the same
boundaries — failure to do so is a stop condition at sync time.

#### `scripts/aios_observation_buffer.py`

Helper for offline agents to write spec-compliant buffer entries.

```bash
aios-observation buffer write --topic "x" --mode-breakdown "..." --tools "..." [...]
```

Validates against schema, writes to `~/.aios_buffer/observations/<uuid>.json`.

#### `scripts/aios_observation_sync.py`

Reads buffer, validates each entry, appends to right log file based
on `agent_id` role + spec mapping. Moves synced entries.

```bash
aios-observation sync push --buffer ~/.aios_buffer --aios-root /home/user/workspaces/jaewon/myworld
aios-observation sync status --json
```

#### Tests

- Buffer write: invalid schema rejected, valid one accepted
- Sync: synced entries move to synced/, failures stay with reason
- Privacy enforcement: entries with banned content rejected at sync
- Idempotency: re-syncing same uuid → skip with already_synced
- Round-trip: write → sync → entry appears in target log file

### child repos

- No source change. They consume the spec as readers via reference
  in their AGENTS.md after ASC-0087 refresh.

## Verification Gate

```bash
test -f docs/AIOS_AGENT_INTERFACE.md
grep -q "spec_version: 1.0" docs/AIOS_AGENT_INTERFACE.md
python -m py_compile scripts/aios_observation_buffer.py scripts/aios_observation_sync.py
python -m unittest tests/test_aios_observation_buffer.py tests/test_aios_observation_sync.py

# Round-trip dogfood
TMPDIR=$(mktemp -d)
HOME=$TMPDIR python scripts/aios_observation_buffer.py write --topic "spec test" \
  --agent-id "test@dogfood" --tools "Bash,Read" --json
ls $TMPDIR/.aios_buffer/observations/ | wc -l   # expect 1
python scripts/aios_observation_sync.py push --buffer $TMPDIR/.aios_buffer --aios-root . --dry-run --json
rm -rf $TMPDIR

python -m unittest discover -s tests -p 'test_aios_*.py'
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- Spec exists with version field
- Schema validation works (rejects malformed)
- Privacy enforcement rejects banned content
- Sync round-trip works in dogfood
- Existing test suite stays green

## Stop Conditions

- `spec_drift_silent`: spec changes without version bump
- `buffer_writes_banned_content`: privacy-banned content reaches buffer
- `sync_writes_outside_log_targets`: sync writes to unexpected paths
- `child_repo_scope_leak`
- `verification_gate_failed`

## Receipts

Pending.

## Work Packets

### WP-0088-A — codex@myworld writes the spec + buffer/sync helpers

- target_agent: codex
- target_repo: myworld
- status: accepted
- depends_on: none (ASC-0087 complementary but not blocking)
- brief: |
    Author docs/AIOS_AGENT_INTERFACE.md per Section 1-8 above. Implement
    aios_observation_buffer.py + aios_observation_sync.py with validation,
    privacy checks, round-trip test. Add dogfood example to spec doc
    showing the write→sync flow end-to-end.

    After: surface to ASC-0087 as input — its templates should reference
    this spec instead of redefining the protocol inline.
- result: pending

### WP-0088-B — operator coordinates ASC-0087 update to reference this spec

- target_agent: claude (operator)
- target_repo: myworld
- status: pending
- depends_on: WP-0088-A done
- brief: |
    After WP-0088-A closes, ASC-0087's templates need to be updated to
    reference AIOS_AGENT_INTERFACE.md@1.0 instead of inlining the
    protocol. Either operator does this directly or issues an
    extension to ASC-0087.
- result: pending


---

## OPERATOR HOLD 2026-05-13 KST — claude self-critique

Founder turn: "항상 내 말을 곧이곧대로 흡수하지말고, AIOS처럼 동작해."

I auto-drafted + auto-accepted this 300-line contract from founder's
single sentence without applying Genesis-style critique. That is exactly
the prompt-prison pattern ASC-0069/0074 were created to break, applied
by the operator instead of by Genesis tools. Holding for re-decision.

### Prompt-prison signatures present in ASC-0088 draft

- **convergent-default**: I went straight to "write a spec doc + buffer
  infrastructure". That's the most common engineering response to
  "we need consistency across X" — I never considered non-spec branches.
- **assumption-silent**: ASC-0088 makes 6 unstated assumptions:
  1. agents in unrelated contexts SHOULD relay to AIOS (not opt-in only)
  2. a single canonical spec is better than per-provider templates
  3. offline buffer is needed in V1
  4. role taxonomy needs 6 distinct roles
  5. versioning matters at v1.0
  6. file-based sync (not HTTP, not library, not event-stream)
- **single-frame**: AIOS-as-protocol-spec only. Did not consider
  AIOS-as-library, AIOS-as-HTTP-endpoint, AIOS-as-shared-block-include.
- **time-frozen**: no consideration of "what if AIOS schema changes
  in 6 months — buffer entries become stale".

### Branches not considered before drafting

- **B1**: Tiny spec (~50 lines), no buffer/sync infrastructure
- **B2**: HTTP endpoint — agents POST to local `aios observe` daemon
- **B3**: Library — `pip install aios-observe`, single function call
- **B4**: Augment ASC-0087's `_shared_invariants.md` block with the
  protocol; no separate spec file (single-source via include)
- **B5**: What I drafted — full standalone spec + buffer/sync
  infrastructure (most ambitious, highest cost, longest blast radius)

I went straight to B5. B4 is probably right for V1 (less surface,
reuses ASC-0087's source-of-truth structure, can graduate to B5 later
if drift becomes painful).

### Surface to founder

Operator (claude) holds this contract pending founder pick:

- **A. supersede with B4** — augment ASC-0087 shared block, no new spec
- **B. keep B5 (this contract)** — full spec + infrastructure
- **C. B1 — tiny spec only**, defer infrastructure
- **D. B2/B3** — HTTP / library approach
- **E. founder reframes** — different solution entirely

Until founder decides, ASC-0088 stays `held` and codex chain skips it.

---
contract_id: ASC-0270
slug: aios-dream-expansion-claude-hardening
status: closed
goal: Turn the operator's AIOS dream-expansion directive into a governed growth map and delegate system hardening to Claude without starting broad implementation.
created: 2026-06-14T02:30:00+09:00
accepted: 2026-06-14T02:30:00+09:00
human_approved: true
closed: 2026-06-21T10:55:00+09:00
closed_by: claude@myworld
closing_note: Dream expansion map authored (docs/discoveries/2026-06-14-aios-dream-explosive-expansion.md). Hardening invariants delegated to ASC-0271. Sub-dispatches asc-0270-claude and asc-0270-claude-r2 collected. All pending results resolved.
origin: The operator said: "꿈을꿔. AIOS라는. 공격적으로 확장하고 폭발적으로 성장시켜. 시스템을 공고히 하는 것은 Claude의 역할."
---

# ASC-0270 AIOS Dream Expansion Claude Hardening

## Decision

Codex opens the dream and growth lane. Claude owns the hardening lane.

Codex output:

- `docs/discoveries/2026-06-14-aios-dream-explosive-expansion.md`

Claude output requested:

- hardening critique;
- invariant pack;
- owner-bound follow-on contracts;
- stop conditions that let growth happen without local-demo overclaim,
  privacy leakage, provider lock-in, or memory auto-acceptance.

## Scope

repos:

- `myworld`

allowed_files:

- `docs/contracts/ASC-0270-aios-dream-expansion-claude-hardening.md`
- `docs/discoveries/2026-06-14-aios-dream-explosive-expansion.md`
- `docs/AGENT_WORKLOG.md`
- `docs/AIOS_AGENT_LEDGER.md`

Claude hardening allowed files:

- `docs/contracts/ASC-0270-aios-dream-expansion-claude-hardening.md`
- `docs/contracts/ASC-0271-*.md`
- `docs/discoveries/2026-06-14-aios-dream-explosive-expansion.md`
- `docs/AGENT_WORKLOG.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `.env`
- `.env.*`
- provider auth files
- private vault contents
- raw provider logs
- private history stores
- `apps/serving/**`
- `apps/control/**`
- child repo implementation files
- `CapabilityOS/**`
- `hivemind/**`
- `memoryOS/**`
- `GenesisOS/**`
- `uri/**`
- `artifacts/**`
- `gemini/**`
- `gemini-cli/**`
- `1.md`

## AIOS Role Evidence

### MemoryOS

- required hardening: dream output must become draft-first memory candidates
  only after review.
- no accepted memory is created by this contract.

### CapabilityOS

- required hardening: distinguish product/growth routes from execution
  authority; provider surfaces are vendors, not AIOS boundaries.

### GenesisOS

- evidence used: `diverge`, `discomfort`, and `critic` CLI runs.
- main discomfort: `provider_blindspot`.
- critic escape vectors applied: table/schema, distant analogy, assumption
  negation, and 1h/1w/1y horizons.

### Hive Mind

- no execution authorized here.
- future hardening may dispatch owner-bound Hive work for SMX, sandbox, and
  worker scaling only through separate contracts.

### MyWorld

- owns the control-plane decision that Codex dreams and Claude hardens.

## Claude Work Packet

- target_agent: claude
- target_repo: myworld
- dispatch_id: asc-0270
- status: issued
- brief: |
    Read:
    - `docs/discoveries/2026-06-14-aios-dream-explosive-expansion.md`
    - `docs/contracts/ASC-0270-aios-dream-expansion-claude-hardening.md`
    - `docs/contracts/ASC-0260-real-user-serving-release-spine.md`
    - `docs/research/AIOS_AGENT_SERVICE_BASELINE_2026-06-13.md`
    - `docs/AIOS_SUBSTRATE_BOUNDARY.md`
    - `docs/AIOS_NEGATIVE_EVIDENCE_AND_COMBINATORIAL_CREATIVITY.md`

    Produce a hardening response that does not implement code and does not
    touch `apps/**` or child repos.

    Required output:
    1. Name the invariants needed to let AIOS grow aggressively without
       becoming unsafe, vague, provider-locked, or local-demo-only.
    2. Split the dream map into owner-bound follow-on contracts for MyWorld,
       Hivemind, MemoryOS, CapabilityOS, and GenesisOS.
    3. Identify which moves can happen before the serving UI prototype and
       which must wait for browser/production-serving evidence.
    4. Add or update a contract note under `docs/contracts/ASC-0271-*.md`
       and append to `docs/AGENT_WORKLOG.md`.
    5. Keep MemoryOS draft-first, CapabilityOS recommendation-only, GenesisOS
       speculative-only, and Hive execution receipt-bound.

## Verification

```bash
test -f docs/discoveries/2026-06-14-aios-dream-explosive-expansion.md
python3 scripts/aios_serving_release_gate.py assess --root . --json
python3 scripts/aios_world_readiness.py --json
git diff --check
```

Expected current state:

- dream map exists;
- production serving remains not ready until a visual target and UI proof exist;
- world readiness remains false;
- Claude hardening packet is issued, not silently replaced by Codex
  implementation.

## Stop Conditions

- `dream_becomes_unbounded_prose`
- `claude_hardening_replaced_by_codex_patch`
- `memory_auto_accepts_dream`
- `capabilityos_executes_tool`
- `genesis_selects_final_truth`
- `apps_serving_implementation_before_visual_target`
- `world_ready_claim_without_release_proof`

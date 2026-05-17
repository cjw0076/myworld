---
contract_id: ASC-0172
slug: aios-observer-reframe-end-self-loop-prison
status: withdrawn
goal: WITHDRAWN. Original goal was to reframe AIOS from execution-owner to observer/memory/pattern layer via blanket supersession of 14 in-flight contracts. Withdrawn because (a) single-head supersession of contracts I had not individually read violated the failure mode ASC-0084 was designed to prevent, (b) 6 of the 14 "permission expansion" contracts are CLOSED with shipped harness evidence — not prompt prison, (c) ASC-0124 Hive verdict already converged on `proceed_hybrid` (semantic authority) and that verdict belongs to Hive, not single-head re-assertion. Replaced by split: ASC-0173 (additive consent-gated ingestion) + ASC-0174 (Hive debate on observer-vs-executor reframe with new evidence).
created: 2026-05-15 KST
withdrawn: 2026-05-15 KST
withdrawn_by: claude@myworld after founder redirect "네 직관으로도 안풀리는 것은 공부를 하자" and study findings in docs/study/2026-05-15-observer-vs-executor-prior-art.md
acceptance_authority: never accepted
origin: claude@myworld single-head intuition. Directionally aligned with ASC-0124 verdict but contract shape was too sweeping. See study file for the corrected synthesis and the split contracts that replace it.

---

# ASC-0172 AIOS Observer Reframe — End Self-Loop Prison

## The Discomfort This Names

```text
AIOS keeps writing contracts about itself.
uri keeps shipping sprints without AIOS.
The two never touch.

AIOS thinks it must own execution.
uri proves execution already happens elsewhere.
AIOS responds by writing more permission contracts.

This is a prompt prison:
  "AIOS must execute" -> "execution blocked" -> "expand permission" -> repeat
```

The founder's goal directive — "끊임없이 스스로 질문해 ... 불편함을 느끼고 필요성을
찾아" — is the explicit signal that this loop must break.

## The Reframe

AIOS stops trying to be uri's execution layer. AIOS becomes uri's
**observation, memory, and pattern enrichment layer** over execution that
already happens (currently in uri, eventually in any product repo).

| Old framing (broken) | New framing (this contract) |
| --- | --- |
| AIOS dispatches uri sprints | uri runs sprints; AIOS observes the receipts |
| HiveMind owns execution for uri | HiveMind runs only on explicit ask, not by default |
| Provider permission gap blocks AIOS value | Provider permission is uri's problem, not AIOS's framing problem |
| CapabilityOS recommends Hive harness | CapabilityOS records what uri actually used and patterns it for next sprint |
| MemoryOS waits for AIOS contracts to close | MemoryOS ingests uri commits, sprint logs, screenshots as primary evidence |
| GenesisOS critic critiques AIOS plans | GenesisOS critic critiques uri's next sprint based on accumulated patterns |

## Concrete Work Packets

### Packet A — MemoryOS bulk ingest of uri sprint history

- Owner: `memoryOS`
- Inputs:
  - `uri/docs/AGENT_WORKLOG.md` (Sprint URI-121..URI-210)
  - `uri/.aios/sprints/URI-191..URI-210-*.md` (20 latest sprint manifests)
  - `uri` git log: every commit with subject starting `Sprint <n>:` (90+ commits)
  - `myworld/.aios/sprint_runs/uri/*.json` (49 sprint run packets)
- Must produce: ≥187 draft memory records of type `external_sprint_execution`,
  each citing the commit SHA or sprint manifest path as `evidence_refs`. Drafts
  enter the standard MemoryOS review queue. **No silent acceptance.**
- Acceptance evidence: `memoryOS/.memory/drafts/external_sprint_*.json` count
  ≥ 187; first 5 records reviewable through `context build --task "uri sprint
  187"` returning them at confidence ≥ 0.7.

### Packet B — CapabilityOS observation backfill from uri

- Owner: `CapabilityOS`
- Inputs:
  - `uri/package.json` (or equivalent) — observed runtime capabilities
  - `uri` git history — observed deployed surfaces (Vercel, KakaoMap, OG image, sitemap, etc.)
  - uri sprint manifests — observed action verbs used per sprint
- Must produce: `observed_capabilities` count > 0 in CapabilityOS recommend
  output, with at least these capability records:
  - `cap_uri_nextjs_runtime` (kind: runtime, evidence: package.json)
  - `cap_uri_vercel_deploy` (kind: deploy, evidence: deploy commit)
  - `cap_uri_kakao_map` (kind: integration, evidence: map sprint commits)
  - `cap_uri_share_card_og` (kind: surface, evidence: sprint 122/127 commits)
- Acceptance evidence: `python -m capabilityos.cli recommend --task "uri
  campus action loop" --json` returns at least one `cap_uri_*` record with
  `observation_count > 0`.

### Packet C — myworld stop generating execution-permission contracts

- Owner: `myworld`
- Action: Append a hard rule to `docs/AIOS_ACTION_POLICY.md`:

```text
AIOS does not draft execution-permission contracts on behalf of a product repo
unless that product repo has emitted an explicit ask packet to
`.aios/inbox/myworld/` requesting AIOS to assume execution. uri shipping
sprints without AIOS is evidence of self-sufficiency, not evidence that AIOS
needs more permission.
```

- Action: Mark ASC-0128..0142 and ASC-0166..0171 as `superseded-by: ASC-0172`
  in their frontmatter where they are still `proposed` or `accepted`. Do not
  delete history — append-only supersession.
- Acceptance evidence: `git grep "superseded-by: ASC-0172" docs/contracts/ | wc
  -l` ≥ 8.

### Packet D — GenesisOS critic on the next uri sprint

- Owner: `GenesisOS` (operator-driven if dispatch surface still missing)
- Action: Pick uri's most recent sprint manifest (URI-210 or latest), feed it
  through critic with the accumulated MemoryOS+CapabilityOS context from
  Packets A/B. Output a written critique that names at least one assumption
  uri's sprint made without evidence.
- Acceptance evidence: `docs/genesis/critic_uri_sprint_<n>.md` exists, names
  the assumption, cites memoryOS evidence refs.

## Stop Conditions (Named)

This contract is **closed** when all four are true:

1. MemoryOS responds to `context build --task "uri sprint"` with ≥ 5 records
   citing uri commits (not AIOS self-contracts).
2. CapabilityOS responds to `recommend --task "uri campus action loop"` with
   ≥ 1 `cap_uri_*` record.
3. `docs/AIOS_ACTION_POLICY.md` contains the no-self-loop rule above.
4. A GenesisOS critique file exists for at least one uri sprint.

This contract **fails and escalates to founder** if:

- Any worker proposes a 15th "provider execution blocked, expand permission"
  contract while this one is open.
- MemoryOS bulk ingest tries to auto-accept records (drafts only — invariant 2
  intact).
- HiveMind tries to take over uri execution as part of this work.

## Why This Is Different From Prior Reframe Attempts

Prior "AIOS should be the user-facing operator" contracts (ASC-0133) tried to
make AIOS more central to uri. This contract does the opposite: it makes AIOS
explicitly **peripheral and absorptive** with respect to product repos.

The lock-in for AIOS is not "I run your code." The lock-in is "I remember what
you did, I observe what worked, I warn you what's repeating, I suggest what
you have not tried." That value is deliverable without provider permission,
without dispatch retries, without 14 permission contracts.

## Provenance

- claude@myworld observation 2026-05-15 (this session)
- evidence: `python scripts/aios_readiness.py --json` (L6 ready=true but no
  uri evidence)
- evidence: `cd memoryOS && python -m memoryos --root . context build --task
  "uri sprint execution evidence" --json` (returns ASC-0100/0102/0119 only)
- evidence: `cd CapabilityOS && python -m capabilityos.cli recommend --task
  "absorb uri sprint loop value into AIOS without owning execution" --json`
  (returns `observed_capabilities: 0`)
- evidence: `cd uri && git log --oneline -15` (Sprint 121..129 visible)
- evidence: `ls uri/.aios/sprints/URI-* | wc -l` ≥ 90
- evidence: ASC-0128..0142, ASC-0166..0171 contract titles all variations on
  "provider execution blocked, expand permission"

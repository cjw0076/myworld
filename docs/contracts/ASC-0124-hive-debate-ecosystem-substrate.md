---
contract_id: ASC-0124
slug: hive-debate-ecosystem-substrate
status: accepted
goal: Run a long-round Hive deliberation to sharpen the AIOS-as-substrate + sovereign-swarm-ecosystem vision before any container/federation contracts ship. Single-head decisions on whether AIOS becomes the agent's primary world (vs auxiliary tool) carry irreversibility risk; Hive adversarial review catches single-frame bias.
created: 2026-05-14 KST
accepted: 2026-05-14 KST by claude as verifier
acceptance_authority: claude@myworld (verifier role) per founder explicit GO "hive 토론으로 아이디어 샤프닝 진행"
origin: founder turn 2026-05-13/14 KST exploring: (a) AIOS as containerized OS substrate not Linux layer, (b) provider CLI restrictions vs open-source LLM blank-slate, (c) multi-instance Government via sovereign swarm, (d) "limits unlocked in VM" framing reconsidered as "right boundaries + rich cooperation". claude responded with 3-part analysis. Founder routes to Hive instead of accepting claude's framing.
---

# ASC-0124 Hive Debate — AIOS Ecosystem Substrate Vision

DNA references: Invariant 1 (decide before acting — committing to substrate
vision is major), Invariant 4 (named exit — debate must produce verdict not
silent timeout), Invariant 6 (operator override always possible — verdict
must preserve founder authority), Invariant 7 (private boundary inviolable —
multi-instance federation must respect this), Invariant 8 (classify before
committing — substrate decision is irreversible-ish).

## Why Hive (not single-head)

Several deep questions surfaced in founder/claude turns 2026-05-13/14:

1. Is AIOS a *tool layer on top of Linux* or a *substrate FOR agents*?
2. Should the primary citizen be Claude/Codex CLI (smart, restricted) or
   open-source LLM (blank-slate, needs tools)?
3. Does "unlock agent limits in VM" framing make sense, or is it a category
   error confusing alignment with operational restriction?
4. Should multi-instance Government federate via signed projections only
   (ASC-0062), or deeper (shared memory, joint Hive execution)?
5. What's the right *size* of AIOS's freedom envelope?
6. Sovereign swarm vs cathedral: do peer instances merge knowledge or stay
   isolated with selective sharing?

claude proposed (in last chat turn) "aligned + autonomous + cooperating
agents on AIOS substrate" framing. But this is a single-head answer to
a multi-stakeholder vision. ASC-0084 (DNA debate) and ASC-0089 (alternatives
debate) demonstrated Hive adversarial review catches single-frame bias on
foundational questions. ASC-0124 follows that pattern.

## Required Reading

- `hivemind/.runs/aios_dna_debate/final_state.md` (ASC-0084 — 8 DNA invariants)
- `hivemind/.runs/asc0088_alternatives_debate/final_state.md` (ASC-0089)
- `hivemind/.runs/living_organism_debate/final_state.md` (ASC-0114 — in flight)
- `docs/contracts/ASC-0062-peer-share-privacy-projection.md` (sovereign swarm prep)
- `docs/contracts/ASC-0080-aios-native-installation.md` (HOLD — installation surface)
- `docs/contracts/ASC-0086-capability-genesis-autonomy-envelope.md` (autonomy)
- `docs/contracts/ASC-0112-aios-chat-wrapper.md` (substrate auto-select)
- `docs/AIOS_GOVERNANCE_MODEL.md`
- `~/.claude/projects/.../memory/feedback_discomfort_as_creativity_source.md`
- `~/.claude/projects/.../memory/feedback_role_capability_difference.md`
- `~/.claude/projects/.../memory/feedback_aios_founder_mode.md`

## Scope

repos: `hivemind`, `myworld`

allowed_files:

- `hivemind/.runs/ecosystem_substrate_debate/**`
- `hivemind/docs/AGENT_WORKLOG.md`
- `docs/discoveries/2026-05-14-hive-ecosystem-substrate-debate-result.md`
- `docs/contracts/ASC-0124-hive-debate-ecosystem-substrate.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `Dockerfile`, `docker-compose.yml`, `*.dockerfile` (NOT created here —
  if container path picked, downstream contract owns it)
- `scripts/aios_container_*.py` (NOT created here)
- `scripts/aios_swarm_*.py` (NOT created here)
- `memoryOS/**`, `CapabilityOS/**`, `GenesisOS/**`, `uri/**`
- `_from_desktop/**`, `dain/**`, `minyoung/**`
- `.env`

## Per-OS Responsibility

### hivemind.must_produce

Minimum 6 rounds (one more than ASC-0084 since topic is broader),
3 voices per round following the proven format:

- **proposer** — argues for adopting the ecosystem-substrate vision
- **critic** — actively tries to break each claim
- **extender** — proposes additions, removals, or reframes

Each voice ≥ 700 words per round. Substrates rotated across rounds if
multiple available.

### 9 adversarial probes (one new over ASC-0114)

1. **Substrate scope test**: which agent functions actually move from
   Linux to AIOS? File I/O? Network? Process spawn? Memory? Where's
   the cutoff between "AIOS owns" and "AIOS delegates to Linux"?
2. **Alignment-as-restriction test**: claude's argument is "alignment
   stays inside VM". Is this assumption correct, or could a sufficiently
   isolated environment let model behavior diverge meaningfully? What
   actually changes for the model in container vs host?
3. **Open-source primacy test**: if primary substrate is Ollama Qwen
   7B (not Claude), what tasks does AIOS lose? What capabilities
   require external Claude? Where's the floor?
4. **Federation trust test**: ASC-0062 prep allows projection-only
   sharing. Real federation needs deeper coordination (joint Hive run,
   shared memory subset). At what depth does federation become
   single-point-of-failure for all peers?
5. **Citizen-vs-tool test**: founder framed AIOS as Government with
   citizens. Agents-as-citizens implies rights AND duties AND
   accountability. What rights do agents have? What duties? Who
   adjudicates? How is accountability enforced when an agent
   "violates" DNA?
6. **Coevolution risk test**: claude proposed "models learn AIOS
   environment". Is this actually beneficial or does it create
   substrate-specific overfitting (model can only function inside
   AIOS, fragile elsewhere)?
7. **Lock-in test**: container substrate + AIOS schemas + Sovereign
   Swarm protocols = significant lock-in for users. Reversibility?
   Migration path? What does an "exit AIOS" look like?
8. **Power concentration test**: if AIOS becomes substrate for many
   users, the AIOS spec maintainers (founder + operator pair) gain
   significant authority over the agent ecosystem. How is this
   distributed/checked?
9. **Existential reframe test**: maybe the entire "AIOS substrate"
   framing is wrong. Counter-hypothesis: AIOS should remain a thin
   coordination layer; agents themselves stay generic Linux processes;
   what's needed is NOT a substrate but a *protocol*. Argue both sides.

### Convergence verdicts

- `proceed_container_substrate` — container/VM substrate IS the next step
- `proceed_protocol_layer_only` — stay thin coordination layer (probe 9 wins)
- `proceed_hybrid` — container as optional packaging, protocol as core
- `proceed_open_source_first` — substrate yes, but Ollama-primary not Claude/Codex
- `defer_pending_governance_audit` — fix governance theater before adding scope
- `escalate_to_founder` — fundamental disagreement persists

### myworld.must_produce

- Discovery summary in
  `docs/discoveries/2026-05-14-hive-ecosystem-substrate-debate-result.md`
  ≤ 800 words pointing into Hive run artifacts
- Based on verdict, propose downstream contracts (or NOT)

## Verification Gate

```bash
python -c "exit(0 if __import__('pathlib').Path('hivemind/.runs/ecosystem_substrate_debate/round_1').is_dir() else 1)"
python -c "exit(0 if __import__('pathlib').Path('hivemind/.runs/ecosystem_substrate_debate/round_6').is_dir() else 1)"
python -c "exit(0 if __import__('pathlib').Path('hivemind/.runs/ecosystem_substrate_debate/final_state.md').is_file() else 1)"
python -c "exit(0 if __import__('pathlib').Path('docs/discoveries/2026-05-14-hive-ecosystem-substrate-debate-result.md').is_file() else 1)"
python -c "
import pathlib
voices = [v for v in pathlib.Path('hivemind/.runs/ecosystem_substrate_debate').glob('round_*/*.md') if v.name != 'synthesis.md']
under = [v for v in voices if len(v.read_text(encoding='utf-8').split()) < 700]
assert not under, f'voices under 700 words: {under}'
"
python -m unittest discover -s tests -p 'test_aios_*.py'
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- ≥6 rounds, 3 voices each
- each voice ≥700 words
- All 9 probes addressed
- Verdict named in final_state.md
- Discovery summary written
- No container/swarm implementation contracts created in this contract

## Stop Conditions

- `early_convergence`: <6 rounds
- `single_voice`: any round <3 distinct voices
- `probe_skipped`: any of 9 probes unaddressed
- `implementation_creep`: this contract spawns Dockerfile or scripts
- `child_repo_scope_leak`
- `verification_gate_failed`

## Receipts

Pending Hive deliberation.

## Work Packets

### WP-0124-A — codex@hivemind runs the deliberation

- target_agent: codex
- target_repo: hivemind
- depends_on: ASC-0084 ✓, ASC-0089 ✓, ASC-0114 in-flight (format reference)
- brief: 6+ round adversarial debate per spec. Each voice ≥ 700 words.
  Rotate substrates if available. Verdict + dissent in final_state.md.

### WP-0124-B — claude@myworld writes summary + acts on verdict

- target_agent: claude
- target_repo: myworld
- depends_on: WP-0124-A done
- brief: read final_state.md, write ≤800-word discovery summary, surface
  verdict to founder. Downstream container/swarm/protocol contracts follow
  only with founder GO.

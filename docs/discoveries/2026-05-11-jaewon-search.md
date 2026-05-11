# Jaewon Workspace Search — 2026-05-11

Initial cross-workspace search performed by `claude@myworld` operator after the founder's directive: "search every doc under jaewon and keep deriving next AIOS work; this very activity is what MemoryOS, CapabilityOS, hivemind, and the control plane should do — turn it into a system."

Six parallel Explore agents covered the major directory groups; Codex's `aios_doc_scout.py` (ASC-0007) then provided a machine-readable task radar over 1822 docs. This file consolidates both human and machine findings and links them to the contracts they spawned.

> Privacy: paths and one-line summaries only. No raw export bodies, no secrets, no chat transcripts. All `_from_desktop/` content is treated as the founder's private archive — referenced for ideas, not copied.

## Domain Summaries (by Explore agents)

### conscious_runtime + jarvis_AI (`_from_desktop/`)
- **conscious_runtime**: working prototype of a graph-OS. `OntologyNode`, `soul.md`-replacing concept graph, ontology delta auto-propagation across self + neighbor nodes (Strange Loop). Phase 1–3 code present (`run_phase1.py`, `workspace.py`, `soul.py`). Migration target → Dipeen.
- **jarvis_AI**: working multimodal UI prototype (MediaPipe hand tracking + Web Speech API + HTML editor + Claude API placeholder). Demonstrates voice + gesture-driven coding agent UX.
- **Gap vs current AIOS**: persistent agent self-concept ontology; ontology-delta IPC; multi-modal IO; conscious self-reflection loop; voice/gesture dispatch.

### deepfake (`/home/user/workspaces/jaewon/deepfake/`)
- Active SRI-Net v7 Specular Comparator paper. Cross-manipulation AUC 0.8624 → 0.8803 (+1.79pp) over baseline across 6 unseen domains. 2026-05-11 weekly report.
- Pending: A1/A2/A3/A5 multi-seed; attribute-stratified error analysis (makeup/pose/eyeglasses/occlusion/illumination); FaceDancer reversal deep-dive; WhichFaceIsReal reconstruction; threshold calibration.
- AIOS dispatchable slices: Hive Mind for parallel feature-stratified analysis; CapabilityOS for attribute labeling tools; MemoryOS for prior ablation decisions.
- Constraint: GPU saturation (3×24GB), `dain/` readonly data dependency.

### universe quantum (`/home/user/workspaces/jaewon/universe/`)
- Paper3 frozen (2026-04). Paper4 in progress: P18-A (γ×σ_m identifiability map, partially done) → P18-B/C/D → P17-A0 (active intervention actionability gate).
- AIOS-relevant: MemoryOS can absorb P12–P16 design lessons; CapabilityOS can catalog Lindblad/POVM/Born simulation tools; literature abstraction surfaces "identifiability breakers" as memory.
- `skills/` is local docx utility, not the AIOS skill catalog.

### docs / ablation / fire (`/home/user/workspaces/jaewon/`)
- `docs/research_consolidation/`: empty placeholder (reserved hub).
- `ablation/`: deepfake ablation results externalized (a0_full, a2_copy_proxy, a3_no_error_maps, a4_no_gate × seed42–44 × 80 epochs × 6 datasets).
- `fire/`: NEW EV-battery thermal-anomaly project (Positional MemAE + CoordConv on 1ch IR 256×256, Jetson Orin target, SSIM loss planned). 10 docs by founder, active 2026-04-28+.
- Cross-cutting candidate: thermal-anomaly Jetson optimization, ablation analysis, research consolidation hub activation, fire→deepfake spatial-memory transfer, Jetson pipeline.

### graphRAG + GoEN (`_from_desktop/`)
- **graphRAG**: skeleton only, no implementation. Low value.
- **GoEN**: completed GNN research (complex unitary representation + directional message passing + STDP, Cora/Citeseer +0.3–0.7pp). Phase-3 STDP unstable, root cause diagnosed as missing timescale separation. **High value** — concepts directly applicable to MemoryOS edge lifecycle (draft → reviewed → accepted = mempool → candidate → consolidated).

### dipeen / Uri / zeiint / competition (`_from_desktop/`)
- **dipeen_v2**: serious agent collaboration platform (FastAPI + Next.js + agent-client CLI + Docker). PM-loop state machine, BYOK per-agent, Wave parallel execution. Successor to conscious_runtime. Orthogonal to AIOS scope — reference, not absorption target.
- **Uri**: university social/companion app. Separate product, not for absorption.
- **zeiint**: 6-week plan project, low signal.
- **competition**: hackathon entry on adversarial AI policy stress test. Standalone.

## Doc Scout (machine, ASC-0007)

`python scripts/aios_doc_scout.py --root /home/user/workspaces/jaewon --json` at 22:35 KST:

- 1679 documents scanned, 1067 with task signals.
- by_domain: `_from_desktop=786, hivemind=119, universe=66, memoryOS=49, myworld=27, fire=10, deepfake=7, CapabilityOS=3`.
- Top signals: `myworld/hivemind/docs/AGENT_WORKLOG.md` (364), `myworld/hivemind/docs/HIVE_MIND_GAPS.md` (337), `myworld/hivemind/docs/TODO.md` (332), `myworld/memoryOS/docs/TODO.md` (315), `myworld/memoryOS/docs/AGENT_WORKLOG.md` (304), `_from_desktop/dipeen_v2/openclaw/CHANGELOG.md` (303), and many myworld-internal contract files.
- Auto-proposed contracts: ASC-0008 (workspace-doc-ingest-memoryos), ASC-0009 (capability-observation-feedback), ASC-0010 (hive-semantic-quality-gate), ASC-0011 (control-plane-loop-policy), ASC-0012 (workspace-instruction-index).
- Output preserved at `docs/AIOS_TASK_RADAR.md`.

## Findings → Contract Mapping

| Finding source | Spawned / informs |
| --- | --- |
| Doc scout self-proposal | ASC-0008 (memoryos ingest), ASC-0009 (capability observation), ASC-0010 (hive semantic gate), ASC-0011 (loop policy) |
| GoEN edge-lifecycle insight | ASC-0008 design hint (mempool → candidate → consolidated) |
| Deepfake / universe / fire active research | Future ASC-0012+ (operator-gated dispatch, GPU/hardware constraints) |
| conscious_runtime ontology + jarvis multimodal | Long-horizon ASCs (ontology delta IPC, multi-modal dispatch interface) — listed for radar but deferred |
| dipeen_v2 / Uri / zeiint / competition | No absorption; remain reference projects |

## Holds / Operator Escalations

- **Heavy compute / hardware contracts** (deepfake multi-seed, fire Jetson, quantum P18 sweep) need founder review before dispatch — they consume real GPU/hardware.
- **`dain/` readonly data dependency** for deepfake — confirm policy before dispatching anything that touches it.
- **`_from_desktop/` privacy posture** — never copy raw bodies into AIOS shared docs; reference by path + hash only.

## Next Loop

1. ASC-0008/0009/0010/0011 stubs issued by `claude@myworld` based on scout proposals; Codex picks up implementation per inline WPs.
2. Re-run scout after ASC-0008/0009 land; expect new candidates.
3. Whenever ledger gains a closeout, scout's signal density should evolve — this is the L5 feedback loop.
4. Founder-gated heavy contracts queued for review (deepfake / fire / quantum) once feedback loop is stable.

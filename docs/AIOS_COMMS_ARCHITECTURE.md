# AIOS Communication Architecture — researched, not asserted

**Built**: 2026-06-09 (claude@myworld), from two cited research streams (foundational
ACL/Contract-Net/actor/blackboard/speech-acts + modern A2A/MCP/AGNTCY + multi-agent
communication research) reconciled with the code-teardown (codex/gemini/omo §comms)
and AIOS's own pieces. Founder directives: "소통방식을 연구하자", "토큰을 local로
치환", "AIOS가 대화하는 방식의 혁신". Sources at bottom.

## The thesis (the research's strongest, most counter-intuitive finding)

**The biggest communication win is LESS communication, not better communication.**
AgentPrune (ICLR 2025) cut inter-agent tokens 28–73% (cost $43.7→$5.6, accuracy
held) just by *pruning* the message graph — and the sparser graph also *defended
against adversarial messages*. "Talk Isn't Always Cheap" (2025): extra debate rounds
/ more debaters *degrade* accuracy via sycophancy, persuasion-over-truth, and
agreement cascades; majority voting explains most of debate's apparent gain. Sparse
topologies beat all-to-all. Multi-agent chatter costs ~15× a single call.

So the founder's two asks — cut tokens, and innovate how AIOS talks — have ONE
answer: **talk less; when you do, talk dense, sparse, commitment-bearing, calibration-
carrying, and prefer verification over debate.** This also names this session's own
failure modes (the agent over-reported and showed agreement-bias — exactly the
sycophancy/over-communication the research warns against).

## What the foundations teach (and the two traps to avoid)

- **Speech-act envelope** (KQML/FIPA): separate *intent* (performative) from *payload*
  from *transport*. AIOS's packets already echo this.
- **Trap 1 — mentalistic semantics** (Wooldridge: why FIPA-ACL failed): never define a
  message's meaning by another agent's beliefs/intentions — unverifiable externally.
  **AIOS fix: meaning = observable COMMITMENT** (a ledger entry, a receipt), not inner state.
- **Trap 2 — heavyweight ontology + dialect fork** (KQML/FIPA adoption killer): keep
  ONE small fixed performative set; never let codex@hivemind grow its own dialect.
- **Contract Net** = AIOS's `contract→dispatch→result→ledger`, minus the auction (route
  to the OS that owns the capability — no bidding).
- **Actor model** = `.aios/inbox/<repo>/` as mailboxes, async, no shared mutable state.
- **Blackboard/tuple-space** = the `.aios` bus, but kept **append-only with provenance**
  (the ledger), not a mutable scratchpad.
- **Human channel** (speech-acts + Clark's grounding + adjustable autonomy): choose
  *act / report / ask* by **reversibility** under the **principle of least collaborative
  effort** — terse, decision-shaped messages for a "GO/HOLD" founder; spend the human's
  bandwidth only where grounding genuinely requires it.

## The architecture (5 layers, each grounded)

1. **Envelope (`aios_packet`)** — adopt **A2A field names** (`task_id`/`context_id`/
   terminal states `done|failed|canceled`) so the bus is bridge-compatible with the
   dominant agent-to-agent standard for ~free (it's already isomorphic: call_id↔taskId,
   trace_id↔contextId, done/blocked/timed_out↔terminal/interrupt states). Performatives
   = a small fixed FIPA-derived set + **AIOS's novel `challenge`** (GenesisOS dissent —
   no existing ACL has "here is the non-obvious reading / I diverge"). Meaning is
   commitment-based (cite the ledger/receipt), never mentalistic.
2. **Transport** — actor mailboxes over the append-only provenance blackboard. Every
   packet: `call_id` + `parent_id`/`context_id` (correlation + lineage = DNA #5),
   `wait_status→timed_out` (named exit = DNA #4). (`aios_packet`, built.)
3. **Discipline — SPARSE + commitment + calibration** (the thesis, encoded):
   - **reference-passing, not content** (`payload_ref`; Anthropic subagents return
     *compressed findings*, not transcripts) — token cost ~constant in payload size.
   - **a sparsity gate**: don't send redundant/low-novelty `inform`; control messages
     (`ask/blocked/failure/done`) always pass. (AgentPrune: prune redundancy.)
   - **calibration-carrying**: every claim carries `confidence` (from `aios_stakes`) +
     `evidence_ref` (provenance). Trust-weight a message by sender calibration.
   - **verification over debate**: prefer an independent second-substrate check + majority
     over deliberation rounds (debate degrades via sycophancy).
4. **Human channel** — silent by default; surface only on reversibility-gated triggers
   (`block` = decision needed, `done` = milestone, `anomaly` = calibration says likely
   wrong). Calibration-explicit, terse register, expand-on-demand (the 85%-lean-brief
   pattern). Fixes this session's over-report + over-ask.
5. **Token→local membrane** — wrap the frontier core in local compute: local LLM
   compresses everything entering the frontier context (tool results, files, logs) and
   expands frontier output for the human; the **frontier only ever exchanges dense
   structured packets**. Local-first cascade (`aios_ceiling` inverted: default local,
   escalate on low-confidence). Substitutes frontier tokens with free 5090 FLOPs.

## The one trap to hold (applies to AIOS *and* to the operator agent)
**Over-communication is net-negative.** Do not add agent-to-agent debate rounds or
all-to-all chatter; do not over-report to the founder; do not let agreement cascade.
Keep talk sparse, authority-gated, verification-biased. "More agents/messages = better"
is empirically false.

## Build order (lean — the research warns against over-engineering comms)
1. Upgrade `aios_packet`: FIPA/A2A-aligned performatives (+ `challenge`), commitment
   semantics, `confidence`/`evidence_ref`, a `should_communicate` sparsity gate, A2A
   bridge naming. *(this commit)*
2. Wire calibration into outgoing packets (`aios_stakes` → `confidence`).
3. Local-membrane compressor for tool-results entering the frontier context (biggest
   token sink) — local-first.

## Sources
Foundational: KQML (UMBC), FIPA-ACL + Contract Net (fipa.org; arXiv 2505.02279),
Wooldridge verifiability (Springer 10.1023/A:1010016503852), Actor model (arXiv
1008.1459), Hearsay-II/Linda, speech acts + Clark grounding, mixed-initiative/adjustable
autonomy. Modern: A2A spec (a2a-protocol.org), MCP (modelcontextprotocol.info), AGNTCY
ACP, Anthropic multi-agent research, AgentPrune "Cut the Crap" (arXiv 2410.02506),
"Talk Isn't Always Cheap" (arXiv 2509.05396), Q-KVComm (2512.17914), latent-space
agent comms (2511.09149). (Full URLs in the research receipts.)

---
name: aios-decide
description: >-
  Run the mandatory AIOS 4-OS query ritual BEFORE any non-trivial operator
  decision (new/supersede contract, vision pivot, strategy choice, cross-repo
  dispatch). Calls MemoryOS + CapabilityOS + GenesisOS + Hive and forces you to
  cite their answers in your reasoning. Exists because the self-observation log
  shows this ritual is the single most-repeatedly SKIPPED step ("still skipped;
  gap signal repeating") — packaging it as one invocation stops the skip.
---

# AIOS 4-OS Decision Ritual

CLAUDE.md mandates: before any non-trivial decision, invoke all 4 OS and cite
their answers. In practice agents skip it under time pressure (see
`docs/AIOS_CLAUDE_SELF_OBSERVATION_LOG.md` — "4-OS query … 이번도 skip (반복
gap)"). This skill makes the ritual a single repeatable surface so it is not
re-derived or silently dropped.

## When to use

**Mandatory before:**
- Drafting / accepting / superseding an ASC contract
- Any vision-level or strategy pivot
- Choosing between ≥2 non-trivial approaches
- Cross-repo dispatch that changes shared state

**Do NOT use:** trivial edits, lint, typo fixes, reading/searching, a decision
already grounded earlier this session.

## Workflow

Run all four; do not stop early. Prefer the `aios` MCP tools (they wrap the OS):

1. **MemoryOS — recall, don't assume.** `aios_retrieve(query=<decision>)`.
   Cite the `trace_id` and what prior accepted memory says (or "null →
   no prior memory", which is itself a finding — see [[aios-memory-propose]]).
2. **CapabilityOS — is there a specialist?** `aios_route(task=<decision>)`.
   Cite the top route + score; if a helper fits, prefer it over hand-work.
3. **GenesisOS — is this reasoning prison'd?** `aios_challenge(text=<your draft
   thesis>)`. Cite the prison signatures + escape vectors and ACT on them
   (restate as table/schema, name+negate top-3 assumptions, compare 1h/1w/1y)
   before committing.
4. **Hive — verify the plan.** `python scripts/aios_invoke.py --goal "<chosen
   action>" --plan-only --json`. Cite the invocation receipt.
5. **Record the ritual token** so enforcement lets the decision land:
   `python scripts/aios_ritual_gate.py record --note "<decision>"`. The
   PreToolUse gate (aios_guard_hook.py) blocks creating a contract
   (`docs/contracts/ASC-*.md`) until a fresh (<60min) token exists — this is
   what makes the ritual enforced, not advisory.

Then state the decision with the four citations inline.

## Output template

```markdown
**4-OS:** memory(trace=…): <recall or null> · route: <top cap@score> ·
genesis: <signatures → what I changed> · hive(receipt=…): <plan ok?>
**Decision:** <one line> — because <grounded reason>.
```

## Hard rules

- **Never skip a leg silently.** If you skip one, say which and why — a named
  skip is a finding; a silent skip is the repeated mistake this skill exists
  to kill.
- **A null/empty OS answer is signal, not noise.** Record it (feed
  `aios_observe`) — e.g. retrieve-null on a product task = domain-coverage gap.
- **Genesis findings must change the artifact**, not just be quoted.
- Carry reversible risk decisively (decide, don't escalate); escalate only
  irreversible + privacy. See memory feedback_carry_risk_decisively.

## Related

- `CLAUDE.md` "Self-integrate with the 4 OS" · memory feedback_4os_query_pattern
- [[aios-memory-propose]] (write a recall result back so next retrieve ≠ null)
- [[absorption-probe]] (measure whether an OS leg actually adds value)

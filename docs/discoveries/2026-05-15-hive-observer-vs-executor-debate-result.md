# Hive Observer-vs-Executor Debate Result

Source: `hivemind/.runs/observer_vs_executor_debate/final_state.md`
Contract: ASC-0174
Verdict: `proceed_authority_routed_management_plane`

ASC-0174 completed 6 rounds with 18 proposer/critic/extender voice artifacts.
It rejects the binary "AIOS is observer" vs "AIOS is executor" frame. The
stronger frame is that AIOS owns the **system calls of long-running agentic
work**: observe, ingest, retrieve, route, challenge, execute, refuse,
override, promote, and close.

AIOS is active at the operating layer, but bounded at the product artifact
layer.

- AIOS-owned records get pre-fact gates.
- AIOS participation can be refused before unsafe work proceeds through AIOS.
- Product-owned records are observed post-fact unless the repo delegates a
  pre-fact hook.
- Dangerous execution remains an explicit opt-in system call with operator
  grant and receipt, not the default identity of AIOS.

The final authority axes are:

1. `record_authority`: who owns the durable artifact.
2. `schema_authority`: who designed the format or UI shaping the artifact.
3. `participation_authority`: whether AIOS assists, routes, summarizes,
   packages, publishes, or improves an action.
4. `override_authority`: who can force a route despite a hold, with what
   ceremony and receipt.

Interpretation:

The repeated permission-chain contracts were negative evidence for a missing
authority model. Retain contracts that harden AIOS-owned records and provider
receipts. Rewrite product-execution expansion as delegated hooks or
participation refusal. Withdraw raw permission expansion that does not name
record authority, stop condition, fallback, and receipt.

The verdict preserves founder ambition without making `dangerous` the AIOS
identity. A sovereign AI operating layer starts with jurisdiction, records,
visible process, institutional memory, and opt-in execution authority.

Immediate downstream work:

- Add authority axes and system-call terms to AIOS shared language/DNA.
- Surface authority/system-call labels in the Control UI.
- Store MemoryOS negative evidence: failed providers, rejected ingests,
  privacy holds, stale memories, and wrong routes.
- Teach CapabilityOS bad-tool and fallback-quality routing.
- Make GenesisOS discomfort gates part of close.
- Make Hive envelopes record provider route, failure category, fallback,
  verification, and result receipt.

This verdict should guide the next interface work: users should see AIOS
observe, retrieve, route, challenge, execute, refuse, and close with evidence,
not only see logs after the fact.

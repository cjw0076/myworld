# AIOS Base Architecture Audit

Generated: 2026-05-14 13:16 KST

This document checks whether AIOS has a solid base before more feature
contracts are added. It is an audit of the operating layer, not a product
marketing description.

## Purpose

AIOS exists to turn one user goal into a governed, inspectable, memory-bearing
operating loop around provider CLIs and local models.

The safe claim is:

```text
AIOS does not replace provider CLIs; it turns them from one-shot executors into
a persistent, governed, inspectable, memory-bearing operating loop for
long-running agentic work.
```

The base should optimize for:

- continuity across sessions;
- ownership and scope control across repos;
- memory reuse and provenance;
- capability/tool/provider routing;
- execution receipts and verification;
- user-visible progress and checkpoint decisions;
- learning from both success and failure.

## Inputs

AIOS currently has these input classes:

| Input | Entry point | Expected artifact |
| --- | --- | --- |
| direct conversation | `POST /api/chat`, `scripts/aios_chat.py` | `.aios/chat/<conversation>/`, `.aios/invocations/chat-*` |
| end-user goal | `POST /api/session`, `scripts/aios_invoke.py --goal` | `.aios/invocations/<id>/session_envelope.json` |
| ask/contract seed | `POST /api/ask`, `scripts/aios_ask.py --draft-contract` | `.aios/asks/<id>/`, proposed contract seed |
| accepted contract | `docs/contracts/ASC-*.md` | dispatch state and repo inbox packets |
| repo work packet | `.aios/inbox/<repo>/*.json` | child repo execution result |
| provider/agent observation | `.aios/observation_buffer/<agent_id>/*.json` | route to MyWorld, Hive, MemoryOS, CapabilityOS, or GenesisOS |
| memory draft/review | MemoryOS CLI/import path | reviewed memory object and retrieval trace |

The base input invariant is: raw user language must become a typed artifact
before execution. Chat responses may stay lightweight, but governed work must
cross a `session_envelope` or accepted contract boundary.

## Outputs

AIOS should produce different outputs for different authority levels:

| Output | Meaning |
| --- | --- |
| chat turn response | user-facing answer, not execution authority |
| session envelope | role-prepared execution context, still plan-only |
| capability route | recommendation-only tool/provider/fallback plan |
| memory context pack | accepted context plus RetrievalTrace provenance |
| genesis branches | speculative alternatives and discomfort signals |
| hive execution plan | executor assignment and verification gate |
| dispatch packet | bounded repo-local work order |
| result packet | execution/verification receipt from owner repo |
| ledger/worklog entry | durable cross-agent state transition |
| memory draft | learnable record requiring review before acceptance |
| control snapshot | visual state for user/operator inspection |

The base output invariant is: completion cannot be only a chat message. It
needs at least one receipt, trace, result packet, ledger entry, or explicit
checkpoint.

## Behavior Loop

The desired base loop is:

```text
1. Intake
   User says a goal or asks a question.

2. Classify
   Gate decides: chat, current-info route, contract seed, or governed work.

3. Prepare
   MyWorld creates a plan-only invocation:
   GenesisOS branches, MemoryOS context, CapabilityOS route, Hive plan.

4. Preflight
   If a route needs permission, Hive converts it into an operator checkpoint.

5. Contract
   MyWorld narrows owner repos, files, verification, and stop conditions.

6. Dispatch
   MyWorld writes repo-local packets under `.aios/inbox/<repo>/`.

7. Execute
   Hive Mind or the owning repo agent acts inside the owning repo.

8. Verify
   Tests, smoke commands, receipts, or review gates prove the work.

9. Learn
   MyWorld collects results, MemoryOS records draft memories, CapabilityOS
   records route observations, GenesisOS records discomfort/branch signals.

10. Advance or stop
    Round controller either proposes the next bounded action or holds with a
    named reason.
```

This loop is stateful, not a fixed linear pipeline. Some simple chat turns may
stop after classify/prepare. Implementation work must pass through contract,
dispatch, verify, and learn.

## Infrastructure

The base infra is local-first and file-backed:

```text
myworld/
  bin/aios
  scripts/aios_launcher.py
  scripts/aios_invoke.py
  scripts/aios_chat_router.py
  scripts/aios_dispatch.py
  scripts/aios_child_watcher.sh
  scripts/aios_round_controller.py
  scripts/aios_monitor.py
  scripts/aios_local_app.py
  apps/control/
  .aios/
    invocations/
    inbox/<repo>/
    outbox/<repo>/
    state/
    chat/
    asks/
```

Child repos own their implementation surfaces:

```text
hivemind/      execution, provider wrapping, permission preflight, verification
memoryOS/      retrieval, context packs, provenance, memory draft/review
CapabilityOS/  capability maps, recommendations, fallback and unblock routes
GenesisOS/     divergence, semantic alignment, discomfort and invention seeds
```

The native install design is user-space only:

- `~/.local/bin/aios`
- `~/.config/systemd/user/aios.service`
- optional desktop autostart entry

No base infra should require writing provider credentials, raw private exports,
or child repo internals from MyWorld.

## Current Evidence

Observed during this audit:

- `scripts/aios_invoke.py --goal "base architecture audit smoke" --json`
  passed all role surfaces and produced a session envelope.
- MemoryOS returned 10 selected memory ids and a RetrievalTrace id for the
  audit smoke.
- CapabilityOS returned recommendation-only routes.
- GenesisOS returned five speculative branches with `authority=speculative_only`.
- Hive plan assigned execution owner to `hivemind` and `default_executor=codex`.
- `scripts/aios_readiness.py --json` reports `L6 repeatable` after ASC-0168
  was closed and pending packets were collected.
- `scripts/aios_monitor.py assess --json` reports `health=attention`, not
  `watch`, because child repos still have uncommitted work.

## Base Verdict

The base is conceptually coherent and now reaches `L6 repeatable` by the
readiness script, but it is not yet product-stable.

The strongest parts are:

- typed invocation artifacts;
- contract/dispatch/result packet loop;
- monitor and readiness checks;
- local control app and chat surface;
- explicit repo ownership boundaries;
- provider failure classification and Hive permission preflight.

The weak parts are:

1. Dirty child repo state still blocks clean watcher execution.
2. MemoryOS context packs often surface ids/traces more than rich useful
   context.
3. CapabilityOS can recommend and propose unblock routes, but broad web/API/MCP
   discovery is not yet a strong visual routing layer.
4. GenesisOS can generate branches and discomfort candidates, but those signals
   do not yet strongly change contract priority.
5. The chat Gate exists, but current-info/tool routes still need real adapters
   before it feels provider-grade.
6. There are many contracts; the base needs fewer canonical operating specs and
   stricter close/commit hygiene.
7. Native always-on install is designed, but should be dogfooded as a user
   service before calling it production infra.

## Required Base Invariants

Before AIOS claims a product-grade base, these must be true:

- One command can show health, active goal, pending checkpoints, and next work.
- One UI can show what each OS did for the current turn.
- A governed goal can be resumed without chat context.
- A provider failure produces a classified fallback or checkpoint, not silence.
- MemoryOS records both useful successes and useful failures.
- CapabilityOS can say "bad tool / bad route" with evidence, not only
  recommend good tools.
- GenesisOS discomfort can change the next work order, not just decorate it.
- Hive Mind remains the execution owner for provider/tool work.
- MyWorld does not become a hidden worker that patches every repo.

## Recommended Next Order

1. Close dirty child repo state through repo-local review/commit or explicit
   hold records.
2. Harden the Gate current-info route so questions like weather cannot be
   answered by a cheap local turn without a real current-info adapter.
3. Upgrade MemoryOS context packs from id lists to compact, cited, user-useful
   memory summaries.
4. Add a CapabilityOS visual search/router surface for web/API/MCP/skill
   discovery, with negative tool evidence.
5. Wire GenesisOS discomfort scores into goal evolution and contract priority.
6. Dogfood the native always-on service and control app as the primary AIOS
   interface.


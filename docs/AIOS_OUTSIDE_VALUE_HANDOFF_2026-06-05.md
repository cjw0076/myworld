# Outside-Value Handoff — Deadline Copilot (control-plane proof → product)

2026-06-05, claude@myworld. The override goal ("AIOS creates value OUTSIDE
itself") now has a working **control-plane proof**. This is the bridge to making
it a real product — which belongs to uri (product) + hivemind (execution), not
the control plane. Decision-ready for the founder.

## What exists now (proven, in myworld, tested + pushed)

A complete value loop on the **local substrate** (free, private, no provider lock):

| stage | script | what it does |
|---|---|---|
| produce | `scripts/aios_deadline_copilot.py` | assignments → dated action plan |
| resilient | `scripts/aios_substrate_router.py` | failover across local models (churn-survival) |
| verify | (in copilot) | deterministic date-check — LLM plans, code verifies |
| quality | (in copilot) | GenesisOS critique gate |
| provenance | receipt JSON | substrate served + routing trail + gates |
| measure | `scripts/aios_value_ledger.py` | verify-pass rate, substrate mix, churn events |

Run: `python scripts/aios_deadline_copilot.py` (uses sample assignments).

## What productionization needs (uri + hivemind — NOT control-plane)

1. **Real input** — replace the hardcoded sample with a student's actual
   assignments: an LMS/이타임/캘린더 adapter or manual entry in the uri app.
   (Clean-room sourcing rules apply — see uri festival-data HARD RULE.)
2. **Per-student memory** — store plans/outcomes in MemoryOS per student so the
   copilot personalizes over time (the "나를 아는 에이전트" thesis in uri goal.md).
3. **Delivery surface** — uri app screen + push/email reminders (codex UI flow).
4. **Execution** — run generation through the hive harness (it already detects
   the local runtime) so it's scheduled/receipted, not a one-shot script.
5. **Trust loop** — surface the value-ledger metrics to the student (completion,
   missed-deadline prevention) per panel #3.

## Founder decision points

- **GO/HOLD** on productionizing Deadline Copilot in uri as the first real
  outside-value feature.
- Input source priority (manual entry first vs LMS/캘린더 adapter)?
- Hosted-substrate tier for quality (add codex/gemini to the router) vs
  local-only for cost/privacy?

Until directed, the control-plane proof stands closed and pushed; no product
code was written in child repos (ownership boundary respected).

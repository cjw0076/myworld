# AIOS Close Condition

ASC-0121 makes contract closeout a classified assertion instead of a paperwork
state flip.

## Close Types

- `closed_goal_met`: pass criteria were evaluated at close time and no unmet
  criterion remains.
- `closed_partial_with_followup`: at least one criterion remains unmet, and a
  named follow-up `ASC-NNNN` owns the residual work.
- `closed_goal_unmet_documented`: the operator is intentionally closing a
  failed contract with a recorded reason.

Plain `closed` remains the frontmatter lifecycle status for compatibility, but
the release event must carry the strict-close evidence when unmet criteria
exist.

## Evaluator

Run:

```bash
python scripts/aios_close_condition.py docs/contracts/ASC-0110-memoryos-retrieval-broken.md --json
```

The evaluator reads a contract, extracts `Pass criteria:` bullets, evaluates
what can be checked safely from local artifacts, and returns:

```json
{
  "contract_id": "ASC-0110",
  "met": 2,
  "unmet": 2,
  "manual": 0,
  "recommended_close_type": "closed_partial_with_followup"
}
```

Every criterion becomes exactly one of `met`, `unmet`, or `manual`; silent
skips are a stop condition.

## Dispatch Enforcement

`scripts/aios_dispatch.py release` calls the evaluator for the created
contract when the contract file is already in `status: closed`.

If unmet criteria exist, release is held unless one of these is supplied:

```bash
python scripts/aios_dispatch.py release \
  --dispatch-id asc-0121 \
  --reason "verified" \
  --close-type closed_partial_with_followup \
  --followup-asc ASC-0122
```

or:

```bash
python scripts/aios_dispatch.py release \
  --dispatch-id asc-0121 \
  --reason "documented_failure" \
  --close-type closed_goal_unmet_documented
```

Emergency bypass exists only for operator recovery:

```bash
python scripts/aios_dispatch.py release \
  --dispatch-id asc-0121 \
  --reason "operator_emergency_reason" \
  --operator-override-strict-close
```

The bypass writes `strict_close_override` to `.aios/state/dispatches.jsonl`.

## Retro Baseline

Run:

```bash
python scripts/aios_retro_close_classify.py --json
```

The retro classifier labels existing closed contracts without reopening or
editing them. Its output is a governance baseline, not an automatic verdict.

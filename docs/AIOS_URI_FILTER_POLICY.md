# AIOS Uri Filter Policy

Uri is a child product repo. It can produce AIOS-relevant operating signals,
but most Uri markdown is product-internal and should not automatically become
control-plane memory or task radar input.

## Outcomes

- `aios_relevant`: the file can flow into `aios_doc_scout.py` as a normal
  signal candidate.
- `uri_internal`: the file is counted in the scout receipt and skipped.
- `operator_review`: the file is skipped and a path-level receipt is written
  under `.aios/uri_review_queue/`.

The filter never writes to `uri/`.

## V1 Rules

Denylist wins before whitelist:

- `uri/products/**`
- `uri/hive/packets/**`
- `uri/research/**`
- `uri/capabilities/**`
- `uri/memory/**`

Whitelisted AIOS-relevant files:

- `uri/docs/URI_NORTHSTAR.md`
- `uri/docs/AGENT_WORKLOG.md`
- `uri/docs/MEMORY_POLICY.md`
- `uri/docs/AIOS_*.md`
- `uri/docs/CAPABILITY_MAP.md`
- `uri/docs/LEGAL_ETHICAL_GUARDRAILS.md`
- `uri/AGENTS.md`

Other `uri/docs/*.md` files become `aios_relevant` only when they contain at
least two AIOS shared-language terms such as `contract`, `dispatch`, `draft`,
`capability`, `hive`, `memory`, `MemoryOS`, `CapabilityOS`, or `AIOS`.

All other Uri markdown becomes `operator_review`.

## Operator Promotion

To promote a recurring review item, update this policy and
`scripts/aios_uri_filter.py` in a later contract. Do not promote by editing
the generated `.aios/uri_review_queue/*.md` receipt.

## Privacy Boundary

Review receipts store only source path, normalized Uri path, outcome, reason,
and matched shared-language terms. They do not copy source document bodies.

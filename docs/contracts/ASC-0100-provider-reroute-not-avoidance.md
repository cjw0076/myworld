---
contract_id: ASC-0100
slug: provider-reroute-not-avoidance
status: closed
goal: Make child-repo execution reroute across provider CLIs and local substrate when auth, PIN, or rate-limit backpressure blocks a worker, while preventing unverified local output from being accepted as final work.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by Codex under founder direction
closed: 2026-05-13 KST
origin: founder correction 2026-05-13 KST - "회피가 아니라 우회를 하도록 해야지"
human_approved: true
---

# ASC-0100 Provider Reroute, Not Avoidance

## Why Now

ASC-0099 dogfood exposed the real failure chain:

- Codex noninteractive CLI blocked on PIN/auth.
- Claude CLI blocked on provider limit/backpressure.
- Gemini CLI blocked on missing auth method.
- Child watcher previously stopped after one fallback instead of continuing the
  route.

This is not an implementation failure inside MemoryOS, CapabilityOS, or Hive.
It is an AIOS runtime routing failure. A blocked provider should not collapse
the contract loop. CapabilityOS should help find another route, and the watcher
should continue until a usable provider is found or all routes are exhausted.

## Scope

repos:

- `myworld`

allowed_files:

- `docs/contracts/ASC-0100-provider-reroute-not-avoidance.md`
- `scripts/aios_child_watcher.sh`
- `tests/test_aios_child_watcher.py`
- `docs/AGENT_WORKLOG.md`

forbidden_files:

- `.env`
- private provider auth files
- raw exports
- child repo implementation files
- provider auth stores

## Must Produce

- Child watcher recognizes provider backpressure strings such as rate limits,
  quota limits, and reset-time messages.
- Child watcher recognizes provider auth/PIN failures, including Korean
  localized PIN failure text and Gemini missing-auth messages.
- Child watcher can route through more than one fallback:
  `codex -> claude -> gemini -> local` or another CapabilityOS-recommended
  order.
- CapabilityOS remains recommendation-only; it suggests fallback agents but
  does not execute the work.
- Local fallback is allowed as a draft/substrate route, but a successful local
  final attempt is marked `held` with
  `local_llm_used_as_final_acceptor_without_verifier`.

## OS Semantics

CapabilityOS has high freedom before execution because it owns route discovery,
tool substitution, provider fallback, cost/privacy/risk notes, and alternative
capability selection. It does not gain authority to accept final work.

GenesisOS has high freedom before execution because it owns meaning
normalization, language alignment, assumption mutation, and alternative framing.
It does not gain authority to mutate memory lifecycle or execute child repo
changes.

Hive remains the execution government. MemoryOS remains evidence and memory.
myworld remains the head/control plane that expresses intent, issues packets,
and decides whether held work can advance.

## Verification Gate

```bash
bash -n scripts/aios_child_watcher.sh
python -m unittest tests/test_aios_child_watcher.py
bash scripts/aios_child_watcher.sh status
python scripts/aios_monitor.py assess --json
```

## Stop Conditions

- `provider_route_stops_early`: watcher stops after one fallback while untried
  providers remain.
- `provider_auth_misclassified`: PIN/auth failure is treated as ordinary child
  failure.
- `provider_backpressure_misclassified`: rate limit or quota failure is treated
  as ordinary child failure.
- `local_auto_accept`: local fallback output becomes final accepted work
  without a verifier.
- `auth_material_leak`: any PIN, API key, or raw auth prompt is written
  into a packet, contract, or ledger.

## Receipts

- Updated `scripts/aios_child_watcher.sh` to loop over fallback candidates and
  skip already tried providers.
- Added provider backpressure and provider auth/PIN classification.
- Added Gemini and local child watcher routes.
- Added tests covering:
  - Korean PIN/access denial
  - Claude provider limit/backpressure
  - Gemini missing auth method
  - chained fallback into local held state
  - local final output requiring verifier
- ASC-0099 dogfood results now show child repo packets can advance to held
  local fallback results instead of leaving monitor pending.

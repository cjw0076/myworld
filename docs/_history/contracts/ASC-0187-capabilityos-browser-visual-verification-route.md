---
contract_id: ASC-0187
slug: capabilityos-browser-visual-verification-route
status: closed
goal: Add a recommendation-only CapabilityOS route for browser visual verification after the AIOS Control Center Firefox screenshot timeout exposed a routing gap.
created: 2026-05-17T14:00:00+09:00
accepted: 2026-05-17T14:00:00+09:00
closed: 2026-05-17T14:08:00+09:00
---

# ASC-0187 CapabilityOS Browser Visual Verification Route

## Why

ASC-0186 follow-up work made the Control Center chat-first, then dogfooded
visual verification. The page loaded successfully, but Firefox headless
screenshot timed out. MyWorld now has a bounded verifier, but CapabilityOS
still routed the task through generic workflow cards instead of a
browser-visual capability.

This contract closes that routing gap without moving browser execution into
CapabilityOS.

## Scope

- repos: `CapabilityOS`, `myworld`
- allowed_files:
  - `CapabilityOS/capabilityos/catalog.py`
  - `CapabilityOS/tests/fixtures/capabilities.json`
  - `CapabilityOS/tests/test_cli.py`
  - `CapabilityOS/README.md`
  - `CapabilityOS/AGENTS.md`
  - `docs/contracts/ASC-0187-capabilityos-browser-visual-verification-route.md`
  - `docs/contracts/README.md`
  - `docs/AGENT_WORKLOG.md`
- forbidden_files:
  - `.env`
  - provider auth files
  - raw exports
  - browser profile directories
  - scripts that launch browsers from CapabilityOS
  - MemoryOS accepted-memory stores

## CapabilityOS Must Produce

- A recommendation-only capability card:
  - `id`: `cap_browser_visual_verification_route`
  - `executes_tools`: `false`
  - `requires_network`: `false`
  - domains include browser, visual, screenshot, verification, UI, Playwright,
    Firefox, Chromium, and agent-browser.
- Ranking behavior where UI/browser screenshot fallback tasks recommend the
  browser visual verification card first.
- Audit behavior still reports `execution_enabled=[]` and complete capability
  kind coverage.

## MyWorld Must Produce

- Evidence from the bounded visual verifier:
  - `.aios/visual_verification/vis-2c99e07acb2a/receipt.json`
- A MemoryOS review request/result for the negative visual verification
  evidence:
  - `.aios/outbox/memoryOS/mdrev-15c71f52178df865.memoryOS.result.json`
- A saved CapabilityOS recommendation receipt:
  - `.aios/capability_routes/visual-verification-firefox-timeout.json`

## Verification Gate

```bash
cd /home/user/workspaces/jaewon/myworld/CapabilityOS
python -m pytest tests/test_cli.py -v
python -m capabilityos.cli --catalog tests/fixtures/capabilities.json recommend --task "verify AIOS Control Center UI with browser screenshot fallback after Firefox timeout" --json
python -m capabilityos.cli --catalog tests/fixtures/capabilities.json audit --json
```

Pass criteria:

- `tests/test_cli.py` passes.
- The recommendation command ranks
  `cap_browser_visual_verification_route` first.
- Audit reports `execution_enabled=[]`, `catalog_complete=true`, and
  `cap_web_research_route` remains the only network-required card.

## Stop Conditions

- `capabilityos_executes_browser`: CapabilityOS launches a browser, binds
  Playwright, calls agent-browser, or installs tooling.
- `catalog_drift`: default catalog and fixture differ.
- `visual_route_not_ranked`: UI/browser screenshot tasks do not recommend the
  new card first.
- `audit_regression`: audit no longer reports recommendation-only coverage.
- `private_browser_profile_leak`: browser profile paths or private history are
  copied into catalog evidence.

## Receipts

- Added `cap_browser_visual_verification_route` to
  `CapabilityOS/capabilityos/catalog.py` and
  `CapabilityOS/tests/fixtures/capabilities.json`.
- Added test
  `test_recommend_ranks_browser_visual_verification_route_for_ui_screenshots`.
- Preserved recommendation-only invariant: no browser launch or tool binding in
  CapabilityOS.

# AIOS Loop Policy Snapshot

- generated_at: `2026-05-13T20:20:48+09:00`
- open_contract_count: `17`
- capacity: `4`
- verifier_starvation_seconds: `40848`
- priority_inversion_detected: `True`

## Binding

ASC-0122 makes this policy prescriptive for `scripts/aios_round_controller.py`.
Each round controller tick reads the current policy JSON before dispatch and
uses `open_contract_order` as the authoritative order for creating/sending the
next packet. Dispatch decisions are recorded in `.aios/state/dispatches.jsonl`
as `policy_dispatch_decision` events with:

- `policy_recommendation_followed`
- `policy_contract_id`
- `policy_issuer`
- `policy_priority_reason`
- `reason`

If a policy-ranked contract cannot dispatch because its scope is malformed,
missing repos, invalid repos, terminal state, or already-sent packets, the
controller records the skip reason and advances to the next policy-ranked
contract. Inline repo declarations such as `repos: myworld` are normalized
for policy-bound dispatch.

## Open Contract Order

| Contract | Issuer | Wait Seconds | Reason |
| --- | --- | ---: | --- |
| ASC-0096 | founder_go | 40848 | founder_go_immediate |
| ASC-0097 | founder_go | 40848 | founder_go_immediate |
| ASC-0107 | founder_go | 40848 | founder_go_immediate |
| ASC-0114 | founder_go | 40848 | founder_go_immediate |
| ASC-0069 | founder_go | 36876 | founder_go_immediate |
| ASC-0115 | verifier | 40848 | verifier_wait_threshold_met |
| ASC-0116 | verifier | 40848 | verifier_wait_threshold_met |
| ASC-0117 | verifier | 40848 | verifier_wait_threshold_met |
| ASC-0121 | verifier | 40848 | verifier_wait_threshold_met |
| ASC-0077 | operator | 40848 | operator_fifo |
| ASC-0099 | codex_auto | 40848 | codex_auto_fifo |
| ASC-0070 | operator | 36876 | operator_fifo |
| ASC-0071 | operator | 36876 | operator_fifo |
| ASC-0072 | operator | 36876 | operator_fifo |
| ASC-0073 | operator | 36876 | operator_fifo |
| ASC-0074 | operator | 36876 | operator_fifo |
| ASC-0075 | operator | 36876 | operator_fifo |

## Radar Decisions

| Decision | Verdict | Issuer | Score | Source | Reason |
| --- | --- | --- | ---: | --- | --- |
| hold_for_capacity | executable | radar_candidate | 359 | `myworld/hivemind/docs/AGENT_WORKLOG.md` | open contract count 17 is at capacity 4 |
| hold_for_capability | needs_capability | radar_candidate | 337 | `myworld/hivemind/docs/HIVE_MIND_GAPS.md` | capability gap signal must route through CapabilityOS first |
| hold_for_capability | needs_capability | radar_candidate | 332 | `myworld/hivemind/docs/TODO.md` | capability gap signal must route through CapabilityOS first |
| hold_for_capability | needs_capability | radar_candidate | 315 | `myworld/memoryOS/docs/TODO.md` | capability gap signal must route through CapabilityOS first |
| hold_for_capability | needs_capability | radar_candidate | 304 | `myworld/memoryOS/docs/AGENT_WORKLOG.md` | capability gap signal must route through CapabilityOS first |
| hold_for_operator | ambiguous | radar_candidate | 303 | `_from_desktop/dipeen_v2/openclaw/CHANGELOG.md` | operator-gated privacy or founder archive path |
| reject_closed_contract_reference | closed_contract_reference | radar_candidate | 299 | `myworld/docs/contracts/ASC-0002-capabilityos-executable-surface.md` | source is already a closed contract evidence document |
| hold_for_capability | needs_capability | radar_candidate | 297 | `myworld/docs/AIOS_AGENT_LEDGER.md` | capability gap signal must route through CapabilityOS first |
| hold_for_capability | needs_capability | radar_candidate | 275 | `myworld/memoryOS/docs/ALPHA_CHECKLIST.md` | capability gap signal must route through CapabilityOS first |
| reject_closed_contract_reference | closed_contract_reference | radar_candidate | 271 | `myworld/docs/contracts/ASC-0020-hive-worklog-gap-cleanup.md` | source is already a closed contract evidence document |
| reject_closed_contract_reference | closed_contract_reference | radar_candidate | 264 | `myworld/docs/contracts/ASC-0003-dispatch-packet-enrichment.md` | source is already a closed contract evidence document |
| reject_closed_contract_reference | closed_contract_reference | radar_candidate | 264 | `myworld/docs/contracts/ASC-0004-dispatch-watcher-and-state-machine.md` | source is already a closed contract evidence document |
| hold_for_operator | ambiguous | radar_candidate | 257 | `_from_desktop/Uri/docs/agents/collab_protocol/WORK_LOG.md` | operator-gated privacy or founder archive path |
| reject_closed_contract_reference | closed_contract_reference | radar_candidate | 254 | `myworld/docs/contracts/ASC-0005-hive-capability-bridge.md` | source is already a closed contract evidence document |
| reject_closed_contract_reference | closed_contract_reference | radar_candidate | 253 | `myworld/docs/contracts/ASC-0001-memoryos-hivemind-loop.md` | source is already a closed contract evidence document |
| hold_for_capacity | executable | radar_candidate | 248 | `myworld/docs/AIOS_WORK_DISPATCH.md` | open contract count 17 is at capacity 4 |
| reject_closed_contract_reference | closed_contract_reference | radar_candidate | 244 | `myworld/docs/contracts/ASC-0021-hive-arrival-pack.md` | source is already a closed contract evidence document |
| hold_for_capability | needs_capability | radar_candidate | 240 | `myworld/memoryOS/docs/CAPABILITYOS_DESIGN_SEEDS.md` | capability gap signal must route through CapabilityOS first |
| hold_for_capability | needs_capability | radar_candidate | 235 | `myworld/memoryOS/CHANGELOG.md` | capability gap signal must route through CapabilityOS first |
| hold_for_capability | needs_capability | radar_candidate | 233 | `myworld/hivemind/docs/hive_mind.md` | capability gap signal must route through CapabilityOS first |
| reject_closed_contract_reference | closed_contract_reference | radar_candidate | 229 | `myworld/docs/contracts/ASC-0012-child-repo-durability-closeout.md` | source is already a closed contract evidence document |
| hold_for_operator | ambiguous | radar_candidate | 228 | `_from_desktop/Uri/docs/infra/Uri_Infra_Security_Reassessment_v1.md` | operator-gated privacy or founder archive path |
| hold_for_operator | needs_context | radar_candidate | 227 | `myworld/memoryOS/docs/HIVE_INTEGRATION.md` | candidate needs context or operator judgment before acceptance |
| hold_for_capability | needs_capability | radar_candidate | 222 | `myworld/docs/AIOS_LOOP_POLICY.md` | capability gap signal must route through CapabilityOS first |
| hold_for_capability | needs_capability | radar_candidate | 222 | `myworld/hivemind/docs/mos_cli_design.md` | capability gap signal must route through CapabilityOS first |
| hold_for_capability | needs_capability | radar_candidate | 219 | `myworld/memoryOS/docs/JSON_SCHEMAS.md` | capability gap signal must route through CapabilityOS first |
| hold_for_operator | ambiguous | radar_candidate | 219 | `_from_desktop/GoEN/ai_shared/AGENT_WORKLOG.md` | operator-gated privacy or founder archive path |
| hold_for_capacity | executable | radar_candidate | 214 | `myworld/hivemind/docs/RADAR_GAP_TRIAGE.md` | open contract count 17 is at capacity 4 |
| reject_closed_contract_reference | closed_contract_reference | radar_candidate | 212 | `myworld/docs/contracts/ASC-0009-capability-observation-feedback.md` | source is already a closed contract evidence document |
| hold_for_operator | ambiguous | radar_candidate | 211 | `_from_desktop/Uri/docs/deploy_trace.md` | operator-gated privacy or founder archive path |
| hold_for_capacity | executable | radar_candidate | 207 | `myworld/docs/AIOS_BUILD_METHOD.md` | open contract count 17 is at capacity 4 |
| hold_for_operator | needs_context | radar_candidate | 204 | `myworld/hivemind/docs/tui_shift.md` | candidate needs context or operator judgment before acceptance |
| hold_for_capability | needs_capability | radar_candidate | 203 | `myworld/hivemind/docs/final.md` | capability gap signal must route through CapabilityOS first |
| hold_for_capability | needs_capability | radar_candidate | 203 | `myworld/hivemind/docs/memoryOS.md` | capability gap signal must route through CapabilityOS first |
| hold_for_capacity | executable | radar_candidate | 201 | `myworld/hivemind/docs/VISION_GRAPH.md` | open contract count 17 is at capacity 4 |
| hold_for_capacity | executable | radar_candidate | 200 | `myworld/hivemind/docs/my_world.md` | open contract count 17 is at capacity 4 |
| reject_out_of_scope | out_of_scope | radar_candidate | 197 | `universe/quantum/northstar/shift/my_world.md` | candidate is outside AIOS-owned repos |
| hold_for_capacity | executable | radar_candidate | 196 | `myworld/hivemind/docs/TUI_HARNESS.md` | open contract count 17 is at capacity 4 |
| hold_for_capability | needs_capability | radar_candidate | 194 | `myworld/docs/WORKSTREAMS.md` | capability gap signal must route through CapabilityOS first |
| reject_closed_contract_reference | closed_contract_reference | radar_candidate | 193 | `myworld/docs/contracts/ASC-0008-workspace-doc-ingest-memoryos.md` | source is already a closed contract evidence document |

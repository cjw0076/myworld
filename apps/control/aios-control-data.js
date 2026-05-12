window.AIOS_CONTROL_SNAPSHOT = {
  "aios_inputs": {
    "capability_routes": [
      "cap_capabilityos_recommendation",
      "cap_hivemind_execution_harness",
      "cap_memoryos_import_run",
      "cap_memoryos_context_build",
      "cap_capabilityos_recommendation",
      "cap_memoryos_context_build",
      "cap_hivemind_execution_harness",
      "cap_memoryos_import_run"
    ],
    "hive_runs": [
      "run_20260512_182859_370b96",
      "run_20260512_181228_aef902",
      "run_20260512_171540_45136a",
      "run_20260512_153529_9eaea3"
    ],
    "memory_traces": [
      "rtrace_02e5c1e5e56a02d5",
      "rtrace_c0619c4194e7535b",
      "rtrace_7f8eb07cf6b0137e",
      "rtrace_ff2208eaa6d9895b"
    ]
  },
  "contracts": {
    "counts": {
      "accepted": 1,
      "closed": 39
    },
    "latest": [
      {
        "accepted": "2026-05-12 18:30 KST by codex acting operator",
        "closed": "",
        "created": "2026-05-12 18:30 KST",
        "goal": "Package the local AIOS control app, snapshot refresh, monitor write, static server, and round-controller status into one repeatable local command.",
        "id": "ASC-0040",
        "path": "docs/contracts/ASC-0040-on-prem-evolving-application.md",
        "slug": "on-prem-evolving-application",
        "status": "accepted",
        "stop_conditions": [
          "`child_repo_source_edit`",
          "`runtime_state_committed`",
          "`server_orphaned`",
          "`snapshot_refresh_failed`",
          "`monitor_not_clear`",
          "`verification_gate_failed`"
        ]
      },
      {
        "accepted": "2026-05-12 18:13 KST by codex acting operator",
        "closed": "2026-05-12 18:24 KST",
        "created": "2026-05-12 18:13 KST",
        "goal": "Create the first local visualization-first AIOS control surface from generated myworld state snapshots.",
        "id": "ASC-0039",
        "path": "docs/contracts/ASC-0039-visual-control-application.md",
        "slug": "visual-control-application",
        "status": "closed",
        "stop_conditions": [
          "`snapshot_reads_logs`: snapshot reads `.aios/logs` bodies.",
          "`child_repo_source_edit`: implementation changes child repo source.",
          "`runtime_state_committed`: `.aios/state` files are staged.",
          "`dependency_sprawl`: contract adds a framework or package manager before the static surface proves useful.",
          "`verification_gate_failed`"
        ]
      },
      {
        "accepted": "2026-05-12 17:18 KST by codex acting operator",
        "closed": "2026-05-12 17:36 KST",
        "created": "2026-05-12 17:18 KST",
        "goal": "Let lower repos submit goals or friction to always-on myworld, receive MemoryOS/CapabilityOS/Hive route packets, and turn returned friction into AIOS improvement candidates.",
        "id": "ASC-0038",
        "path": "docs/contracts/ASC-0038-self-resonant-repo-loop.md",
        "slug": "self-resonant-repo-loop",
        "status": "closed",
        "stop_conditions": [
          "`direct_child_repo_edit`: myworld patches child implementation files instead of issuing a packet.",
          "`route_executes_work`: route packet triggers provider, tool, or repo execution directly.",
          "`memory_auto_accept`: submitted goal or route creates accepted memory without MemoryOS review.",
          "`capability_binding_without_review`: route binds or installs tools instead of recommending.",
          "`sensitive_source_content_in_goal`: submission includes unreviewed source dump content or key-like values.",
          "`unbounded_repo_source`: submit accepts an unknown source repo without explicit operator allow-list.",
          "`verification_gate_failed`"
        ]
      },
      {
        "accepted": "2026-05-12 KST by claude acting operator",
        "closed": "2026-05-12 16:01 KST",
        "created": "2026-05-12 KST",
        "goal": "Make child-watcher provider-fallback recognize codex CLI access-denied messages in Korean (and other locales) so ASC-0025 fallback triggers when codex CLI rejects non-interactive auth in localized text.",
        "id": "ASC-0037",
        "path": "docs/contracts/ASC-0037-child-watcher-locale-aware-fallback.md",
        "slug": "child-watcher-locale-aware-fallback",
        "status": "closed",
        "stop_conditions": [
          "`regex_too_broad`: new pattern matches non-auth failures (e.g. routine Korean error messages from unrelated tools).",
          "`fallback_loop`: fallback agent (claude) also fails with same category and watcher recurses without bound.",
          "`child_repo_source_edit`: this contract changes child repo source.",
          "`english_pattern_regression`: existing English patterns no longer match."
        ]
      },
      {
        "accepted": "2026-05-12 15:39 KST",
        "closed": "2026-05-12 16:01 KST",
        "created": "2026-05-12 15:39 KST",
        "goal": "Teach every lower-repo agent the AIOS shared language and require semantic handshakes before cross-repo work.",
        "id": "ASC-0036",
        "path": "docs/contracts/ASC-0036-cross-repo-semantic-alignment.md",
        "slug": "cross-repo-semantic-alignment",
        "status": "closed",
        "stop_conditions": [
          "`semantic_drift_unresolved`",
          "`missing_repo_agent_update`",
          "`handshake_validator_false_positive`",
          "`child_repo_scope_leak`",
          "`role_boundary_blur`",
          "`verification_gate_failed`"
        ]
      },
      {
        "accepted": "2026-05-12 15:17 KST",
        "closed": "2026-05-12 15:24 KST",
        "created": "2026-05-12 15:17 KST",
        "goal": "Wire the action policy into dispatch creation and sending so checkpoint-required packets are blocked before inbox delivery.",
        "id": "ASC-0035",
        "path": "docs/contracts/ASC-0035-policy-gated-dispatch.md",
        "slug": "policy-gated-dispatch",
        "status": "closed",
        "stop_conditions": [
          "`policy_gate_not_called_before_inbox_write`",
          "`non_allowed_policy_packet_written_to_inbox`",
          "`manual_send_and_loop_policy_drift`",
          "`policy_blocks_all_local_dispatch`",
          "`child_repo_scope_leak`",
          "`missing_dispatch_event_for_blocked_packet`"
        ]
      },
      {
        "accepted": "2026-05-12 14:40 KST",
        "closed": "2026-05-12 14:42 KST",
        "created": "2026-05-12 14:40 KST",
        "goal": "Add a machine-checkable AIOS action policy engine that gates proposed actions by authority, risk, privacy, resource use, and checkpoint requirements.",
        "id": "ASC-0034",
        "path": "docs/contracts/ASC-0034-governance-action-policy-engine.md",
        "slug": "governance-action-policy-engine",
        "status": "closed",
        "stop_conditions": [
          "`policy_allows_forbidden_action`",
          "`policy_skips_human_checkpoint`",
          "`policy_blocks_all_low_risk_work`",
          "`policy_executes_action`",
          "`child_repo_scope_leak`"
        ]
      },
      {
        "accepted": "2026-05-12 14:35 KST",
        "closed": "2026-05-12 14:37 KST",
        "created": "2026-05-12 14:35 KST",
        "goal": "Define and validate the next AIOS readiness layer for accountable enterprise-scale and sovereign-AI governance.",
        "id": "ASC-0033",
        "path": "docs/contracts/ASC-0033-sovereign-ai-governance-readiness.md",
        "slug": "sovereign-ai-governance-readiness",
        "status": "closed",
        "stop_conditions": [
          "`sovereignty_overclaim`: output claims real-world legal authority or political sovereignty.",
          "`governance_without_checkpoint`: high-authority actions can proceed without human checkpoint rules.",
          "`audit_gap`: readiness can pass without ledger/evidence artifacts.",
          "`resource_authority_gap`: capability/resource use has no bounded policy.",
          "`child_repo_scope_leak`: this contract edits child repo source."
        ]
      },
      {
        "accepted": "2026-05-12",
        "closed": "2026-05-12",
        "created": "2026-05-12",
        "goal": "Create an isolated Uri child repository for the student digital campus business workspace without mixing product artifacts into the MyWorld control plane.",
        "id": "ASC-0032",
        "path": "docs/contracts/ASC-0032-uri-repo-isolation-setup.md",
        "slug": "uri-repo-isolation-setup",
        "status": "closed",
        "stop_conditions": [
          "privacy_violation",
          "scope_violation",
          "missing_required_artifact",
          "ownership_conflict",
          "contract_ambiguous",
          "nonpublic code or tool access required",
          "proprietary workflow copied without public evidence or license"
        ]
      },
      {
        "accepted": "2026-05-12 14:13 KST",
        "closed": "2026-05-12 14:16 KST",
        "created": "2026-05-12 14:13 KST",
        "goal": "Dogfood CapabilityOS web-route by producing and validating a cited web evidence receipt for AIOS capability routing.",
        "id": "ASC-0031",
        "path": "docs/contracts/ASC-0031-web-evidence-execution-loop.md",
        "slug": "web-evidence-execution-loop",
        "status": "closed",
        "stop_conditions": [
          "`uncited_claim`: receipt makes a web-derived claim without source URL.",
          "`raw_page_body_committed`: receipt stores copied raw page bodies instead of short claims/paraphrases.",
          "`privacy_violation`: receipt includes secrets, personal data, raw private exports, or credentialed pages.",
          "`capability_route_missing`: receipt does not reference the CapabilityOS `web-route` plan.",
          "`stale_source_policy`: current-topic source has no accessed date or source date when available."
        ]
      }
    ],
    "total": 40
  },
  "dispatches": {
    "counts": {
      "collected": 4,
      "escalated": 1,
      "passed": 2,
      "released": 27
    },
    "latest": [
      {
        "collected": [
          "myworld"
        ],
        "contract_id": "ASC-0040",
        "dispatch_id": "asc-0040",
        "goal": "Package the local AIOS control app, snapshot refresh, monitor write, static server, and round-controller status into one repeatable local command.",
        "reason": "asc_0040_on_prem_local_app_verified",
        "sent": [
          "myworld"
        ],
        "status": "released",
        "timestamp": "2026-05-12T18:34:23+09:00"
      },
      {
        "collected": [
          "myworld"
        ],
        "contract_id": "ASC-0039",
        "dispatch_id": "asc-0039",
        "goal": "Create the first local visualization-first AIOS control surface from generated myworld state snapshots.",
        "reason": "asc_0039_visual_control_application_verified",
        "sent": [
          "myworld"
        ],
        "status": "released",
        "timestamp": "2026-05-12T18:23:51+09:00"
      },
      {
        "collected": [
          "CapabilityOS",
          "hivemind",
          "memoryOS",
          "myworld"
        ],
        "contract_id": "ASC-0038",
        "dispatch_id": "asc-0038",
        "goal": "Let lower repos submit goals or friction to always-on myworld, receive MemoryOS/CapabilityOS/Hive route packets, and turn returned friction into AIOS improvement candidates.",
        "reason": "asc_0038_self_resonant_repo_loop_verified",
        "sent": [
          "CapabilityOS",
          "hivemind",
          "memoryOS",
          "myworld"
        ],
        "status": "released",
        "timestamp": "2026-05-12T17:36:21+09:00"
      },
      {
        "collected": [
          "myworld"
        ],
        "contract_id": "ASC-0037",
        "dispatch_id": "asc-0037",
        "goal": "Make child-watcher provider-fallback recognize codex CLI access-denied messages in Korean (and other locales) so ASC-0025 fallback triggers when codex CLI rejects non-interactive auth in localized text.",
        "reason": "asc_0037_locale_aware_fallback_verified",
        "sent": [],
        "status": "released",
        "timestamp": "2026-05-12T17:13:30+09:00"
      },
      {
        "collected": [
          "CapabilityOS",
          "hivemind",
          "memoryOS",
          "myworld"
        ],
        "contract_id": "ASC-0036",
        "dispatch_id": "asc-0036",
        "goal": "Teach every lower-repo agent the AIOS shared language and require semantic handshakes before cross-repo work.",
        "reason": "child_work_committed_by_operator_after_korean_auth_locale_fix",
        "sent": [
          "CapabilityOS",
          "hivemind",
          "memoryOS",
          "myworld"
        ],
        "status": "released",
        "timestamp": "2026-05-12T16:31:20+09:00"
      },
      {
        "collected": [
          "myworld"
        ],
        "contract_id": "ASC-0035",
        "dispatch_id": "asc-0035-policy-gate-dogfood",
        "goal": "Wire the action policy into dispatch creation and sending so checkpoint-required packets are blocked before inbox delivery.",
        "reason": "asc_0035_policy_gated_dispatch_verified",
        "sent": [
          "myworld"
        ],
        "status": "released",
        "timestamp": "2026-05-12T15:22:22+09:00"
      },
      {
        "collected": [],
        "contract_id": "ASC-0035",
        "dispatch_id": "asc-0035",
        "goal": "Wire the action policy into dispatch creation and sending so checkpoint-required packets are blocked before inbox delivery.",
        "reason": "action_policy_escalate",
        "sent": [],
        "status": "escalated",
        "timestamp": "2026-05-12T15:18:45+09:00"
      },
      {
        "collected": [
          "myworld"
        ],
        "contract_id": "ASC-0034",
        "dispatch_id": "asc-0034",
        "goal": "Add a machine-checkable AIOS action policy engine that gates proposed actions by authority, risk, privacy, resource use, and checkpoint requirements.",
        "reason": "asc_0034_governance_action_policy_engine_verified",
        "sent": [
          "myworld"
        ],
        "status": "released",
        "timestamp": "2026-05-12T14:42:08+09:00"
      },
      {
        "collected": [
          "myworld"
        ],
        "contract_id": "ASC-0033",
        "dispatch_id": "asc-0033",
        "goal": "Define and validate the next AIOS readiness layer for accountable enterprise-scale and sovereign-AI governance.",
        "reason": "asc_0033_sovereign_ai_governance_readiness_verified",
        "sent": [
          "myworld"
        ],
        "status": "released",
        "timestamp": "2026-05-12T14:37:27+09:00"
      },
      {
        "collected": [
          "myworld"
        ],
        "contract_id": "ASC-0031",
        "dispatch_id": "asc-0031",
        "goal": "Dogfood CapabilityOS web-route by producing and validating a cited web evidence receipt for AIOS capability routing.",
        "reason": "asc_0031_web_evidence_execution_loop_verified",
        "sent": [
          "myworld"
        ],
        "status": "released",
        "timestamp": "2026-05-12T14:15:45+09:00"
      },
      {
        "collected": [
          "CapabilityOS"
        ],
        "contract_id": "ASC-0030",
        "dispatch_id": "asc-0030",
        "goal": "Add a recommendation-only CapabilityOS web research route so AIOS can deliberately use broad internet search with source and privacy guardrails.",
        "reason": "asc_0030_capabilityos_web_research_route_verified",
        "sent": [
          "CapabilityOS"
        ],
        "status": "released",
        "timestamp": "2026-05-12T03:27:45+09:00"
      },
      {
        "collected": [
          "myworld"
        ],
        "contract_id": "ASC-0029",
        "dispatch_id": "asc-0029",
        "goal": "Add a persistent control-plane round controller so AIOS continuation does not depend on a chat turn staying open.",
        "reason": "asc_0029_persistent_control_loop_verified",
        "sent": [
          "myworld"
        ],
        "status": "passed",
        "timestamp": "2026-05-12T03:13:10+09:00"
      }
    ],
    "timeline": [
      {
        "dispatch_id": "asc-0038",
        "event": "escalated",
        "repo": "myworld",
        "status": "escalated",
        "timestamp": "2026-05-12T17:18:48+09:00"
      },
      {
        "dispatch_id": "asc-0038",
        "event": "escalated",
        "repo": "hivemind",
        "status": "escalated",
        "timestamp": "2026-05-12T17:18:48+09:00"
      },
      {
        "dispatch_id": "asc-0038",
        "event": "escalated",
        "repo": "memoryOS",
        "status": "escalated",
        "timestamp": "2026-05-12T17:18:48+09:00"
      },
      {
        "dispatch_id": "asc-0038",
        "event": "escalated",
        "repo": "CapabilityOS",
        "status": "escalated",
        "timestamp": "2026-05-12T17:18:48+09:00"
      },
      {
        "dispatch_id": "asc-0038",
        "event": "sent",
        "repo": "myworld",
        "status": "sent",
        "timestamp": "2026-05-12T17:30:01+09:00"
      },
      {
        "dispatch_id": "asc-0038",
        "event": "sent",
        "repo": "hivemind",
        "status": "sent",
        "timestamp": "2026-05-12T17:30:01+09:00"
      },
      {
        "dispatch_id": "asc-0038",
        "event": "sent",
        "repo": "memoryOS",
        "status": "sent",
        "timestamp": "2026-05-12T17:30:01+09:00"
      },
      {
        "dispatch_id": "asc-0038",
        "event": "sent",
        "repo": "CapabilityOS",
        "status": "sent",
        "timestamp": "2026-05-12T17:30:01+09:00"
      },
      {
        "dispatch_id": "asc-0038",
        "event": "running",
        "repo": "myworld",
        "status": "running",
        "timestamp": "2026-05-12T17:30:29+09:00"
      },
      {
        "dispatch_id": "asc-0038",
        "event": "watched",
        "repo": "myworld",
        "status": "passed",
        "timestamp": "2026-05-12T17:30:38+09:00"
      },
      {
        "dispatch_id": "asc-0038",
        "event": "collected",
        "repo": "myworld",
        "status": "collected",
        "timestamp": "2026-05-12T17:31:01+09:00"
      },
      {
        "dispatch_id": "asc-0038",
        "event": "collected",
        "repo": "hivemind",
        "status": "collected",
        "timestamp": "2026-05-12T17:32:38+09:00"
      },
      {
        "dispatch_id": "asc-0038",
        "event": "collected",
        "repo": "CapabilityOS",
        "status": "collected",
        "timestamp": "2026-05-12T17:32:38+09:00"
      },
      {
        "dispatch_id": "asc-0038",
        "event": "collected",
        "repo": "memoryOS",
        "status": "collected",
        "timestamp": "2026-05-12T17:33:10+09:00"
      },
      {
        "dispatch_id": "asc-0038",
        "event": "running",
        "repo": "myworld",
        "status": "running",
        "timestamp": "2026-05-12T17:36:02+09:00"
      },
      {
        "dispatch_id": "asc-0038",
        "event": "watched",
        "repo": "myworld",
        "status": "passed",
        "timestamp": "2026-05-12T17:36:12+09:00"
      },
      {
        "dispatch_id": "asc-0038",
        "event": "released",
        "repo": null,
        "status": "released",
        "timestamp": "2026-05-12T17:36:21+09:00"
      },
      {
        "dispatch_id": "asc-0039",
        "event": "created",
        "repo": null,
        "status": "created",
        "timestamp": "2026-05-12T18:14:52+09:00"
      },
      {
        "dispatch_id": "asc-0039",
        "event": "sent",
        "repo": "myworld",
        "status": "sent",
        "timestamp": "2026-05-12T18:23:28+09:00"
      },
      {
        "dispatch_id": "asc-0039",
        "event": "sent",
        "repo": "myworld",
        "status": "sent",
        "timestamp": "2026-05-12T18:23:31+09:00"
      },
      {
        "dispatch_id": "asc-0039",
        "event": "running",
        "repo": "myworld",
        "status": "running",
        "timestamp": "2026-05-12T18:23:32+09:00"
      },
      {
        "dispatch_id": "asc-0039",
        "event": "watched",
        "repo": "myworld",
        "status": "passed",
        "timestamp": "2026-05-12T18:23:41+09:00"
      },
      {
        "dispatch_id": "asc-0039",
        "event": "collected",
        "repo": "myworld",
        "status": "collected",
        "timestamp": "2026-05-12T18:23:51+09:00"
      },
      {
        "dispatch_id": "asc-0039",
        "event": "released",
        "repo": null,
        "status": "released",
        "timestamp": "2026-05-12T18:23:51+09:00"
      },
      {
        "dispatch_id": "asc-0040",
        "event": "created",
        "repo": null,
        "status": "created",
        "timestamp": "2026-05-12T18:30:26+09:00"
      },
      {
        "dispatch_id": "asc-0040",
        "event": "sent",
        "repo": "myworld",
        "status": "sent",
        "timestamp": "2026-05-12T18:30:26+09:00"
      },
      {
        "dispatch_id": "asc-0040",
        "event": "running",
        "repo": "myworld",
        "status": "running",
        "timestamp": "2026-05-12T18:34:00+09:00"
      },
      {
        "dispatch_id": "asc-0040",
        "event": "watched",
        "repo": "myworld",
        "status": "passed",
        "timestamp": "2026-05-12T18:34:11+09:00"
      },
      {
        "dispatch_id": "asc-0040",
        "event": "collected",
        "repo": "myworld",
        "status": "collected",
        "timestamp": "2026-05-12T18:34:23+09:00"
      },
      {
        "dispatch_id": "asc-0040",
        "event": "released",
        "repo": null,
        "status": "released",
        "timestamp": "2026-05-12T18:34:23+09:00"
      }
    ],
    "total": 34
  },
  "generated_at": "2026-05-12T18:34:43+09:00",
  "goals": {
    "active": {
      "completed": [
        "source_read_registry: ASC-0023 added Hive source-read records and arrival-pack reconciliation hints.",
        "watcher_execution_reliability: ASC-0025 added bounded child watcher provider-access fallback and structured attempt evidence.",
        "capability_routing_memory: ASC-0026 made CapabilityOS recommendations consume prior AIOS observation outcomes in-memory.",
        "memory_feedback_tightening: ASC-0027 added MemoryOS feedback directives and Hive context-pack rendering for next-run shaping.",
        "capability_route_binding: ASC-0028 bound child watcher access-denied fallback selection to CapabilityOS provider-route recommendations.",
        "persistent_control_loop: ASC-0029 added a provider-independent round controller that runs monitor, goal evolution, dispatch apply, child watcher status, and durable round receipts outside the chat turn.",
        "capabilityos_web_research_route: ASC-0030 added a broad internet/web research route with source policy, privacy policy, route limits, and no CapabilityOS-side network execution.",
        "web_evidence_execution_loop: ASC-0031 dogfooded CapabilityOS `web-route` by producing a cited web evidence receipt and a validator for source, privacy, and citation guardrails."
      ],
      "id": "AIOS-GOAL-0001",
      "north_star": [
        "Build AIOS until one local-first operating system can coordinate the functional",
        "surface of a large enterprise and a sovereign AI governance stack: strategy,",
        "memory, capability discovery, execution, verification, learning, policy,",
        "audit, resource routing, and operator checkpoints."
      ],
      "path": "docs/goals/AIOS-GOAL-0001-make-something-great.md",
      "preferred_next": [
        "on_prem_evolving_application: package AIOS as a local application whose control plane, memory store, capability router, and execution harness keep improving through verified repo feedback.",
        "web_evidence_memory_review: turn validated web evidence receipts into MemoryOS review candidates without auto-accepting web-derived facts.",
        "capability_observation_memory_import: decide which CapabilityOS observations should enter MemoryOS as reviewable durable memory.",
        "contract_autodraft_from_goal_plan: turn an unblocked goal evolution recommendation into a proposed smart contract draft without relying on chat memory."
      ],
      "slug": "make-something-great",
      "status": "active"
    },
    "evolution": {
      "monitor_health": "clear",
      "path": "docs/goals/AIOS-GOAL-0001-evolution.md",
      "readiness": "L6 repeatable",
      "recommendation": "goal:on_prem_evolving_application"
    },
    "items": [
      {
        "completed": [
          "source_read_registry: ASC-0023 added Hive source-read records and arrival-pack reconciliation hints.",
          "watcher_execution_reliability: ASC-0025 added bounded child watcher provider-access fallback and structured attempt evidence.",
          "capability_routing_memory: ASC-0026 made CapabilityOS recommendations consume prior AIOS observation outcomes in-memory.",
          "memory_feedback_tightening: ASC-0027 added MemoryOS feedback directives and Hive context-pack rendering for next-run shaping.",
          "capability_route_binding: ASC-0028 bound child watcher access-denied fallback selection to CapabilityOS provider-route recommendations.",
          "persistent_control_loop: ASC-0029 added a provider-independent round controller that runs monitor, goal evolution, dispatch apply, child watcher status, and durable round receipts outside the chat turn.",
          "capabilityos_web_research_route: ASC-0030 added a broad internet/web research route with source policy, privacy policy, route limits, and no CapabilityOS-side network execution.",
          "web_evidence_execution_loop: ASC-0031 dogfooded CapabilityOS `web-route` by producing a cited web evidence receipt and a validator for source, privacy, and citation guardrails."
        ],
        "id": "AIOS-GOAL-0001",
        "north_star": [
          "Build AIOS until one local-first operating system can coordinate the functional",
          "surface of a large enterprise and a sovereign AI governance stack: strategy,",
          "memory, capability discovery, execution, verification, learning, policy,",
          "audit, resource routing, and operator checkpoints."
        ],
        "path": "docs/goals/AIOS-GOAL-0001-make-something-great.md",
        "preferred_next": [
          "on_prem_evolving_application: package AIOS as a local application whose control plane, memory store, capability router, and execution harness keep improving through verified repo feedback.",
          "web_evidence_memory_review: turn validated web evidence receipts into MemoryOS review candidates without auto-accepting web-derived facts.",
          "capability_observation_memory_import: decide which CapabilityOS observations should enter MemoryOS as reviewable durable memory.",
          "contract_autodraft_from_goal_plan: turn an unblocked goal evolution recommendation into a proposed smart contract draft without relying on chat memory."
        ],
        "slug": "make-something-great",
        "status": "active"
      }
    ]
  },
  "monitor": {
    "findings": [],
    "generated_at": "2026-05-12T18:34:43+09:00",
    "health": "clear",
    "next_actions": [
      {
        "action": "continue_observing",
        "owner": "myworld",
        "reason": "No active monitor alerts.",
        "severity": "info"
      }
    ],
    "schema_version": "aios.monitor.assessment.v1",
    "snapshot_generated_at": "2026-05-12T18:34:43+09:00",
    "watched": {
      "alerts": 0,
      "contracts": 40,
      "dispatches": 33,
      "reconciliations_applied": 1,
      "repos": 3
    }
  },
  "next_actions": [
    {
      "action": "continue_observing",
      "owner": "myworld",
      "reason": "No active monitor alerts.",
      "severity": "info"
    }
  ],
  "repos": {
    "items": [
      {
        "changes": [],
        "dirty": false,
        "exists": true,
        "goal_count": 0,
        "inbox_count": 11,
        "outbox_count": 11,
        "repo": "hivemind",
        "route_count": 0
      },
      {
        "changes": [],
        "dirty": false,
        "exists": true,
        "goal_count": 0,
        "inbox_count": 9,
        "outbox_count": 9,
        "repo": "memoryOS",
        "route_count": 0
      },
      {
        "changes": [],
        "dirty": false,
        "exists": true,
        "goal_count": 0,
        "inbox_count": 8,
        "outbox_count": 8,
        "repo": "CapabilityOS",
        "route_count": 0
      }
    ]
  },
  "root": "/home/user/workspaces/jaewon/myworld",
  "round_controller": {
    "child_executions": [],
    "child_watcher_status": {
      "name": "child_watcher_status",
      "parsed": {
        "pending_total": 0,
        "repos": {
          "CapabilityOS": {
            "inbox": 8,
            "outbox": 8,
            "pending": 0,
            "running": false
          },
          "hivemind": {
            "inbox": 11,
            "outbox": 11,
            "pending": 0,
            "running": false
          },
          "memoryOS": {
            "inbox": 9,
            "outbox": 9,
            "pending": 0,
            "running": false
          }
        }
      },
      "returncode": 0,
      "status": "passed",
      "stderr_tail": "",
      "timed_out": false
    },
    "failed_steps": [],
    "generated_at": "2026-05-12T18:34:13+09:00",
    "mode": "control_only",
    "recommended_next": {
      "action": "hold_for_monitor",
      "reason": "blocked"
    },
    "root": "/home/user/workspaces/jaewon/myworld",
    "schema_version": "aios.round_controller.v1",
    "status": "passed",
    "steps": {
      "dispatch_loop": {
        "error": "",
        "name": "dispatch_loop",
        "parsed": {
          "actions": [],
          "generated_at": "2026-05-12T18:34:11+09:00",
          "mode": "apply",
          "observations": [
            {
              "contract_id": "ASC-0001",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0002",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0003",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0004",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0005",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0006",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0007",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0008",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0009",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0010",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0011",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0012",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0013",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0014",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0015",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0016",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0017",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0018",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0019",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0020",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0021",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0022",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0023",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0024",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0025",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0026",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0027",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0028",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0029",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0030",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0031",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0032",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0033",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0034",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0035",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0036",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0037",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0038",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0039",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0040",
              "dispatch_id": "asc-0040",
              "next": "await_results",
              "pending_results": [
                "myworld"
              ],
              "status": "accepted"
            }
          ],
          "schema_version": "aios.loop.v1"
        },
        "returncode": 0,
        "status": "passed",
        "stderr_tail": "",
        "timed_out": false
      },
      "goal_evolution": {
        "error": "",
        "name": "goal_evolution",
        "parsed": {
          "evidence": {
            "monitor_findings": 1,
            "monitor_health": "blocked",
            "policy_decision_count": 40,
            "policy_generated_at": "2026-05-12T18:34:11+09:00",
            "radar_candidate_count": 60,
            "readiness_level": null,
            "readiness_level_name": null
          },
          "generated_at": "2026-05-12T18:34:11+09:00",
          "goal": {
            "anti_cheat_checks": [
              "Do not count docs-only work as progress when the goal requires execution.",
              "Do not reopen closed contracts as new work.",
              "Do not auto-accept private/archive paths or raw exports.",
              "Do not let myworld become a broad child-repo implementation worker.",
              "Do not claim goal progress without monitor/readiness/policy evidence.",
              "Do not accept self-evaluation without adversarial or verification evidence for high-risk changes.",
              "Do not pursue coercion, illegal access, deception, or real-world authority without explicit lawful authorization and human checkpoints.",
              "Do not optimize power without governance, auditability, reversibility, and bounded execution."
            ],
            "goal_id": "AIOS-GOAL-0001",
            "path": "/home/user/workspaces/jaewon/myworld/docs/goals/AIOS-GOAL-0001-make-something-great.md",
            "quality_function": [
              "reduce_user_relay: fewer cases where the user must copy context between agents or repos.",
              "increase_verified_execution: more child-repo work closes with tests, receipts, result packets, and monitor-clear evidence.",
              "improve_context_reuse: MemoryOS context, Hive arrival packs, and accepted prior decisions shape future work.",
              "improve_capability_routing: CapabilityOS recommendations and observations affect tool/provider choices when execution options matter.",
              "strengthen_stop_conditions: privacy, scope, stale evidence, and ambiguous ownership stop the loop instead of being bypassed.",
              "increase_repeatability: a future agent can rerun the loop from docs/scripts without chat context.",
              "increase_institutional_capacity: AIOS can coordinate strategy, execution, audit, learning, and resource routing across many workstreams like a large organization.",
              "strengthen_governance: every autonomous action has authority, scope, accountability, rollback/hold semantics, and review evidence."
            ],
            "slug": "make-something-great",
            "status": "active"
          },
          "recommendation": {
            "alignment_reasons": [
              "goal_preferred_next"
            ],
            "blocked": false,
            "blocked_reasons": [],
            "candidate_task": "package AIOS as a local application whose control plane, memory store, capability router, and execution harness keep improving through verified repo feedback.",
            "domain": "myworld",
            "goal_score": 100,
            "path": "goal:on_prem_evolving_application",
            "policy_decision": "goal_preferred",
            "policy_reason": "listed in active goal Preferred Next Improvements",
            "radar_score": 0,
            "signals": {}
          },
          "schema_version": "aios.goal_evolution.v1",
          "stop_conditions": [
            "monitor_not_clear"
          ],
          "top_candidates": [
            {
              "alignment_reasons": [
                "verification_signal",
                "policy_accept_now"
              ],
              "blocked": true,
              "blocked_reasons": [
                "history_source_requires_triage"
              ],
              "candidate_task": "issue a Hive Mind packet for execution, harness, or verification follow-up",
              "domain": "hivemind",
              "goal_score": 375,
              "path": "myworld/hivemind/docs/AGENT_WORKLOG.md",
              "policy_decision": "accept_now",
              "policy_reason": "executable candidate and loop capacity is available",
              "radar_score": 359,
              "signals": {
                "aios": 4,
                "blocker": 4,
                "capabilityos": 1,
                "contract": 8,
                "gap": 3,
                "hivemind": 12,
                "memoryos": 12,
                "next": 12,
                "p0": 3,
                "todo": 12,
                "verify": 9
              }
            },
            {
              "alignment_reasons": [
                "verification_signal",
                "capability_dependency"
              ],
              "blocked": true,
              "blocked_reasons": [
                "hold_for_capability"
              ],
              "candidate_task": "issue a Hive Mind packet for execution, harness, or verification follow-up",
              "domain": "hivemind",
              "goal_score": 328,
              "path": "myworld/hivemind/docs/HIVE_MIND_GAPS.md",
              "policy_decision": "hold_for_capability",
              "policy_reason": "capability gap signal must route through CapabilityOS first",
              "radar_score": 337,
              "signals": {
                "blocker": 9,
                "capabilityos": 9,
                "contract": 3,
                "gap": 11,
                "hivemind": 12,
                "memoryos": 12,
                "next": 12,
                "verify": 12
              }
            },
            {
              "alignment_reasons": [
                "verification_signal",
                "capability_dependency"
              ],
              "blocked": true,
              "blocked_reasons": [
                "hold_for_capability"
              ],
              "candidate_task": "issue a Hive Mind packet for execution, harness, or verification follow-up",
              "domain": "hivemind",
              "goal_score": 323,
              "path": "myworld/hivemind/docs/TODO.md",
              "policy_decision": "hold_for_capability",
              "policy_reason": "capability gap signal must route through CapabilityOS first",
              "radar_score": 332,
              "signals": {
                "aios": 1,
                "blocker": 8,
                "capabilityos": 12,
                "contract": 4,
                "gap": 4,
                "hivemind": 12,
                "memoryos": 12,
                "next": 12,
                "p0": 1,
                "todo": 3,
                "verify": 10
              }
            },
            {
              "alignment_reasons": [
                "verification_signal"
              ],
              "blocked": true,
              "blocked_reasons": [
                "private_or_operator_gated_path",
                "hold_for_operator"
              ],
              "candidate_task": "triage as external workspace context before importing into AIOS",
              "domain": "_from_desktop",
              "goal_score": 309,
              "path": "_from_desktop/dipeen_v2/openclaw/CHANGELOG.md",
              "policy_decision": "hold_for_operator",
              "policy_reason": "operator-gated privacy or founder archive path",
              "radar_score": 303,
              "signals": {
                "blocker": 12,
                "capabilityos": 5,
                "gap": 12,
                "memoryos": 12,
                "next": 12,
                "verify": 12
              }
            },
            {
              "alignment_reasons": [
                "verification_signal",
                "capability_dependency"
              ],
              "blocked": true,
              "blocked_reasons": [
                "hold_for_capability"
              ],
              "candidate_task": "issue a MemoryOS packet for context/provenance/review lifecycle follow-up",
              "domain": "memoryOS",
              "goal_score": 306,
              "path": "myworld/memoryOS/docs/TODO.md",
              "policy_decision": "hold_for_capability",
              "policy_reason": "capability gap signal must route through CapabilityOS first",
              "radar_score": 315,
              "signals": {
                "capabilityos": 12,
                "contract": 12,
                "gap": 8,
                "hivemind": 12,
                "memoryos": 12,
                "next": 4,
                "todo": 12,
                "verify": 8
              }
            },
            {
              "alignment_reasons": [
                "verification_signal",
                "capability_dependency"
              ],
              "blocked": true,
              "blocked_reasons": [
                "history_source_requires_triage",
                "hold_for_capability"
              ],
              "candidate_task": "issue a MemoryOS packet for context/provenance/review lifecycle follow-up",
              "domain": "memoryOS",
              "goal_score": 295,
              "path": "myworld/memoryOS/docs/AGENT_WORKLOG.md",
              "policy_decision": "hold_for_capability",
              "policy_reason": "capability gap signal must route through CapabilityOS first",
              "radar_score": 304,
              "signals": {
                "aios": 6,
                "blocker": 1,
                "capabilityos": 8,
                "contract": 12,
                "gap": 8,
                "hivemind": 12,
                "memoryos": 12,
                "next": 5,
                "todo": 4,
                "verify": 12
              }
            },
            {
              "alignment_reasons": [
                "verification_signal",
                "capability_dependency"
              ],
              "blocked": true,
              "blocked_reasons": [
                "closed_contract_source",
                "reject_closed_contract_reference"
              ],
              "candidate_task": "promote this control-plane signal into an AIOS contract or readiness gate",
              "domain": "myworld",
              "goal_score": 290,
              "path": "myworld/docs/contracts/ASC-0002-capabilityos-executable-surface.md",
              "policy_decision": "reject_closed_contract_reference",
              "policy_reason": "source is already a closed contract evidence document",
              "radar_score": 299,
              "signals": {
                "aios": 10,
                "blocker": 4,
                "capabilityos": 12,
                "contract": 12,
                "hivemind": 12,
                "memoryos": 12,
                "stop_condition": 4,
                "verify": 12
              }
            },
            {
              "alignment_reasons": [
                "increases_repeatability",
                "increases_verified_execution",
                "verification_signal"
              ],
              "blocked": true,
              "blocked_reasons": [
                "closed_contract_source",
                "reject_closed_contract_reference"
              ],
              "candidate_task": "promote this control-plane signal into an AIOS contract or readiness gate",
              "domain": "myworld",
              "goal_score": 290,
              "path": "myworld/docs/contracts/ASC-0004-dispatch-watcher-and-state-machine.md",
              "policy_decision": "reject_closed_contract_reference",
              "policy_reason": "source is already a closed contract evidence document",
              "radar_score": 264,
              "signals": {
                "aios": 12,
                "capabilityos": 4,
                "contract": 12,
                "gap": 3,
                "hivemind": 8,
                "memoryos": 10,
                "stop_condition": 6,
                "verify": 12
              }
            },
            {
              "alignment_reasons": [
                "verification_signal",
                "capability_dependency"
              ],
              "blocked": true,
              "blocked_reasons": [
                "index_source_requires_triage",
                "hold_for_capability"
              ],
              "candidate_task": "promote this control-plane signal into an AIOS contract or readiness gate",
              "domain": "myworld",
              "goal_score": 288,
              "path": "myworld/docs/AIOS_AGENT_LEDGER.md",
              "policy_decision": "hold_for_capability",
              "policy_reason": "capability gap signal must route through CapabilityOS first",
              "radar_score": 297,
              "signals": {
                "aios": 12,
                "blocker": 1,
                "capabilityos": 11,
                "contract": 12,
                "gap": 1,
                "hivemind": 12,
                "memoryos": 12,
                "next": 9,
                "stop_condition": 1,
                "verify": 9
              }
            },
            {
              "alignment_reasons": [
                "verification_signal"
              ],
              "blocked": true,
              "blocked_reasons": [
                "closed_contract_source",
                "reject_closed_contract_reference"
              ],
              "candidate_task": "promote this control-plane signal into an AIOS contract or readiness gate",
              "domain": "myworld",
              "goal_score": 277,
              "path": "myworld/docs/contracts/ASC-0020-hive-worklog-gap-cleanup.md",
              "policy_decision": "reject_closed_contract_reference",
              "policy_reason": "source is already a closed contract evidence document",
              "radar_score": 271,
              "signals": {
                "aios": 3,
                "capabilityos": 3,
                "contract": 12,
                "gap": 8,
                "hivemind": 12,
                "memoryos": 3,
                "next": 8,
                "stop_condition": 3,
                "todo": 5,
                "verify": 6
              }
            }
          ]
        },
        "returncode": 0,
        "status": "passed",
        "stderr_tail": "",
        "timed_out": false
      },
      "monitor": {
        "error": "",
        "name": "monitor",
        "parsed": {
          "findings": [
            {
              "action": "collect_result_or_run_watcher",
              "alert": {
                "code": "dispatch_results_pending",
                "dispatch_id": "asc-0040",
                "repos": [
                  "myworld"
                ]
              },
              "code": "dispatch_results_pending",
              "owner": "myworld",
              "reason": "A sent dispatch has no collected result packet for at least one target repo.",
              "severity": "high"
            }
          ],
          "generated_at": "2026-05-12T18:34:11+09:00",
          "health": "blocked",
          "next_actions": [
            {
              "action": "collect_result_or_run_watcher",
              "owner": "myworld",
              "reason": "A sent dispatch has no collected result packet for at least one target repo.",
              "severity": "high"
            }
          ],
          "schema_version": "aios.monitor.assessment.v1",
          "snapshot_generated_at": "2026-05-12T18:34:11+09:00",
          "watched": {
            "alerts": 1,
            "contracts": 40,
            "dispatches": 33,
            "reconciliations_applied": 1,
            "repos": 3
          }
        },
        "returncode": 0,
        "status": "passed",
        "stderr_tail": "",
        "timed_out": false
      }
    }
  },
  "schema_version": "aios.control_snapshot.v1",
  "stop_lanes": {
    "items": [
      {
        "contracts": [
          "ASC-0033"
        ],
        "name": "`audit_gap`: readiness can pass without ledger/evidence artifacts."
      },
      {
        "contracts": [
          "ASC-0038"
        ],
        "name": "`capability_binding_without_review`: route binds or installs tools instead of recommending."
      },
      {
        "contracts": [
          "ASC-0031"
        ],
        "name": "`capability_route_missing`: receipt does not reference the CapabilityOS `web-route` plan."
      },
      {
        "contracts": [
          "ASC-0036",
          "ASC-0035",
          "ASC-0034"
        ],
        "name": "`child_repo_scope_leak`"
      },
      {
        "contracts": [
          "ASC-0033"
        ],
        "name": "`child_repo_scope_leak`: this contract edits child repo source."
      },
      {
        "contracts": [
          "ASC-0040"
        ],
        "name": "`child_repo_source_edit`"
      },
      {
        "contracts": [
          "ASC-0039"
        ],
        "name": "`child_repo_source_edit`: implementation changes child repo source."
      },
      {
        "contracts": [
          "ASC-0037"
        ],
        "name": "`child_repo_source_edit`: this contract changes child repo source."
      },
      {
        "contracts": [
          "ASC-0039"
        ],
        "name": "`dependency_sprawl`: contract adds a framework or package manager before the static surface proves useful."
      },
      {
        "contracts": [
          "ASC-0038"
        ],
        "name": "`direct_child_repo_edit`: myworld patches child implementation files instead of issuing a packet."
      },
      {
        "contracts": [
          "ASC-0037"
        ],
        "name": "`english_pattern_regression`: existing English patterns no longer match."
      },
      {
        "contracts": [
          "ASC-0037"
        ],
        "name": "`fallback_loop`: fallback agent (claude) also fails with same category and watcher recurses without bound."
      }
    ]
  }
};

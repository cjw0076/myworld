window.AIOS_CONTROL_SNAPSHOT = {
  "aios_inputs": {
    "capability_routes": [
      "cap_quickstartdemo_"
    ],
    "hive_runs": [],
    "memory_traces": []
  },
  "completion": {
    "checked_at": "2026-05-17T11:36:04+09:00",
    "criteria": [
      {
        "criterion": "1. autopoietic loop closed + always-on",
        "evidence": "round controller running=True, last_round=2026-05-17T11:36:03+09:00, dream+local_operator organs ran=True",
        "met": true
      },
      {
        "criterion": "2. sovereignty readiness = 1.0",
        "evidence": "sovereignty readiness = 1.0",
        "met": true,
        "partial": true
      },
      {
        "criterion": "3. DNA invariants deterministic",
        "evidence": "AIOS_DNA.md present=True, authority model=True",
        "met": true
      },
      {
        "criterion": "4. delegable via MCP",
        "evidence": "aios_mcp_server.py=True, .mcp.json=True",
        "met": true
      },
      {
        "criterion": "5. personal / 1인 1 AIOS",
        "evidence": "install=True, workbench=True, model-agnostic tiers=True",
        "met": true
      }
    ],
    "criteria_met": "5/5",
    "fully_sovereign": true,
    "schema": "aios.completion.v1",
    "self_maintaining": true,
    "verdict": "AIOS COMPLETE — fully sovereign and self-maintaining"
  },
  "contracts": {
    "counts": {
      "accepted": 6,
      "closed": 155,
      "proposed": 10,
      "superseded": 1,
      "superseded-by-rewrite": 7,
      "withdrawn": 8
    },
    "latest": [
      {
        "accepted": "2026-05-17 05:40 KST",
        "closed": "",
        "created": "2026-05-17 05:35 KST",
        "goal": "Replace bare file-drop dispatch with a leased jobs queue — kind + job_key + lease_until + retry_remaining + ownership_token — so concurrent watchers cannot double-claim work or collide on IDs.",
        "id": "ASC-0185",
        "path": "docs/contracts/ASC-0185-leased-jobs-queue.md",
        "slug": "leased-jobs-queue",
        "status": "accepted",
        "stop_conditions": [
          "Migration risk: existing in-flight `.aios/inbox` packets must be adopted into the queue without loss → ship a one-time adopt step; do not strand live packets.",
          "If atomic rename is unavailable on the target filesystem → fall back to a lock file, do not silently drop the lease guarantee."
        ]
      },
      {
        "accepted": "2026-05-17 05:40 KST",
        "closed": "",
        "created": "2026-05-17 05:35 KST",
        "goal": "Add a deterministic enforcement layer — pre-action hooks that hard-block any action violating a DNA invariant or contract scope, regardless of model intent — so AIOS invariants are binding, not advisory.",
        "id": "ASC-0184",
        "path": "docs/contracts/ASC-0184-hooks-deterministic-enforcement.md",
        "slug": "hooks-deterministic-enforcement",
        "status": "accepted",
        "stop_conditions": [
          "A hook would block the autopoietic loop on a false positive → the soft checks fail-open and log; only the privacy hook fails-closed.",
          "Enforcement conflicts with an accepted contract → escalate, do not silently override the contract."
        ]
      },
      {
        "accepted": "",
        "closed": "",
        "created": "2026-05-17 03:35 KST",
        "goal": "Build dream phase 2 — periodic parametric self-evolution that re-fits a per-repo LoRA adapter from each OS's verified-good experience and hot-swaps it on context switch. The named heavier follow-on already declared in scripts/aios_self_evolve.py.",
        "id": "ASC-0183",
        "path": "docs/contracts/ASC-0183-dream-parametric-per-repo-adapters.md",
        "slug": "dream-parametric-per-repo-adapters",
        "status": "proposed",
        "stop_conditions": [
          "No GPU and CPU re-fit exceeds the round budget → ship phase 1 only, hold phase 2 until hardware is present (do not block the autopoietic loop).",
          "A re-fit adapter regresses on held-out verified invocations → discard the draft, keep the prior adapter, record the regression as negative evidence."
        ]
      },
      {
        "accepted": "2026-05-17 03:35 KST",
        "closed": "2026-05-17 03:55 KST",
        "created": "2026-05-17 03:35 KST",
        "goal": "Execute the first synthetic matched-run benchmark fixture per ASC-0162's protocol — validate the measurement protocol on real task pairs and feed executed numbers into the AIOS utility paper.",
        "id": "ASC-0182",
        "path": "docs/contracts/ASC-0182-first-matched-run-benchmark-execution.md",
        "slug": "first-matched-run-benchmark-execution",
        "status": "closed",
        "stop_conditions": [
          "A fixture requires private data → stop, redesign fixture.",
          "A matched pair cannot hold provider/model/snapshot constant → exclude the pair per the protocol's Exclusions, do not fabricate a substitute."
        ]
      },
      {
        "accepted": "2026-05-16 KST by claude@myworld — founder GO \"B surface 계약 착수\"; Model B is local-first (no DNA trust-model change), surface consolidation of already-closed contracts (ASC-0080, ASC-0156)",
        "closed": "2026-05-16 KST — Packet A done (registry-based emit eligibility, aios_emit_recap.py, non-uri repo demoagent flowed end-to-end, unregistered repo rejected, 9/9 tests pass); Packets B-E named",
        "created": "2026-05-16 KST",
        "goal": "Consolidate the scattered Model B seeds (native install, Control Center, chat, ingest server) into `aios-workbench` — a coherent local-first developer product where a developer points AIOS at their own agent project, that project emits recap packets, and AIOS observes/absorbs/recommends. Local-first, so no hosting decision (ASC-0180) is needed for Model B.",
        "id": "ASC-0181",
        "path": "docs/contracts/ASC-0181-aios-workbench-developer-product.md",
        "slug": "aios-workbench-developer-product",
        "status": "closed",
        "stop_conditions": [
          "The workbench forks the substrate (`aios-core` must stay single).",
          "A hosting / non-localhost surface is added (that is Model A / ASC-0180).",
          "The emit registry is used to bypass the ASC-0173 consent gate — every emitted packet still carries the exact consent string."
        ]
      },
      {
        "accepted": "2026-05-15 KST by claude@myworld for deliberation dispatch — founder explicitly routed the hosting commitment to Hive (\"호스팅은 Hive 심의로 보냄\"). Final verdict acceptance reserved to founder.",
        "closed": "",
        "created": "2026-05-15 KST",
        "goal": "Run a Hive deliberation (ASC-0084 / ASC-0174 format, 6+ rounds, 3 voices) on the question \"how should AIOS hosting relate to the DNA — specifically the Preamble root-of-trust clause and Invariant 7 (privacy boundary) — given that Model A (invisible infra under uri) needs a non-localhost ingest endpoint to serve production users, but any non-localhost AIOS surface is the first AIOS component that is not local-first?\"",
        "id": "ASC-0180",
        "path": "docs/contracts/ASC-0180-hive-debate-aios-hosting-trust-model.md",
        "slug": "hive-debate-aios-hosting-trust-model",
        "status": "accepted",
        "stop_conditions": [
          "`early_convergence`: < 6 rounds",
          "`single_voice`: any round < 3 distinct voices",
          "`probe_skipped`: any of 9 probes unaddressed",
          "`implementation_creep`: this contract spawns deployment manifests or hosting code",
          "`verification_gate_failed`"
        ]
      },
      {
        "accepted": "2026-05-15 KST by claude@myworld under delegated authority — local-first protocol work, no DNA trust-model change, no hosting commitment, no founder escalation rule triggered",
        "closed": "2026-05-15 KST — 4/4 stop conditions met: schema doc, loopback-only server, 8/8 tests pass, http-fed packet URI-212 flowed end-to-end",
        "created": "2026-05-15 KST",
        "goal": "Turn the `.aios/inbox` filesystem-drop dispatch boundary into an HTTP-shaped ingest protocol that works local-first (localhost) and is hosting-ready, so both Model A (AIOS as invisible infra under uri) and Model B (AIOS as installable dev product) can serve end users on the same protocol. No hosting commitment — protocol only.",
        "id": "ASC-0179",
        "path": "docs/contracts/ASC-0179-aios-ingest-protocol-local-first.md",
        "slug": "aios-ingest-protocol-local-first",
        "status": "closed",
        "stop_conditions": [
          "The server binds anything other than `127.0.0.1` (that is the hosting decision, reserved to ASC-0180).",
          "Auth, TLS, or multi-tenant code appears (same reason).",
          "A second, divergent ingestion path is created instead of reusing the ASC-0173 pipeline."
        ]
      },
      {
        "accepted": "2026-05-15 KST by claude@myworld — phase 1 explicitly authorized by founder GO on the ASC-0174 verdict (\"verdict accept, phase 1 착수\")",
        "closed": "2026-05-15 KST — all 4 stop conditions met (DNA amendment, Packet A 14 contracts reconciled, Packet B policy rule, Packet C 5 follow-ons named)",
        "created": "2026-05-15 KST",
        "goal": "Execute phase 1 of the ASC-0174 verdict (`proceed_authority_routed_management_plane`) — land the authority-model vocabulary in the DNA, reconcile the ASC-0128..0177 permission-chain contracts under retain/rewrite/withdraw, and name the remaining phase-1 downstream work as packets.",
        "id": "ASC-0178",
        "path": "docs/contracts/ASC-0178-aios-authority-model-phase-1.md",
        "slug": "aios-authority-model-phase-1",
        "status": "closed",
        "stop_conditions": [
          "Any reconciliation flip deletes a contract instead of setting a status.",
          "A 15th \"Bind ASC-0066...\" template clone is autodrafted while this contract is open (signals Packet B did not bind).",
          "The retain/rewrite/withdraw classification is applied without individually reading the contract (the table is provisional, not authoritative)."
        ]
      },
      {
        "accepted": "",
        "closed": "",
        "created": "2026-05-15T15:54:59+09:00",
        "goal": "Bind ASC-0066 provider backpressure role capsules to an executable, verified fallback path that can hand work to Claude, Codex, Gemini, or a local LLM without bypassing Hive verification.",
        "id": "ASC-0177",
        "path": "docs/contracts/ASC-0177-provider-fallback-execution-binding-hivemind-child-watcher-held-since-2026-05-14-13-10-kst-du-d6492719.md",
        "slug": "provider-fallback-execution-binding-hivemind-child-watcher-held-since-2026-05-14-13-10-kst-du-d6492719",
        "status": "withdrawn",
        "stop_conditions": [
          "`fallback_executes_without_contract`",
          "`provider_secret_leak`",
          "`role_capsule_missing_rubric`",
          "`local_llm_used_as_final_acceptor_without_verifier`",
          "`verification_gate_failed`",
          "`operator_acceptance_missing`",
          "`scope_not_narrowed_before_dispatch`"
        ]
      },
      {
        "accepted": "",
        "closed": "",
        "created": "2026-05-15T15:47:53+09:00",
        "goal": "Bind ASC-0066 provider backpressure role capsules to an executable, verified fallback path that can hand work to Claude, Codex, Gemini, or a local LLM without bypassing Hive verification.",
        "id": "ASC-0176",
        "path": "docs/contracts/ASC-0176-provider-fallback-execution-binding-capabilityos-genesisos-not-enrolled-in-repo-goal-submission-p-d04277ad.md",
        "slug": "provider-fallback-execution-binding-capabilityos-genesisos-not-enrolled-in-repo-goal-submission-p-d04277ad",
        "status": "withdrawn",
        "stop_conditions": [
          "`fallback_executes_without_contract`",
          "`provider_secret_leak`",
          "`role_capsule_missing_rubric`",
          "`local_llm_used_as_final_acceptor_without_verifier`",
          "`verification_gate_failed`",
          "`operator_acceptance_missing`",
          "`scope_not_narrowed_before_dispatch`"
        ]
      }
    ],
    "total": 187
  },
  "dispatches": {
    "counts": {
      "collected": 77,
      "created": 3,
      "passed": 3,
      "released": 104,
      "retried": 1,
      "sent": 4,
      "skipped": 13
    },
    "latest": [
      {
        "collected": [],
        "contract_id": "ASC-0116",
        "dispatch_id": "asc-0116",
        "goal": "Stop round_controller from blocking dispatch when monitor health=attention is caused by codex's own active work (e.g. memoryOS dirty during ASC-0111 implementation). Distinguish \"attention because something is broken\" from \"attention because someone is working\" so AIOS doesn't self-throttle while working.",
        "reason": "send_error:ValueError",
        "sent": [],
        "status": "skipped",
        "timestamp": "2026-05-17T04:05:17+09:00"
      },
      {
        "collected": [],
        "contract_id": "ASC-0117",
        "dispatch_id": "asc-0117",
        "goal": "Distinguish \"accepted but waiting\" from \"actively in-progress\" in ASC-0011 capacity policy. Today open_count=22 vs capacity=4 means verifier-issued contracts wait 2-3 hours before dispatch. Founder /loop directs continuous contract issue → policy creates artificial gridlock between issuance and execution.",
        "reason": "send_error:ValueError",
        "sent": [],
        "status": "skipped",
        "timestamp": "2026-05-17T04:05:17+09:00"
      },
      {
        "collected": [
          "hivemind"
        ],
        "contract_id": "ASC-0180",
        "dispatch_id": "asc-0180",
        "goal": "Run a Hive deliberation (ASC-0084 / ASC-0174 format, 6+ rounds, 3 voices) on the question \"how should AIOS hosting relate to the DNA — specifically the Preamble root-of-trust clause and Invariant 7 (privacy boundary) — given that Model A (invisible infra under uri) needs a non-localhost ingest endpoint to serve production users, but any non-localhost AIOS surface is the first AIOS component that is not local-first?\"",
        "reason": "policy_held_checkpoint",
        "sent": [
          "hivemind"
        ],
        "status": "skipped",
        "timestamp": "2026-05-17T04:05:17+09:00"
      },
      {
        "collected": [],
        "contract_id": "ASC-0182",
        "dispatch_id": "asc-0182",
        "goal": "Execute the first synthetic matched-run benchmark fixture per ASC-0162's protocol — validate the measurement protocol on real task pairs and feed executed numbers into the AIOS utility paper.",
        "reason": "",
        "sent": [
          "myworld"
        ],
        "status": "sent",
        "timestamp": "2026-05-17T02:36:25+09:00"
      },
      {
        "collected": [
          "hivemind"
        ],
        "contract_id": "ASC-0180",
        "dispatch_id": "asc-0180-r2",
        "goal": "Run a Hive deliberation (ASC-0084 / ASC-0174 format, 6+ rounds, 3 voices) on the question \"how should AIOS hosting relate to the DNA — specifically the Preamble root-of-trust clause and Invariant 7 (privacy boundary) — given that Model A (invisible infra under uri) needs a non-localhost ingest endpoint to serve production users, but any non-localhost AIOS surface is the first AIOS component that is not local-first?\"",
        "reason": "",
        "sent": [
          "hivemind"
        ],
        "status": "collected",
        "timestamp": "2026-05-16T13:55:34+09:00"
      },
      {
        "collected": [
          "myworld"
        ],
        "contract_id": null,
        "dispatch_id": "aios-feedback-run_20260516_115153_0888e2-gen00",
        "goal": null,
        "reason": "",
        "sent": [],
        "status": "collected",
        "timestamp": "2026-05-16T11:52:18+09:00"
      },
      {
        "collected": [
          "myworld"
        ],
        "contract_id": null,
        "dispatch_id": "aios-feedback-run_20260516_115155_d24976-gen00",
        "goal": null,
        "reason": "",
        "sent": [],
        "status": "collected",
        "timestamp": "2026-05-16T11:52:18+09:00"
      },
      {
        "collected": [
          "myworld"
        ],
        "contract_id": null,
        "dispatch_id": "aios-feedback-run_20260516_114604_b5d071-gen00",
        "goal": null,
        "reason": "",
        "sent": [],
        "status": "collected",
        "timestamp": "2026-05-16T11:46:34+09:00"
      },
      {
        "collected": [
          "myworld"
        ],
        "contract_id": null,
        "dispatch_id": "aios-feedback-run_20260516_114606_9d3d84-gen00",
        "goal": null,
        "reason": "",
        "sent": [],
        "status": "collected",
        "timestamp": "2026-05-16T11:46:34+09:00"
      },
      {
        "collected": [
          "myworld"
        ],
        "contract_id": null,
        "dispatch_id": "aios-feedback-run_20260516_114052_f096f3-gen00",
        "goal": null,
        "reason": "",
        "sent": [],
        "status": "collected",
        "timestamp": "2026-05-16T11:41:24+09:00"
      },
      {
        "collected": [
          "myworld"
        ],
        "contract_id": null,
        "dispatch_id": "aios-feedback-run_20260516_114053_bd1d0c-gen00",
        "goal": null,
        "reason": "",
        "sent": [],
        "status": "collected",
        "timestamp": "2026-05-16T11:41:24+09:00"
      },
      {
        "collected": [
          "myworld"
        ],
        "contract_id": null,
        "dispatch_id": "aios-feedback-run_20260516_113600_aeccdd-gen00",
        "goal": null,
        "reason": "",
        "sent": [],
        "status": "collected",
        "timestamp": "2026-05-16T11:36:15+09:00"
      }
    ],
    "timeline": [
      {
        "dispatch_id": "asc-0117",
        "event": "policy_dispatch_decision",
        "repo": null,
        "status": "selected",
        "timestamp": "2026-05-17T00:33:05+09:00"
      },
      {
        "dispatch_id": "asc-0117",
        "event": "policy_dispatch_decision",
        "repo": "myworld",
        "status": "skipped",
        "timestamp": "2026-05-17T00:33:05+09:00"
      },
      {
        "dispatch_id": "asc-0180",
        "event": "policy_dispatch_decision",
        "repo": null,
        "status": "skipped",
        "timestamp": "2026-05-17T00:33:05+09:00"
      },
      {
        "dispatch_id": "asc-0116",
        "event": "policy_dispatch_decision",
        "repo": null,
        "status": "selected",
        "timestamp": "2026-05-17T01:28:23+09:00"
      },
      {
        "dispatch_id": "asc-0116",
        "event": "policy_dispatch_decision",
        "repo": "myworld",
        "status": "skipped",
        "timestamp": "2026-05-17T01:28:23+09:00"
      },
      {
        "dispatch_id": "asc-0117",
        "event": "policy_dispatch_decision",
        "repo": null,
        "status": "selected",
        "timestamp": "2026-05-17T01:28:23+09:00"
      },
      {
        "dispatch_id": "asc-0117",
        "event": "policy_dispatch_decision",
        "repo": "myworld",
        "status": "skipped",
        "timestamp": "2026-05-17T01:28:23+09:00"
      },
      {
        "dispatch_id": "asc-0180",
        "event": "policy_dispatch_decision",
        "repo": null,
        "status": "skipped",
        "timestamp": "2026-05-17T01:28:23+09:00"
      },
      {
        "dispatch_id": "asc-0116",
        "event": "policy_dispatch_decision",
        "repo": null,
        "status": "selected",
        "timestamp": "2026-05-17T01:40:24+09:00"
      },
      {
        "dispatch_id": "asc-0116",
        "event": "policy_dispatch_decision",
        "repo": "myworld",
        "status": "skipped",
        "timestamp": "2026-05-17T01:40:24+09:00"
      },
      {
        "dispatch_id": "asc-0117",
        "event": "policy_dispatch_decision",
        "repo": null,
        "status": "selected",
        "timestamp": "2026-05-17T01:40:24+09:00"
      },
      {
        "dispatch_id": "asc-0117",
        "event": "policy_dispatch_decision",
        "repo": "myworld",
        "status": "skipped",
        "timestamp": "2026-05-17T01:40:24+09:00"
      },
      {
        "dispatch_id": "asc-0180",
        "event": "policy_dispatch_decision",
        "repo": null,
        "status": "skipped",
        "timestamp": "2026-05-17T01:40:24+09:00"
      },
      {
        "dispatch_id": "asc-0116",
        "event": "policy_dispatch_decision",
        "repo": null,
        "status": "selected",
        "timestamp": "2026-05-17T02:14:12+09:00"
      },
      {
        "dispatch_id": "asc-0116",
        "event": "policy_dispatch_decision",
        "repo": "myworld",
        "status": "skipped",
        "timestamp": "2026-05-17T02:14:12+09:00"
      },
      {
        "dispatch_id": "asc-0117",
        "event": "policy_dispatch_decision",
        "repo": null,
        "status": "selected",
        "timestamp": "2026-05-17T02:14:12+09:00"
      },
      {
        "dispatch_id": "asc-0117",
        "event": "policy_dispatch_decision",
        "repo": "myworld",
        "status": "skipped",
        "timestamp": "2026-05-17T02:14:12+09:00"
      },
      {
        "dispatch_id": "asc-0180",
        "event": "policy_dispatch_decision",
        "repo": null,
        "status": "skipped",
        "timestamp": "2026-05-17T02:14:12+09:00"
      },
      {
        "dispatch_id": "asc-0116",
        "event": "policy_dispatch_decision",
        "repo": null,
        "status": "selected",
        "timestamp": "2026-05-17T02:32:24+09:00"
      },
      {
        "dispatch_id": "asc-0116",
        "event": "policy_dispatch_decision",
        "repo": "myworld",
        "status": "skipped",
        "timestamp": "2026-05-17T02:32:25+09:00"
      },
      {
        "dispatch_id": "asc-0117",
        "event": "policy_dispatch_decision",
        "repo": null,
        "status": "selected",
        "timestamp": "2026-05-17T02:32:25+09:00"
      },
      {
        "dispatch_id": "asc-0117",
        "event": "policy_dispatch_decision",
        "repo": "myworld",
        "status": "skipped",
        "timestamp": "2026-05-17T02:32:25+09:00"
      },
      {
        "dispatch_id": "asc-0180",
        "event": "policy_dispatch_decision",
        "repo": null,
        "status": "skipped",
        "timestamp": "2026-05-17T02:32:25+09:00"
      },
      {
        "dispatch_id": "asc-0182",
        "event": "created",
        "repo": null,
        "status": "created",
        "timestamp": "2026-05-17T02:36:25+09:00"
      },
      {
        "dispatch_id": "asc-0182",
        "event": "sent",
        "repo": "myworld",
        "status": "sent",
        "timestamp": "2026-05-17T02:36:25+09:00"
      },
      {
        "dispatch_id": "asc-0116",
        "event": "policy_dispatch_decision",
        "repo": null,
        "status": "selected",
        "timestamp": "2026-05-17T04:05:17+09:00"
      },
      {
        "dispatch_id": "asc-0116",
        "event": "policy_dispatch_decision",
        "repo": "myworld",
        "status": "skipped",
        "timestamp": "2026-05-17T04:05:17+09:00"
      },
      {
        "dispatch_id": "asc-0117",
        "event": "policy_dispatch_decision",
        "repo": null,
        "status": "selected",
        "timestamp": "2026-05-17T04:05:17+09:00"
      },
      {
        "dispatch_id": "asc-0117",
        "event": "policy_dispatch_decision",
        "repo": "myworld",
        "status": "skipped",
        "timestamp": "2026-05-17T04:05:17+09:00"
      },
      {
        "dispatch_id": "asc-0180",
        "event": "policy_dispatch_decision",
        "repo": null,
        "status": "skipped",
        "timestamp": "2026-05-17T04:05:17+09:00"
      }
    ],
    "total": 205
  },
  "friction_radar": {
    "items": [
      {
        "need": "collect_result_or_run_watcher",
        "owner": "myworld",
        "reason": "A sent dispatch has no collected result packet for at least one target repo.",
        "severity": "high",
        "source": "monitor"
      },
      {
        "need": "hold_for_repo_owner_triage",
        "owner": "CapabilityOS",
        "reason": "A child repo has uncommitted changes that need owner review before new work is stacked on it.",
        "severity": "medium",
        "source": "monitor"
      },
      {
        "need": "hold_for_repo_owner_triage",
        "owner": "GenesisOS",
        "reason": "A child repo has uncommitted changes that need owner review before new work is stacked on it.",
        "severity": "medium",
        "source": "monitor"
      },
      {
        "need": "review_prompt_prison_escape_vectors",
        "owner": "GenesisOS",
        "reason": "GenesisOS critic found advisory prompt-prison signatures in open contracts.",
        "severity": "info",
        "source": "monitor"
      }
    ]
  },
  "generated_at": "2026-05-17T11:36:03+09:00",
  "genesis_lens": {
    "authority": "speculative_only",
    "branches": [
      {
        "branch_id": "inversion-provider",
        "contract_seed": "Explore `inversion` mutation for: provider 실패 기억은?",
        "premise": "Assume the stated goal is a symptom, not the target.",
        "risk": "Speculative branch. Requires MyWorld contract before execution.",
        "type": "inversion",
        "what_it_breaks": "Breaks literal prompt obedience.",
        "why_it_might_matter": "The useful system may be the one that refuses premature completion."
      },
      {
        "branch_id": "alien_domain-provider",
        "contract_seed": "Explore `alien_domain` mutation for: provider 실패 기억은?",
        "premise": "Treat the goal like city planning, not software delivery.",
        "risk": "Speculative branch. Requires MyWorld contract before execution.",
        "type": "alien_domain",
        "what_it_breaks": "Breaks repo-shaped thinking.",
        "why_it_might_matter": "Infrastructure, rituals, and zoning may matter more than features."
      },
      {
        "branch_id": "constraint_removal-provider",
        "contract_seed": "Explore `constraint_removal` mutation for: provider 실패 기억은?",
        "premise": "Temporarily remove the requirement that every idea be testable today.",
        "risk": "Speculative branch. Requires MyWorld contract before execution.",
        "type": "constraint_removal",
        "what_it_breaks": "Breaks verification-first convergence.",
        "why_it_might_matter": "A non-testable branch can still become a contract seed later."
      },
      {
        "branch_id": "failure_as_feature-provider",
        "contract_seed": "Explore `failure_as_feature` mutation for: provider 실패 기억은?",
        "premise": "Treat the current failure mode as the product's strongest signal.",
        "risk": "Speculative branch. Requires MyWorld contract before execution.",
        "type": "failure_as_feature",
        "what_it_breaks": "Breaks the habit of hiding friction.",
        "why_it_might_matter": "Provider limits, prompt limits, and human limits reveal OS boundaries."
      },
      {
        "branch_id": "anti_user_prompt-provider",
        "contract_seed": "Explore `anti_user_prompt` mutation for: provider 실패 기억은?",
        "premise": "Resist the literal request and infer the unstated need behind it.",
        "risk": "Speculative branch. Requires MyWorld contract before execution.",
        "type": "anti_user_prompt",
        "what_it_breaks": "Breaks compliance-as-creativity.",
        "why_it_might_matter": "The next valuable move may be to change the question."
      }
    ],
    "source_artifact": ".aios/invocations/chat-ae0b74ec9f46bf2c/genesis/branches.json",
    "source_invocation": "chat-ae0b74ec9f46bf2c",
    "stop_conditions": [
      "no_execution_authority",
      "no_memory_acceptance",
      "no_capability_routing",
      "reject_unsafe_real_world_action"
    ]
  },
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
      "preferred_next": [],
      "slug": "make-something-great",
      "status": "active"
    },
    "evolution": {
      "monitor_health": "clear",
      "path": "docs/goals/AIOS-GOAL-0001-evolution.md",
      "readiness": "L6 repeatable",
      "recommendation": "myworld/hivemind/docs/RADAR_GAP_TRIAGE.md"
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
        "preferred_next": [],
        "slug": "make-something-great",
        "status": "active"
      },
      {
        "completed": [],
        "id": "AIOS-GOAL-0001-paper5-p20-genesis-plan",
        "north_star": [],
        "path": "docs/goals/AIOS-GOAL-0001-paper5-p20-genesis-plan.md",
        "preferred_next": [],
        "slug": "AIOS-GOAL-0001-paper5-p20-genesis-plan",
        "status": "unknown"
      }
    ]
  },
  "installation": {
    "command": {
      "available": false,
      "launcher_installed": false,
      "path": ""
    },
    "commands": [
      "aios install",
      "aios open",
      "aios status --json",
      "aios stop"
    ],
    "control_center": {
      "running": false,
      "url": "http://127.0.0.1:8765/",
      "websocket_running": false
    },
    "gate_chair": {
      "candidate_config": {
        "command_available": true,
        "fallback_expected": null,
        "mode": "claude",
        "model": "claude-opus-4-6",
        "path": ".aios/gate/founder/chair_candidate_runtime.json",
        "status": "candidate",
        "updated_at": "2026-05-16T14:15:25+09:00"
      },
      "candidate_config_active": true,
      "detail": "chair_runtime.json",
      "enabled": true,
      "gate_pack_active": true,
      "gate_pack_id": "gatepack_3e4a537ceb2b1516",
      "latest_turn": {
        "created_at": "2026-05-17T11:34:29+09:00",
        "executed": true,
        "mode": "claude",
        "model": "claude-opus-4-6",
        "path": ".aios/chat/gate-chair-eval-177e8627e75a4e6e-current-4/gate_chair_turns.jsonl",
        "status": "success"
      },
      "mode": "internal_evidence_synthesizer",
      "runtime_config": {
        "mode": "internal_evidence_synthesizer",
        "model": "",
        "path": ".aios/gate/founder/chair_runtime.json",
        "status": "active",
        "updated_at": "2026-05-16T14:10:29+09:00"
      },
      "runtime_config_active": true,
      "state": "internal"
    },
    "headline": "AIOS can be installed.",
    "loop": {
      "latest_next": "hold_for_monitor",
      "latest_status": "passed",
      "running": true
    },
    "service": {
      "active": false,
      "enabled": "not-found",
      "installed": false,
      "state": {
        "active": "inactive",
        "available": true,
        "enabled": "not-found"
      }
    },
    "status": "ready_to_install",
    "targets": {
      "desktop": {
        "exists": false,
        "managed": false,
        "path": "/home/user/.config/autostart/aios-control.desktop"
      },
      "launcher": {
        "exists": false,
        "managed": false,
        "path": "/home/user/.local/bin/aios"
      },
      "service": {
        "exists": false,
        "managed": false,
        "path": "/home/user/.config/systemd/user/aios.service"
      }
    }
  },
  "invocations": {
    "latest": [
      {
        "artifact_previews": {
          "capability_route": {
            "path": ".aios/invocations/chat-ae0b74ec9f46bf2c/capability/route.json",
            "preview": "{ \"contract\": \"capabilityos.recommendations.v1\", \"observed_capabilities\": 0, \"recommendation_only\": true, \"recommendations\": [ { \"actions\": [ \"recommend\", \"schema-check\", \"freshness-check\", \"cite\", \"fallback\" ], \"confidence\": 0.6, \"cost\": \"free\", \"description\": \"Maps API capability contracts, freshness requirements, and privacy limits for later executor review.\", \"domains\": [ \"aios\", \"api\", \"contract\", \"schema\", \"freshness\", \"provider\" ], \"evidence_refs\": [ \"../CapabilityOS/README.md\", \"../docs/AIOS_BUILD_METHOD.md",
            "truncated": true
          },
          "dispatch_packets": {
            "path": ".aios/invocations/chat-ae0b74ec9f46bf2c/dispatch/packets.json",
            "preview": "{ \"goal_hash\": \"d64125621308b950207faf196775db430b400b5c0b56c8f9a92730414407f800\", \"packets\": [ { \"mode\": \"local_cli\", \"role\": \"divergence\", \"target_repo\": \"GenesisOS\" }, { \"mode\": \"degraded_allowed\", \"role\": \"context\", \"target_repo\": \"memoryOS\" }, { \"mode\": \"recommendation_only\", \"role\": \"route\", \"target_repo\": \"CapabilityOS\" }, { \"mode\": \"plan_only\", \"role\": \"execution_plan\", \"target_repo\": \"hivemind\" } ], \"schema_version\": \"aios.dispatch_packets.v1\", \"status\": \"draft\" }",
            "truncated": false
          },
          "genesis": {
            "path": ".aios/invocations/chat-ae0b74ec9f46bf2c/genesis/branches.json",
            "preview": "{ \"authority\": \"speculative_only\", \"branches\": [ { \"branch_id\": \"inversion-provider\", \"contract_seed\": \"Explore `inversion` mutation for: provider 실패 기억은?\", \"premise\": \"Assume the stated goal is a symptom, not the target.\", \"risk\": \"Speculative branch. Requires MyWorld contract before execution.\", \"type\": \"inversion\", \"what_it_breaks\": \"Breaks literal prompt obedience.\", \"why_it_might_matter\": \"The useful system may be the one that refuses premature completion.\" }, { \"branch_id\": \"alien_domain-provider\", \"contract_",
            "truncated": true
          },
          "hive_execution_plan": {
            "path": ".aios/invocations/chat-ae0b74ec9f46bf2c/hive/execution_plan.json",
            "preview": "{ \"candidate_provider\": \"capabilityos_recommended\", \"candidate_worker\": \"hive.provider_loop\", \"contract_id\": null, \"execute_allowed\": false, \"goal_hash\": \"d64125621308b950207faf196775db430b400b5c0b56c8f9a92730414407f800\", \"owner_repo\": \"hivemind\", \"plan_only\": true, \"schema_version\": \"aios.hive_execution_plan.v1\", \"stop_conditions\": [ \"missing_required_artifact\", \"scope_violation\", \"provider_backpressure\", \"verification_gate_failed\" ], \"user_patterns\": { \"patterns\": [ { \"confidence\": 0.78, \"evidence_refs\": [ \"docs/",
            "truncated": true
          },
          "memory_context_pack": {
            "path": ".aios/invocations/chat-ae0b74ec9f46bf2c/memory/context_pack.md",
            "preview": "# Context pack Task: provider 실패 기억은? Role: hive ## Source - MemoryOS context build returned JSON. - selected_memory_ids: [\"mem_940ad99fcc2ed445\", \"mem_4a44670b379ca4ea\", \"mem_d0b64430dd5da2a8\", \"mem_5012d57c2c4acbf6\", \"mem_1f18cea463eed9fd\"] - trace_id: rtrace_28397e888283f266",
            "truncated": false
          },
          "memory_request": {
            "path": ".aios/invocations/chat-ae0b74ec9f46bf2c/memory/context_request.json",
            "preview": "{ \"auto_accept\": false, \"for_role\": \"hive\", \"goal_hash\": \"d64125621308b950207faf196775db430b400b5c0b56c8f9a92730414407f800\", \"project\": \"AIOS\", \"requested_outputs\": [ \"context_pack.md\", \"retrieval_trace\" ], \"schema_version\": \"aios.memory_context_request.v1\", \"task\": \"provider 실패 기억은?\" }",
            "truncated": false
          }
        },
        "created_at": "2026-05-17T11:34:07+09:00",
        "degraded_receipt": {
          "missing_or_degraded_roles": [],
          "status": "not_needed",
          "stop_conditions_triggered": []
        },
        "executor_assignment": {
          "default_executor": "codex",
          "execution_owner": "hivemind",
          "mode": "bounded_worker_packet",
          "requires_dispatch_packet": true,
          "requires_verification_result": true
        },
        "goal": "provider 실패 기억은?",
        "invocation_id": "chat-ae0b74ec9f46bf2c",
        "next_action": "dispatch_ready",
        "overall_status": "passed",
        "role_artifacts": {
          "capability_route": ".aios/invocations/chat-ae0b74ec9f46bf2c/capability/route.json",
          "dispatch_packets": ".aios/invocations/chat-ae0b74ec9f46bf2c/dispatch/packets.json",
          "genesis": ".aios/invocations/chat-ae0b74ec9f46bf2c/genesis/branches.json",
          "hive_execution_plan": ".aios/invocations/chat-ae0b74ec9f46bf2c/hive/execution_plan.json",
          "memory_context_pack": ".aios/invocations/chat-ae0b74ec9f46bf2c/memory/context_pack.md",
          "memory_request": ".aios/invocations/chat-ae0b74ec9f46bf2c/memory/context_request.json"
        },
        "role_statuses": {
          "capability": "passed",
          "genesis": "passed",
          "hive": "passed",
          "memory": "passed"
        },
        "session_envelope": ".aios/invocations/chat-ae0b74ec9f46bf2c/session_envelope.json"
      },
      {
        "artifact_previews": {
          "capability_route": {
            "path": ".aios/invocations/chat-df86e60a788ee549/capability/route.json",
            "preview": "{ \"contract\": \"capabilityos.recommendations.v1\", \"observed_capabilities\": 0, \"recommendation_only\": true, \"recommendations\": [ { \"actions\": [ \"once\", \"run\", \"start\", \"stop\", \"status\", \"drain\" ], \"confidence\": 0.65, \"cost\": \"free\", \"description\": \"Reads .aios/inbox/<repo>/*.json, spawns assigned-agent processes inside target repos, writes .aios/outbox/<repo>/*.result.json, and records held/pending_concurrent_work states. Used to drain pending packets that block higher AIOS readiness levels. Operator-controlled start",
            "truncated": true
          },
          "dispatch_packets": {
            "path": ".aios/invocations/chat-df86e60a788ee549/dispatch/packets.json",
            "preview": "{ \"goal_hash\": \"b072d04096bc154bb64da0b90ea13a38b394561b32d2abee98b540de83859d0c\", \"packets\": [ { \"mode\": \"local_cli\", \"role\": \"divergence\", \"target_repo\": \"GenesisOS\" }, { \"mode\": \"degraded_allowed\", \"role\": \"context\", \"target_repo\": \"memoryOS\" }, { \"mode\": \"recommendation_only\", \"role\": \"route\", \"target_repo\": \"CapabilityOS\" }, { \"mode\": \"plan_only\", \"role\": \"execution_plan\", \"target_repo\": \"hivemind\" } ], \"schema_version\": \"aios.dispatch_packets.v1\", \"status\": \"draft\" }",
            "truncated": false
          },
          "genesis": {
            "path": ".aios/invocations/chat-df86e60a788ee549/genesis/branches.json",
            "preview": "{ \"authority\": \"speculative_only\", \"branches\": [ { \"branch_id\": \"inversion-aios-gate-agent\", \"contract_seed\": \"Explore `inversion` mutation for: AIOS에는 gate 역할의 Agent가 있나? 아니면 시스템 답변밖에 못하나?\", \"premise\": \"Assume the stated goal is a symptom, not the target.\", \"risk\": \"Speculative branch. Requires MyWorld contract before execution.\", \"type\": \"inversion\", \"what_it_breaks\": \"Breaks literal prompt obedience.\", \"why_it_might_matter\": \"The useful system may be the one that refuses premature completion.\" }, { \"branch_id\": ",
            "truncated": true
          },
          "hive_execution_plan": {
            "path": ".aios/invocations/chat-df86e60a788ee549/hive/execution_plan.json",
            "preview": "{ \"candidate_provider\": \"capabilityos_recommended\", \"candidate_worker\": \"hive.provider_loop\", \"contract_id\": null, \"execute_allowed\": false, \"goal_hash\": \"b072d04096bc154bb64da0b90ea13a38b394561b32d2abee98b540de83859d0c\", \"owner_repo\": \"hivemind\", \"plan_only\": true, \"schema_version\": \"aios.hive_execution_plan.v1\", \"stop_conditions\": [ \"missing_required_artifact\", \"scope_violation\", \"provider_backpressure\", \"verification_gate_failed\" ], \"user_patterns\": { \"patterns\": [ { \"confidence\": 0.78, \"evidence_refs\": [ \"docs/",
            "truncated": true
          },
          "memory_context_pack": {
            "path": ".aios/invocations/chat-df86e60a788ee549/memory/context_pack.md",
            "preview": "# Context pack Task: AIOS에는 gate 역할의 Agent가 있나? 아니면 시스템 답변밖에 못하나? Role: hive ## Source - MemoryOS context build returned JSON. - selected_memory_ids: [\"mem_5012d57c2c4acbf6\", \"mem_001f6d5191fb8e51\"] - trace_id: rtrace_36a55d2279468acb",
            "truncated": false
          },
          "memory_request": {
            "path": ".aios/invocations/chat-df86e60a788ee549/memory/context_request.json",
            "preview": "{ \"auto_accept\": false, \"for_role\": \"hive\", \"goal_hash\": \"b072d04096bc154bb64da0b90ea13a38b394561b32d2abee98b540de83859d0c\", \"project\": \"AIOS\", \"requested_outputs\": [ \"context_pack.md\", \"retrieval_trace\" ], \"schema_version\": \"aios.memory_context_request.v1\", \"task\": \"AIOS에는 gate 역할의 Agent가 있나? 아니면 시스템 답변밖에 못하나?\" }",
            "truncated": false
          }
        },
        "created_at": "2026-05-17T11:33:22+09:00",
        "degraded_receipt": {
          "missing_or_degraded_roles": [],
          "status": "not_needed",
          "stop_conditions_triggered": []
        },
        "executor_assignment": {
          "default_executor": "codex",
          "execution_owner": "hivemind",
          "mode": "bounded_worker_packet",
          "requires_dispatch_packet": true,
          "requires_verification_result": true
        },
        "goal": "AIOS에는 gate 역할의 Agent가 있나? 아니면 시스템 답변밖에 못하나?",
        "invocation_id": "chat-df86e60a788ee549",
        "next_action": "dispatch_ready",
        "overall_status": "passed",
        "role_artifacts": {
          "capability_route": ".aios/invocations/chat-df86e60a788ee549/capability/route.json",
          "dispatch_packets": ".aios/invocations/chat-df86e60a788ee549/dispatch/packets.json",
          "genesis": ".aios/invocations/chat-df86e60a788ee549/genesis/branches.json",
          "hive_execution_plan": ".aios/invocations/chat-df86e60a788ee549/hive/execution_plan.json",
          "memory_context_pack": ".aios/invocations/chat-df86e60a788ee549/memory/context_pack.md",
          "memory_request": ".aios/invocations/chat-df86e60a788ee549/memory/context_request.json"
        },
        "role_statuses": {
          "capability": "passed",
          "genesis": "passed",
          "hive": "passed",
          "memory": "passed"
        },
        "session_envelope": ".aios/invocations/chat-df86e60a788ee549/session_envelope.json"
      },
      {
        "artifact_previews": {
          "capability_route": {
            "path": ".aios/invocations/chat-170565ae3554470e/capability/route.json",
            "preview": "{ \"contract\": \"capabilityos.recommendations.v1\", \"observed_capabilities\": 0, \"recommendation_only\": true, \"recommendations\": [ { \"actions\": [ \"run\", \"inspect\", \"verify\", \"demo\", \"memory-loop\" ], \"confidence\": 0.8, \"cost\": \"free\", \"description\": \"Creates AIOS runs, schedules agents, verifies artifacts, and records execution receipts.\", \"domains\": [ \"aios\", \"hivemind\", \"execution\", \"verification\", \"run\" ], \"evidence_refs\": [ \"../hivemind/README.md\", \"../docs/contracts/ASC-0001-memoryos-hivemind-loop.md\", \"../.aios/ou",
            "truncated": true
          },
          "dispatch_packets": {
            "path": ".aios/invocations/chat-170565ae3554470e/dispatch/packets.json",
            "preview": "{ \"goal_hash\": \"d24bfa47de65465f921afc60c83e1ac57d050f67c7a4ed12f9ac4534a394401a\", \"packets\": [ { \"mode\": \"local_cli\", \"role\": \"divergence\", \"target_repo\": \"GenesisOS\" }, { \"mode\": \"degraded_allowed\", \"role\": \"context\", \"target_repo\": \"memoryOS\" }, { \"mode\": \"recommendation_only\", \"role\": \"route\", \"target_repo\": \"CapabilityOS\" }, { \"mode\": \"plan_only\", \"role\": \"execution_plan\", \"target_repo\": \"hivemind\" } ], \"schema_version\": \"aios.dispatch_packets.v1\", \"status\": \"draft\" }",
            "truncated": false
          },
          "genesis": {
            "path": ".aios/invocations/chat-170565ae3554470e/genesis/branches.json",
            "preview": "{ \"authority\": \"speculative_only\", \"branches\": [ { \"branch_id\": \"inversion-goal\", \"contract_seed\": \"Explore `inversion` mutation for: 나에 대한 기억은?\", \"premise\": \"Assume the stated goal is a symptom, not the target.\", \"risk\": \"Speculative branch. Requires MyWorld contract before execution.\", \"type\": \"inversion\", \"what_it_breaks\": \"Breaks literal prompt obedience.\", \"why_it_might_matter\": \"The useful system may be the one that refuses premature completion.\" }, { \"branch_id\": \"alien_domain-goal\", \"contract_seed\": \"Explor",
            "truncated": true
          },
          "hive_execution_plan": {
            "path": ".aios/invocations/chat-170565ae3554470e/hive/execution_plan.json",
            "preview": "{ \"candidate_provider\": \"capabilityos_recommended\", \"candidate_worker\": \"hive.provider_loop\", \"contract_id\": null, \"execute_allowed\": false, \"goal_hash\": \"d24bfa47de65465f921afc60c83e1ac57d050f67c7a4ed12f9ac4534a394401a\", \"owner_repo\": \"hivemind\", \"plan_only\": true, \"schema_version\": \"aios.hive_execution_plan.v1\", \"stop_conditions\": [ \"missing_required_artifact\", \"scope_violation\", \"provider_backpressure\", \"verification_gate_failed\" ], \"user_patterns\": { \"patterns\": [ { \"confidence\": 0.78, \"evidence_refs\": [ \"docs/",
            "truncated": true
          },
          "memory_context_pack": {
            "path": ".aios/invocations/chat-170565ae3554470e/memory/context_pack.md",
            "preview": "# Context pack Task: 나에 대한 기억은? Role: hive ## Source - MemoryOS context build returned JSON. - selected_memory_ids: [\"mem_940ad99fcc2ed445\", \"mem_3af960f629693170\", \"mem_4a44670b379ca4ea\", \"mem_d0b64430dd5da2a8\", \"mem_5012d57c2c4acbf6\", \"mem_e4a9c7fe7d342598\", \"mem_001f6d5191fb8e51\", \"mem_70c8edbf4c5c9c7b\", \"mem_4f390c90de100dbf\", \"mem_61910dd09950fc81\"] - trace_id: rtrace_8703b4790bcc073e",
            "truncated": false
          },
          "memory_request": {
            "path": ".aios/invocations/chat-170565ae3554470e/memory/context_request.json",
            "preview": "{ \"auto_accept\": false, \"for_role\": \"hive\", \"goal_hash\": \"d24bfa47de65465f921afc60c83e1ac57d050f67c7a4ed12f9ac4534a394401a\", \"project\": \"AIOS\", \"requested_outputs\": [ \"context_pack.md\", \"retrieval_trace\" ], \"schema_version\": \"aios.memory_context_request.v1\", \"task\": \"나에 대한 기억은?\" }",
            "truncated": false
          }
        },
        "created_at": "2026-05-17T11:32:36+09:00",
        "degraded_receipt": {
          "missing_or_degraded_roles": [],
          "status": "not_needed",
          "stop_conditions_triggered": []
        },
        "executor_assignment": {
          "default_executor": "codex",
          "execution_owner": "hivemind",
          "mode": "bounded_worker_packet",
          "requires_dispatch_packet": true,
          "requires_verification_result": true
        },
        "goal": "나에 대한 기억은?",
        "invocation_id": "chat-170565ae3554470e",
        "next_action": "dispatch_ready",
        "overall_status": "passed",
        "role_artifacts": {
          "capability_route": ".aios/invocations/chat-170565ae3554470e/capability/route.json",
          "dispatch_packets": ".aios/invocations/chat-170565ae3554470e/dispatch/packets.json",
          "genesis": ".aios/invocations/chat-170565ae3554470e/genesis/branches.json",
          "hive_execution_plan": ".aios/invocations/chat-170565ae3554470e/hive/execution_plan.json",
          "memory_context_pack": ".aios/invocations/chat-170565ae3554470e/memory/context_pack.md",
          "memory_request": ".aios/invocations/chat-170565ae3554470e/memory/context_request.json"
        },
        "role_statuses": {
          "capability": "passed",
          "genesis": "passed",
          "hive": "passed",
          "memory": "passed"
        },
        "session_envelope": ".aios/invocations/chat-170565ae3554470e/session_envelope.json"
      },
      {
        "artifact_previews": {
          "capability_route": {
            "path": ".aios/invocations/chat-6617783a0cc46c79/capability/route.json",
            "preview": "{ \"contract\": \"capabilityos.recommendations.v1\", \"observed_capabilities\": 0, \"recommendation_only\": true, \"recommendations\": [ { \"actions\": [ \"run\", \"inspect\", \"verify\", \"demo\", \"memory-loop\" ], \"confidence\": 0.8, \"cost\": \"free\", \"description\": \"Creates AIOS runs, schedules agents, verifies artifacts, and records execution receipts.\", \"domains\": [ \"aios\", \"hivemind\", \"execution\", \"verification\", \"run\" ], \"evidence_refs\": [ \"../hivemind/README.md\", \"../docs/contracts/ASC-0001-memoryos-hivemind-loop.md\", \"../.aios/ou",
            "truncated": true
          },
          "dispatch_packets": {
            "path": ".aios/invocations/chat-6617783a0cc46c79/dispatch/packets.json",
            "preview": "{ \"goal_hash\": \"9c596cb6c4f8af13a3d48109deba0d54d60753f90f0b8e37d851161b6ca0d541\", \"packets\": [ { \"mode\": \"local_cli\", \"role\": \"divergence\", \"target_repo\": \"GenesisOS\" }, { \"mode\": \"degraded_allowed\", \"role\": \"context\", \"target_repo\": \"memoryOS\" }, { \"mode\": \"recommendation_only\", \"role\": \"route\", \"target_repo\": \"CapabilityOS\" }, { \"mode\": \"plan_only\", \"role\": \"execution_plan\", \"target_repo\": \"hivemind\" } ], \"schema_version\": \"aios.dispatch_packets.v1\", \"status\": \"draft\" }",
            "truncated": false
          },
          "genesis": {
            "path": ".aios/invocations/chat-6617783a0cc46c79/genesis/branches.json",
            "preview": "{ \"authority\": \"speculative_only\", \"branches\": [ { \"branch_id\": \"inversion-goal\", \"contract_seed\": \"Explore `inversion` mutation for: 너는 누구니?\", \"premise\": \"Assume the stated goal is a symptom, not the target.\", \"risk\": \"Speculative branch. Requires MyWorld contract before execution.\", \"type\": \"inversion\", \"what_it_breaks\": \"Breaks literal prompt obedience.\", \"why_it_might_matter\": \"The useful system may be the one that refuses premature completion.\" }, { \"branch_id\": \"alien_domain-goal\", \"contract_seed\": \"Explore `",
            "truncated": true
          },
          "hive_execution_plan": {
            "path": ".aios/invocations/chat-6617783a0cc46c79/hive/execution_plan.json",
            "preview": "{ \"candidate_provider\": \"capabilityos_recommended\", \"candidate_worker\": \"hive.provider_loop\", \"contract_id\": null, \"execute_allowed\": false, \"goal_hash\": \"9c596cb6c4f8af13a3d48109deba0d54d60753f90f0b8e37d851161b6ca0d541\", \"owner_repo\": \"hivemind\", \"plan_only\": true, \"schema_version\": \"aios.hive_execution_plan.v1\", \"stop_conditions\": [ \"missing_required_artifact\", \"scope_violation\", \"provider_backpressure\", \"verification_gate_failed\" ], \"user_patterns\": { \"patterns\": [ { \"confidence\": 0.78, \"evidence_refs\": [ \"docs/",
            "truncated": true
          },
          "memory_context_pack": {
            "path": ".aios/invocations/chat-6617783a0cc46c79/memory/context_pack.md",
            "preview": "# Context pack Task: 너는 누구니? Role: hive ## Source - MemoryOS context build returned JSON. - selected_memory_ids: [\"mem_940ad99fcc2ed445\", \"mem_3af960f629693170\", \"mem_4a44670b379ca4ea\", \"mem_d0b64430dd5da2a8\", \"mem_5012d57c2c4acbf6\", \"mem_e4a9c7fe7d342598\", \"mem_001f6d5191fb8e51\", \"mem_70c8edbf4c5c9c7b\", \"mem_4f390c90de100dbf\", \"mem_61910dd09950fc81\"] - trace_id: rtrace_6a2becba2693950c",
            "truncated": false
          },
          "memory_request": {
            "path": ".aios/invocations/chat-6617783a0cc46c79/memory/context_request.json",
            "preview": "{ \"auto_accept\": false, \"for_role\": \"hive\", \"goal_hash\": \"9c596cb6c4f8af13a3d48109deba0d54d60753f90f0b8e37d851161b6ca0d541\", \"project\": \"AIOS\", \"requested_outputs\": [ \"context_pack.md\", \"retrieval_trace\" ], \"schema_version\": \"aios.memory_context_request.v1\", \"task\": \"너는 누구니?\" }",
            "truncated": false
          }
        },
        "created_at": "2026-05-17T11:32:17+09:00",
        "degraded_receipt": {
          "missing_or_degraded_roles": [],
          "status": "not_needed",
          "stop_conditions_triggered": []
        },
        "executor_assignment": {
          "default_executor": "codex",
          "execution_owner": "hivemind",
          "mode": "bounded_worker_packet",
          "requires_dispatch_packet": true,
          "requires_verification_result": true
        },
        "goal": "너는 누구니?",
        "invocation_id": "chat-6617783a0cc46c79",
        "next_action": "dispatch_ready",
        "overall_status": "passed",
        "role_artifacts": {
          "capability_route": ".aios/invocations/chat-6617783a0cc46c79/capability/route.json",
          "dispatch_packets": ".aios/invocations/chat-6617783a0cc46c79/dispatch/packets.json",
          "genesis": ".aios/invocations/chat-6617783a0cc46c79/genesis/branches.json",
          "hive_execution_plan": ".aios/invocations/chat-6617783a0cc46c79/hive/execution_plan.json",
          "memory_context_pack": ".aios/invocations/chat-6617783a0cc46c79/memory/context_pack.md",
          "memory_request": ".aios/invocations/chat-6617783a0cc46c79/memory/context_request.json"
        },
        "role_statuses": {
          "capability": "passed",
          "genesis": "passed",
          "hive": "passed",
          "memory": "passed"
        },
        "session_envelope": ".aios/invocations/chat-6617783a0cc46c79/session_envelope.json"
      },
      {
        "artifact_previews": {
          "capability_route": {
            "path": ".aios/invocations/chat-978e0c2be8a6c366/capability/route.json",
            "preview": "{ \"contract\": \"capabilityos.recommendations.v1\", \"observed_capabilities\": 0, \"recommendation_only\": true, \"recommendations\": [ { \"actions\": [ \"recommend\", \"schema-check\", \"freshness-check\", \"cite\", \"fallback\" ], \"confidence\": 0.6, \"cost\": \"free\", \"description\": \"Maps API capability contracts, freshness requirements, and privacy limits for later executor review.\", \"domains\": [ \"aios\", \"api\", \"contract\", \"schema\", \"freshness\", \"provider\" ], \"evidence_refs\": [ \"../CapabilityOS/README.md\", \"../docs/AIOS_BUILD_METHOD.md",
            "truncated": true
          },
          "dispatch_packets": {
            "path": ".aios/invocations/chat-978e0c2be8a6c366/dispatch/packets.json",
            "preview": "{ \"goal_hash\": \"d64125621308b950207faf196775db430b400b5c0b56c8f9a92730414407f800\", \"packets\": [ { \"mode\": \"local_cli\", \"role\": \"divergence\", \"target_repo\": \"GenesisOS\" }, { \"mode\": \"degraded_allowed\", \"role\": \"context\", \"target_repo\": \"memoryOS\" }, { \"mode\": \"recommendation_only\", \"role\": \"route\", \"target_repo\": \"CapabilityOS\" }, { \"mode\": \"plan_only\", \"role\": \"execution_plan\", \"target_repo\": \"hivemind\" } ], \"schema_version\": \"aios.dispatch_packets.v1\", \"status\": \"draft\" }",
            "truncated": false
          },
          "genesis": {
            "path": ".aios/invocations/chat-978e0c2be8a6c366/genesis/branches.json",
            "preview": "{ \"authority\": \"speculative_only\", \"branches\": [ { \"branch_id\": \"inversion-provider\", \"contract_seed\": \"Explore `inversion` mutation for: provider 실패 기억은?\", \"premise\": \"Assume the stated goal is a symptom, not the target.\", \"risk\": \"Speculative branch. Requires MyWorld contract before execution.\", \"type\": \"inversion\", \"what_it_breaks\": \"Breaks literal prompt obedience.\", \"why_it_might_matter\": \"The useful system may be the one that refuses premature completion.\" }, { \"branch_id\": \"alien_domain-provider\", \"contract_",
            "truncated": true
          },
          "hive_execution_plan": {
            "path": ".aios/invocations/chat-978e0c2be8a6c366/hive/execution_plan.json",
            "preview": "{ \"candidate_provider\": \"capabilityos_recommended\", \"candidate_worker\": \"hive.provider_loop\", \"contract_id\": null, \"execute_allowed\": false, \"goal_hash\": \"d64125621308b950207faf196775db430b400b5c0b56c8f9a92730414407f800\", \"owner_repo\": \"hivemind\", \"plan_only\": true, \"schema_version\": \"aios.hive_execution_plan.v1\", \"stop_conditions\": [ \"missing_required_artifact\", \"scope_violation\", \"provider_backpressure\", \"verification_gate_failed\" ], \"user_patterns\": { \"patterns\": [ { \"confidence\": 0.78, \"evidence_refs\": [ \"docs/",
            "truncated": true
          },
          "memory_context_pack": {
            "path": ".aios/invocations/chat-978e0c2be8a6c366/memory/context_pack.md",
            "preview": "# Context pack Task: provider 실패 기억은? Role: hive ## Source - MemoryOS context build returned JSON. - selected_memory_ids: [\"mem_940ad99fcc2ed445\", \"mem_4a44670b379ca4ea\", \"mem_d0b64430dd5da2a8\", \"mem_5012d57c2c4acbf6\", \"mem_1f18cea463eed9fd\"] - trace_id: rtrace_1ae216a69d2eb2c0",
            "truncated": false
          },
          "memory_request": {
            "path": ".aios/invocations/chat-978e0c2be8a6c366/memory/context_request.json",
            "preview": "{ \"auto_accept\": false, \"for_role\": \"hive\", \"goal_hash\": \"d64125621308b950207faf196775db430b400b5c0b56c8f9a92730414407f800\", \"project\": \"AIOS\", \"requested_outputs\": [ \"context_pack.md\", \"retrieval_trace\" ], \"schema_version\": \"aios.memory_context_request.v1\", \"task\": \"provider 실패 기억은?\" }",
            "truncated": false
          }
        },
        "created_at": "2026-05-17T11:32:16+09:00",
        "degraded_receipt": {
          "missing_or_degraded_roles": [],
          "status": "not_needed",
          "stop_conditions_triggered": []
        },
        "executor_assignment": {
          "default_executor": "codex",
          "execution_owner": "hivemind",
          "mode": "bounded_worker_packet",
          "requires_dispatch_packet": true,
          "requires_verification_result": true
        },
        "goal": "provider 실패 기억은?",
        "invocation_id": "chat-978e0c2be8a6c366",
        "next_action": "dispatch_ready",
        "overall_status": "passed",
        "role_artifacts": {
          "capability_route": ".aios/invocations/chat-978e0c2be8a6c366/capability/route.json",
          "dispatch_packets": ".aios/invocations/chat-978e0c2be8a6c366/dispatch/packets.json",
          "genesis": ".aios/invocations/chat-978e0c2be8a6c366/genesis/branches.json",
          "hive_execution_plan": ".aios/invocations/chat-978e0c2be8a6c366/hive/execution_plan.json",
          "memory_context_pack": ".aios/invocations/chat-978e0c2be8a6c366/memory/context_pack.md",
          "memory_request": ".aios/invocations/chat-978e0c2be8a6c366/memory/context_request.json"
        },
        "role_statuses": {
          "capability": "passed",
          "genesis": "passed",
          "hive": "passed",
          "memory": "passed"
        },
        "session_envelope": ".aios/invocations/chat-978e0c2be8a6c366/session_envelope.json"
      }
    ]
  },
  "memory_draft_queue": {
    "counts": {
      "chat_turn_summary": 128,
      "genesis_friction_signal": 67
    },
    "items": [
      {
        "confidence": 0.72,
        "content_preview": "User asked: provider 실패 기억은? AIOS replied: ## Provider 실패 기억 요약 MemoryOS accepted memory에 명시적 \"provider failure\" 레코드는 없었지만, AIOS receipt fallback에서 negative evidence 5건이 추출됨 (trace: `rtrace_65a6bab990cbc585`). ### Negative Evidence (receipt-derived) | ID | 실패 ",
        "conversation_id": "gate-chair-eval-177e8627e75a4e6e-current-4",
        "created_at": "2026-05-17T11:34:29+09:00",
        "draft_id": "gate-chair-eval-177e8627e75a4e6e-current-4:0",
        "genesis_ref": "",
        "origin": "aios_chat",
        "raw_refs": [
          "messages.jsonl",
          "cost.json"
        ],
        "review_request_id": "",
        "review_result": "",
        "review_result_ref": "",
        "review_state": "operator_review_required",
        "reviewed_at": "",
        "source_artifact": ".aios/chat/gate-chair-eval-177e8627e75a4e6e-current-4/memory_drafts.json",
        "status": "draft",
        "truncated": true,
        "type": "chat_turn_summary"
      },
      {
        "confidence": 0.67,
        "content_preview": "GenesisOS projected discomfort/need signal: - inversion-provider: Breaks literal prompt obedience -> The useful system may be the one that refuses premature completion - alien_domain-provider: Breaks repo-shaped thinking -> Infrastructure, rituals, and zoning ",
        "conversation_id": "gate-chair-eval-177e8627e75a4e6e-current-4",
        "created_at": "2026-05-17T11:34:29+09:00",
        "draft_id": "gate-chair-eval-177e8627e75a4e6e-current-4:1",
        "genesis_ref": ".aios/invocations/chat-ae0b74ec9f46bf2c/genesis/branches.json",
        "origin": "aios_chat_genesis",
        "raw_refs": [
          "messages.jsonl",
          "gate_decisions",
          ".aios/invocations/chat-ae0b74ec9f46bf2c/genesis/branches.json"
        ],
        "review_request_id": "",
        "review_result": "",
        "review_result_ref": "",
        "review_state": "operator_review_required",
        "reviewed_at": "",
        "source_artifact": ".aios/chat/gate-chair-eval-177e8627e75a4e6e-current-4/memory_drafts.json",
        "status": "draft",
        "truncated": true,
        "type": "genesis_friction_signal"
      },
      {
        "confidence": 0.72,
        "content_preview": "User asked: AIOS에는 gate 역할의 Agent가 있나? 아니면 시스템 답변밖에 못하나? AIOS replied: 가능해. provided chatbot, Codex CLI, Claude CLI, local LLM은 AIOS에 붙는 provider substrate로 흡수할 수 있어. 다만 필요한 것은 단순 Agent 하나가 아니라 Gate/Chair Agent 계층이야. 이 Gate가 네가 지금 Codex에게 맡기는 판단처럼 MemoryOS con",
        "conversation_id": "gate-chair-eval-177e8627e75a4e6e-current-3",
        "created_at": "2026-05-17T11:34:07+09:00",
        "draft_id": "gate-chair-eval-177e8627e75a4e6e-current-3:0",
        "genesis_ref": "",
        "origin": "aios_chat",
        "raw_refs": [
          "messages.jsonl",
          "cost.json"
        ],
        "review_request_id": "",
        "review_result": "",
        "review_result_ref": "",
        "review_state": "operator_review_required",
        "reviewed_at": "",
        "source_artifact": ".aios/chat/gate-chair-eval-177e8627e75a4e6e-current-3/memory_drafts.json",
        "status": "draft",
        "truncated": true,
        "type": "chat_turn_summary"
      },
      {
        "confidence": 0.67,
        "content_preview": "GenesisOS projected discomfort/need signal: - inversion-aios-gate-agent: Breaks literal prompt obedience -> The useful system may be the one that refuses premature completion - alien_domain-aios-gate-agent: Breaks repo-shaped thinking -> Infrastructure, ritual",
        "conversation_id": "gate-chair-eval-177e8627e75a4e6e-current-3",
        "created_at": "2026-05-17T11:34:07+09:00",
        "draft_id": "gate-chair-eval-177e8627e75a4e6e-current-3:1",
        "genesis_ref": ".aios/invocations/chat-df86e60a788ee549/genesis/branches.json",
        "origin": "aios_chat_genesis",
        "raw_refs": [
          "messages.jsonl",
          "gate_decisions",
          ".aios/invocations/chat-df86e60a788ee549/genesis/branches.json"
        ],
        "review_request_id": "",
        "review_result": "",
        "review_result_ref": "",
        "review_state": "operator_review_required",
        "reviewed_at": "",
        "source_artifact": ".aios/chat/gate-chair-eval-177e8627e75a4e6e-current-3/memory_drafts.json",
        "status": "draft",
        "truncated": true,
        "type": "genesis_friction_signal"
      },
      {
        "confidence": 0.72,
        "content_preview": "User asked: 나에 대한 기억은? AIOS replied: MemoryOS가 너와 AIOS 작업 방식에 관련된 기억 10개를 찾았어 (rtrace_230849e7c29ba1af). 핵심은 이거야. - Claude의 CLI 기능들을 탑재할거야. 세션 로그나 대화 내용들을 토대로 역설계해서 시스템을 구축하는건 어때? codex와 local LLM도 사용할 수 있게 [docs/contracts/ASC-0050-aios-primitive-surface.md:9]",
        "conversation_id": "gate-chair-eval-177e8627e75a4e6e-current-2",
        "created_at": "2026-05-17T11:33:22+09:00",
        "draft_id": "gate-chair-eval-177e8627e75a4e6e-current-2:0",
        "genesis_ref": "",
        "origin": "aios_chat",
        "raw_refs": [
          "messages.jsonl",
          "cost.json"
        ],
        "review_request_id": "",
        "review_result": "",
        "review_result_ref": "",
        "review_state": "operator_review_required",
        "reviewed_at": "",
        "source_artifact": ".aios/chat/gate-chair-eval-177e8627e75a4e6e-current-2/memory_drafts.json",
        "status": "draft",
        "truncated": true,
        "type": "chat_turn_summary"
      },
      {
        "confidence": 0.67,
        "content_preview": "GenesisOS projected discomfort/need signal: - inversion-goal: Breaks literal prompt obedience -> The useful system may be the one that refuses premature completion - alien_domain-goal: Breaks repo-shaped thinking -> Infrastructure, rituals, and zoning may matt",
        "conversation_id": "gate-chair-eval-177e8627e75a4e6e-current-2",
        "created_at": "2026-05-17T11:33:22+09:00",
        "draft_id": "gate-chair-eval-177e8627e75a4e6e-current-2:1",
        "genesis_ref": ".aios/invocations/chat-170565ae3554470e/genesis/branches.json",
        "origin": "aios_chat_genesis",
        "raw_refs": [
          "messages.jsonl",
          "gate_decisions",
          ".aios/invocations/chat-170565ae3554470e/genesis/branches.json"
        ],
        "review_request_id": "",
        "review_result": "",
        "review_result_ref": "",
        "review_state": "operator_review_required",
        "reviewed_at": "",
        "source_artifact": ".aios/chat/gate-chair-eval-177e8627e75a4e6e-current-2/memory_drafts.json",
        "status": "draft",
        "truncated": true,
        "type": "genesis_friction_signal"
      },
      {
        "confidence": 0.72,
        "content_preview": "User asked: 너는 누구니? AIOS replied: 나는 AIOS — 재원의 로컬 AI Operating System 대화 표면이야. **구조적으로**: myworld control plane 위에서 5개 인격(Hive Mind, MemoryOS, CapabilityOS, GenesisOS, Sovereign Self)을 묶어 돌리는 운영 인터페이스. 특정 provider(Claude, Codex, Ollama) 하나가 아니라, 필요에 따라 provid",
        "conversation_id": "gate-chair-eval-177e8627e75a4e6e-current-1",
        "created_at": "2026-05-17T11:32:36+09:00",
        "draft_id": "gate-chair-eval-177e8627e75a4e6e-current-1:0",
        "genesis_ref": "",
        "origin": "aios_chat",
        "raw_refs": [
          "messages.jsonl",
          "cost.json"
        ],
        "review_request_id": "",
        "review_result": "",
        "review_result_ref": "",
        "review_state": "operator_review_required",
        "reviewed_at": "",
        "source_artifact": ".aios/chat/gate-chair-eval-177e8627e75a4e6e-current-1/memory_drafts.json",
        "status": "draft",
        "truncated": true,
        "type": "chat_turn_summary"
      },
      {
        "confidence": 0.67,
        "content_preview": "GenesisOS projected discomfort/need signal: - inversion-goal: Breaks literal prompt obedience -> The useful system may be the one that refuses premature completion - alien_domain-goal: Breaks repo-shaped thinking -> Infrastructure, rituals, and zoning may matt",
        "conversation_id": "gate-chair-eval-177e8627e75a4e6e-current-1",
        "created_at": "2026-05-17T11:32:36+09:00",
        "draft_id": "gate-chair-eval-177e8627e75a4e6e-current-1:1",
        "genesis_ref": ".aios/invocations/chat-6617783a0cc46c79/genesis/branches.json",
        "origin": "aios_chat_genesis",
        "raw_refs": [
          "messages.jsonl",
          "gate_decisions",
          ".aios/invocations/chat-6617783a0cc46c79/genesis/branches.json"
        ],
        "review_request_id": "",
        "review_result": "",
        "review_result_ref": "",
        "review_state": "operator_review_required",
        "reviewed_at": "",
        "source_artifact": ".aios/chat/gate-chair-eval-177e8627e75a4e6e-current-1/memory_drafts.json",
        "status": "draft",
        "truncated": true,
        "type": "genesis_friction_signal"
      },
      {
        "confidence": 0.72,
        "content_preview": "User asked: provider 실패 기억은? AIOS replied: MemoryOS가 선택한 accepted failure memory는 없었지만, AIOS가 local receipts에서 negative evidence 5개를 찾았어 (rtrace_1ae216a69d2eb2c0). 이건 아직 MemoryOS accepted memory가 아니라 Gate가 다음 route를 망치지 않기 위한 보조 증거야. - neg_173396d7a243ece5: hi",
        "conversation_id": "gate-chair-eval-177e8627e75a4e6e-internal-4",
        "created_at": "2026-05-17T11:32:17+09:00",
        "draft_id": "gate-chair-eval-177e8627e75a4e6e-internal-4:0",
        "genesis_ref": "",
        "origin": "aios_chat",
        "raw_refs": [
          "messages.jsonl",
          "cost.json"
        ],
        "review_request_id": "",
        "review_result": "",
        "review_result_ref": "",
        "review_state": "operator_review_required",
        "reviewed_at": "",
        "source_artifact": ".aios/chat/gate-chair-eval-177e8627e75a4e6e-internal-4/memory_drafts.json",
        "status": "draft",
        "truncated": true,
        "type": "chat_turn_summary"
      },
      {
        "confidence": 0.67,
        "content_preview": "GenesisOS projected discomfort/need signal: - inversion-provider: Breaks literal prompt obedience -> The useful system may be the one that refuses premature completion - alien_domain-provider: Breaks repo-shaped thinking -> Infrastructure, rituals, and zoning ",
        "conversation_id": "gate-chair-eval-177e8627e75a4e6e-internal-4",
        "created_at": "2026-05-17T11:32:17+09:00",
        "draft_id": "gate-chair-eval-177e8627e75a4e6e-internal-4:1",
        "genesis_ref": ".aios/invocations/chat-978e0c2be8a6c366/genesis/branches.json",
        "origin": "aios_chat_genesis",
        "raw_refs": [
          "messages.jsonl",
          "gate_decisions",
          ".aios/invocations/chat-978e0c2be8a6c366/genesis/branches.json"
        ],
        "review_request_id": "",
        "review_result": "",
        "review_result_ref": "",
        "review_state": "operator_review_required",
        "reviewed_at": "",
        "source_artifact": ".aios/chat/gate-chair-eval-177e8627e75a4e6e-internal-4/memory_drafts.json",
        "status": "draft",
        "truncated": true,
        "type": "genesis_friction_signal"
      },
      {
        "confidence": 0.72,
        "content_preview": "User asked: AIOS에는 gate 역할의 Agent가 있나? 아니면 시스템 답변밖에 못하나? AIOS replied: 가능해. provided chatbot, Codex CLI, Claude CLI, local LLM은 AIOS에 붙는 provider substrate로 흡수할 수 있어. 다만 필요한 것은 단순 Agent 하나가 아니라 Gate/Chair Agent 계층이야. 이 Gate가 네가 지금 Codex에게 맡기는 판단처럼 MemoryOS con",
        "conversation_id": "gate-chair-eval-177e8627e75a4e6e-internal-3",
        "created_at": "2026-05-17T11:32:16+09:00",
        "draft_id": "gate-chair-eval-177e8627e75a4e6e-internal-3:0",
        "genesis_ref": "",
        "origin": "aios_chat",
        "raw_refs": [
          "messages.jsonl",
          "cost.json"
        ],
        "review_request_id": "",
        "review_result": "",
        "review_result_ref": "",
        "review_state": "operator_review_required",
        "reviewed_at": "",
        "source_artifact": ".aios/chat/gate-chair-eval-177e8627e75a4e6e-internal-3/memory_drafts.json",
        "status": "draft",
        "truncated": true,
        "type": "chat_turn_summary"
      },
      {
        "confidence": 0.67,
        "content_preview": "GenesisOS projected discomfort/need signal: - inversion-aios-gate-agent: Breaks literal prompt obedience -> The useful system may be the one that refuses premature completion - alien_domain-aios-gate-agent: Breaks repo-shaped thinking -> Infrastructure, ritual",
        "conversation_id": "gate-chair-eval-177e8627e75a4e6e-internal-3",
        "created_at": "2026-05-17T11:32:16+09:00",
        "draft_id": "gate-chair-eval-177e8627e75a4e6e-internal-3:1",
        "genesis_ref": ".aios/invocations/chat-62fd5775b8fb5ce2/genesis/branches.json",
        "origin": "aios_chat_genesis",
        "raw_refs": [
          "messages.jsonl",
          "gate_decisions",
          ".aios/invocations/chat-62fd5775b8fb5ce2/genesis/branches.json"
        ],
        "review_request_id": "",
        "review_result": "",
        "review_result_ref": "",
        "review_state": "operator_review_required",
        "reviewed_at": "",
        "source_artifact": ".aios/chat/gate-chair-eval-177e8627e75a4e6e-internal-3/memory_drafts.json",
        "status": "draft",
        "truncated": true,
        "type": "genesis_friction_signal"
      }
    ],
    "latest_created_at": "2026-05-17T11:34:29+09:00",
    "total": 195
  },
  "monitor": {
    "findings": [
      {
        "action": "collect_result_or_run_watcher",
        "alert": {
          "code": "dispatch_results_pending",
          "dispatch_id": "asc-0182",
          "repos": [
            "myworld"
          ]
        },
        "code": "dispatch_results_pending",
        "owner": "myworld",
        "reason": "A sent dispatch has no collected result packet for at least one target repo.",
        "severity": "high"
      },
      {
        "action": "hold_for_repo_owner_triage",
        "alert": {
          "code": "repo_dirty",
          "entries": [
            "?? docs/AIOS_AGENT_LEDGER.md"
          ],
          "repo": "CapabilityOS"
        },
        "code": "repo_dirty",
        "owner": "CapabilityOS",
        "reason": "A child repo has uncommitted changes that need owner review before new work is stacked on it.",
        "severity": "medium"
      },
      {
        "action": "hold_for_repo_owner_triage",
        "alert": {
          "code": "repo_dirty",
          "entries": [
            " M genesisos/cli.py",
            " M genesisos/critic.py"
          ],
          "repo": "GenesisOS"
        },
        "code": "repo_dirty",
        "owner": "GenesisOS",
        "reason": "A child repo has uncommitted changes that need owner review before new work is stacked on it.",
        "severity": "medium"
      },
      {
        "action": "review_prompt_prison_escape_vectors",
        "alert": {
          "code": "genesis_prompt_prison_advisory",
          "flagged_count": 3,
          "report_schema_version": "aios.genesis_critic_dispatch.v1",
          "sample": [
            {
              "confidence": 0.5,
              "contract_id": "ASC-0183",
              "escape_vectors": [
                "force one analogy from a distant domain before deciding",
                "enumerate assumptions, then negate the top three",
                "rewrite in plain language before using the jargon again"
              ],
              "path": "docs/contracts/ASC-0183-dream-parametric-per-repo-adapters.md",
              "signature_count": 3,
              "signatures": [
                {
                  "escape_vector": "force one analogy from a distant domain before deciding",
                  "evidence": "no cross-domain frame markers found",
                  "signature": "single-frame"
                },
                {
                  "escape_vector": "enumerate assumptions, then negate the top three",
                  "evidence": "no explicit assumptions named",
                  "signature": "assumption-silent"
                },
                {
                  "escape_vector": "rewrite in plain language before using the jargon again",
                  "evidence": "jargon terms without unfolding: aios, capabilityos, contract, genesisos, hivemind, memoryos",
                  "signature": "terminology-trapped"
                }
              ],
              "status": "proposed"
            },
            {
              "confidence": 0.5,
              "contract_id": "ASC-0184",
              "escape_vectors": [
                "force one analogy from a distant domain before deciding",
                "enumerate assumptions, then negate the top three",
                "rewrite in plain language before using the jargon again"
              ],
              "path": "docs/contracts/ASC-0184-hooks-deterministic-enforcement.md",
              "signature_count": 3,
              "signatures": [
                {
                  "escape_vector": "force one analogy from a distant domain before deciding",
                  "evidence": "no cross-domain frame markers found",
                  "signature": "single-frame"
                },
                {
                  "escape_vector": "enumerate assumptions, then negate the top three",
                  "evidence": "no explicit assumptions named",
                  "signature": "assumption-silent"
                },
                {
                  "escape_vector": "rewrite in plain language before using the jargon again",
                  "evidence": "jargon terms without unfolding: agent, aios, contract, ledger",
                  "signature": "terminology-trapped"
                }
              ],
              "status": "accepted"
            },
            {
              "confidence": 0.667,
              "contract_id": "ASC-0185",
              "escape_vectors": [
                "force one analogy from a distant domain before deciding",
                "enumerate assumptions, then negate the top three",
                "rewrite in plain language before using the jargon again",
                "compare the answer in 1h, 1w, and 1y time horizons"
              ],
              "path": "docs/contracts/ASC-0185-leased-jobs-queue.md",
              "signature_count": 4,
              "signatures": [
                {
                  "escape_vector": "force one analogy from a distant domain before deciding",
                  "evidence": "no cross-domain frame markers found",
                  "signature": "single-frame"
                },
                {
                  "escape_vector": "enumerate assumptions, then negate the top three",
                  "evidence": "no explicit assumptions named",
                  "signature": "assumption-silent"
                },
                {
                  "escape_vector": "rewrite in plain language before using the jargon again",
                  "evidence": "jargon terms without unfolding: aios, dispatch, provenance",
                  "signature": "terminology-trapped"
                },
                {
                  "escape_vector": "compare the answer in 1h, 1w, and 1y time horizons",
                  "evidence": "no short-term versus long-term alternative found",
                  "signature": "time-frozen"
                }
              ],
              "status": "accepted"
            }
          ],
          "scanned_count": 4
        },
        "code": "genesis_prompt_prison_advisory",
        "owner": "GenesisOS",
        "reason": "GenesisOS critic found advisory prompt-prison signatures in open contracts.",
        "severity": "info"
      },
      {
        "action": "review_5_persona_axis",
        "alert": {
          "code": "persona_axis_advisory",
          "contracts_scored": 20,
          "persona_composite": 0.44,
          "report_schema_version": "aios.persona_audit.v1"
        },
        "code": "persona_axis_advisory",
        "owner": "myworld",
        "reason": "AIOS 5-persona cognitive architecture score is advisory and orthogonal to governance.",
        "severity": "info"
      }
    ],
    "generated_at": "2026-05-17T11:36:03+09:00",
    "health": "blocked",
    "next_actions": [
      {
        "action": "collect_result_or_run_watcher",
        "owner": "myworld",
        "reason": "A sent dispatch has no collected result packet for at least one target repo.",
        "severity": "high"
      },
      {
        "action": "hold_for_repo_owner_triage",
        "owner": "CapabilityOS",
        "reason": "A child repo has uncommitted changes that need owner review before new work is stacked on it.",
        "severity": "medium"
      },
      {
        "action": "hold_for_repo_owner_triage",
        "owner": "GenesisOS",
        "reason": "A child repo has uncommitted changes that need owner review before new work is stacked on it.",
        "severity": "medium"
      },
      {
        "action": "review_prompt_prison_escape_vectors",
        "owner": "GenesisOS",
        "reason": "GenesisOS critic found advisory prompt-prison signatures in open contracts.",
        "severity": "info"
      },
      {
        "action": "review_5_persona_axis",
        "owner": "myworld",
        "reason": "AIOS 5-persona cognitive architecture score is advisory and orthogonal to governance.",
        "severity": "info"
      }
    ],
    "persona_axis": {
      "authority": "advisory_only",
      "contracts_scored": 20,
      "generated_at": "2026-05-17T11:36:03+09:00",
      "per_contract": [
        {
          "contract_id": "ASC-0159",
          "path": "docs/contracts/ASC-0159-aios-operating-layer-paper-draft.md",
          "scores": {
            "philosophy_score": 0.0,
            "retriever_score": 0.0,
            "router_score": 1.0,
            "sovereign_score": 1.0,
            "wrapper_score": 0.0
          },
          "signals": {
            "capability_route": true,
            "founder_gate": true,
            "genesis_philosophy": false,
            "operator_pair": true,
            "providers": [
              "codex"
            ],
            "rtrace": false,
            "vision_keywords": true
          }
        },
        {
          "contract_id": "ASC-0160",
          "path": "docs/contracts/ASC-0160-paper-refinement-loop.md",
          "scores": {
            "philosophy_score": 1.0,
            "retriever_score": 0.0,
            "router_score": 1.0,
            "sovereign_score": 1.0,
            "wrapper_score": 0.0
          },
          "signals": {
            "capability_route": true,
            "founder_gate": true,
            "genesis_philosophy": true,
            "operator_pair": true,
            "providers": [
              "codex"
            ],
            "rtrace": false,
            "vision_keywords": true
          }
        },
        {
          "contract_id": "ASC-0161",
          "path": "docs/contracts/ASC-0161-paper-related-work-source-evidence.md",
          "scores": {
            "philosophy_score": 0.0,
            "retriever_score": 0.0,
            "router_score": 1.0,
            "sovereign_score": 1.0,
            "wrapper_score": 0.0
          },
          "signals": {
            "capability_route": true,
            "founder_gate": true,
            "genesis_philosophy": false,
            "operator_pair": true,
            "providers": [
              "codex"
            ],
            "rtrace": true,
            "vision_keywords": true
          }
        },
        {
          "contract_id": "ASC-0162",
          "path": "docs/contracts/ASC-0162-direct-cli-vs-aios-benchmark-protocol.md",
          "scores": {
            "philosophy_score": 0.0,
            "retriever_score": 0.0,
            "router_score": 1.0,
            "sovereign_score": 1.0,
            "wrapper_score": 0.0
          },
          "signals": {
            "capability_route": true,
            "founder_gate": true,
            "genesis_philosophy": false,
            "operator_pair": true,
            "providers": [
              "codex"
            ],
            "rtrace": false,
            "vision_keywords": true
          }
        },
        {
          "contract_id": "ASC-0163",
          "path": "docs/contracts/ASC-0163-negative-evidence-combinatorial-creativity.md",
          "scores": {
            "philosophy_score": 1.0,
            "retriever_score": 0.0,
            "router_score": 1.0,
            "sovereign_score": 1.0,
            "wrapper_score": 1.0
          },
          "signals": {
            "capability_route": true,
            "founder_gate": true,
            "genesis_philosophy": true,
            "operator_pair": true,
            "providers": [
              "claude",
              "codex",
              "local",
              "ollama"
            ],
            "rtrace": true,
            "vision_keywords": true
          }
        },
        {
          "contract_id": "ASC-0164",
          "path": "docs/contracts/ASC-0164-genesisos-child-watcher-surface.md",
          "scores": {
            "philosophy_score": 0.0,
            "retriever_score": 0.0,
            "router_score": 1.0,
            "sovereign_score": 1.0,
            "wrapper_score": 0.0
          },
          "signals": {
            "capability_route": true,
            "founder_gate": true,
            "genesis_philosophy": false,
            "operator_pair": true,
            "providers": [
              "codex"
            ],
            "rtrace": false,
            "vision_keywords": true
          }
        },
        {
          "contract_id": "ASC-0165",
          "path": "docs/contracts/ASC-0165-memory-genesis-provider-blindspot-reinforcement.md",
          "scores": {
            "philosophy_score": 1.0,
            "retriever_score": 0.0,
            "router_score": 1.0,
            "sovereign_score": 1.0,
            "wrapper_score": 1.0
          },
          "signals": {
            "capability_route": true,
            "founder_gate": true,
            "genesis_philosophy": true,
            "operator_pair": true,
            "providers": [
              "claude",
              "codex",
              "local"
            ],
            "rtrace": false,
            "vision_keywords": true
          }
        },
        {
          "contract_id": "ASC-0166",
          "path": "docs/contracts/ASC-0166-provider-pin-required-classification.md",
          "scores": {
            "philosophy_score": 0.0,
            "retriever_score": 0.0,
            "router_score": 0.0,
            "sovereign_score": 1.0,
            "wrapper_score": 1.0
          },
          "signals": {
            "capability_route": false,
            "founder_gate": true,
            "genesis_philosophy": false,
            "operator_pair": true,
            "providers": [
              "claude",
              "codex",
              "local"
            ],
            "rtrace": false,
            "vision_keywords": true
          }
        },
        {
          "contract_id": "ASC-0167",
          "path": "docs/contracts/ASC-0167-capabilityos-permissioned-constraint-break-route.md",
          "scores": {
            "philosophy_score": 0.0,
            "retriever_score": 0.0,
            "router_score": 0.0,
            "sovereign_score": 1.0,
            "wrapper_score": 0.0
          },
          "signals": {
            "capability_route": false,
            "founder_gate": true,
            "genesis_philosophy": false,
            "operator_pair": true,
            "providers": [
              "codex"
            ],
            "rtrace": false,
            "vision_keywords": true
          }
        },
        {
          "contract_id": "ASC-0168",
          "path": "docs/contracts/ASC-0168-hivemind-permission-preflight.md",
          "scores": {
            "philosophy_score": 0.0,
            "retriever_score": 0.0,
            "router_score": 0.0,
            "sovereign_score": 1.0,
            "wrapper_score": 0.0
          },
          "signals": {
            "capability_route": false,
            "founder_gate": true,
            "genesis_philosophy": false,
            "operator_pair": true,
            "providers": [
              "codex"
            ],
            "rtrace": false,
            "vision_keywords": true
          }
        },
        {
          "contract_id": "ASC-0169",
          "path": "docs/contracts/ASC-0169-hivemind-aios-packet-runner.md",
          "scores": {
            "philosophy_score": 0.0,
            "retriever_score": 0.0,
            "router_score": 1.0,
            "sovereign_score": 1.0,
            "wrapper_score": 0.0
          },
          "signals": {
            "capability_route": true,
            "founder_gate": true,
            "genesis_philosophy": false,
            "operator_pair": true,
            "providers": [
              "local"
            ],
            "rtrace": false,
            "vision_keywords": true
          }
        },
        {
          "contract_id": "ASC-0170",
          "path": "docs/contracts/ASC-0170-hivemind-scoped-writable-provider-execution.md",
          "scores": {
            "philosophy_score": 0.0,
            "retriever_score": 0.0,
            "router_score": 1.0,
            "sovereign_score": 1.0,
            "wrapper_score": 0.0
          },
          "signals": {
            "capability_route": true,
            "founder_gate": true,
            "genesis_philosophy": false,
            "operator_pair": true,
            "providers": [
              "codex"
            ],
            "rtrace": false,
            "vision_keywords": true
          }
        },
        {
          "contract_id": "ASC-0171",
          "path": "docs/contracts/ASC-0171-hivemind-permissioned-dangerous-provider-execution.md",
          "scores": {
            "philosophy_score": 0.0,
            "retriever_score": 0.0,
            "router_score": 0.0,
            "sovereign_score": 1.0,
            "wrapper_score": 0.0
          },
          "signals": {
            "capability_route": false,
            "founder_gate": true,
            "genesis_philosophy": false,
            "operator_pair": true,
            "providers": [
              "codex"
            ],
            "rtrace": false,
            "vision_keywords": true
          }
        },
        {
          "contract_id": "ASC-0173",
          "path": "docs/contracts/ASC-0173-product-repo-consent-emitted-evidence-ingest.md",
          "scores": {
            "philosophy_score": 0.0,
            "retriever_score": 0.0,
            "router_score": 0.0,
            "sovereign_score": 1.0,
            "wrapper_score": 0.0
          },
          "signals": {
            "capability_route": false,
            "founder_gate": true,
            "genesis_philosophy": false,
            "operator_pair": true,
            "providers": [
              "claude"
            ],
            "rtrace": false,
            "vision_keywords": true
          }
        },
        {
          "contract_id": "ASC-0174",
          "path": "docs/contracts/ASC-0174-hive-debate-observer-vs-executor-reframe.md",
          "scores": {
            "philosophy_score": 1.0,
            "retriever_score": 0.0,
            "router_score": 0.0,
            "sovereign_score": 1.0,
            "wrapper_score": 1.0
          },
          "signals": {
            "capability_route": false,
            "founder_gate": true,
            "genesis_philosophy": true,
            "operator_pair": true,
            "providers": [
              "claude",
              "codex"
            ],
            "rtrace": false,
            "vision_keywords": true
          }
        },
        {
          "contract_id": "ASC-0175",
          "path": "docs/contracts/ASC-0175-memoryos-continuous-health-instrumentation.md",
          "scores": {
            "philosophy_score": 0.0,
            "retriever_score": 0.0,
            "router_score": 1.0,
            "sovereign_score": 1.0,
            "wrapper_score": 1.0
          },
          "signals": {
            "capability_route": true,
            "founder_gate": true,
            "genesis_philosophy": false,
            "operator_pair": true,
            "providers": [
              "claude",
              "codex",
              "local"
            ],
            "rtrace": false,
            "vision_keywords": true
          }
        },
        {
          "contract_id": "ASC-0178",
          "path": "docs/contracts/ASC-0178-aios-authority-model-phase-1.md",
          "scores": {
            "philosophy_score": 0.0,
            "retriever_score": 0.0,
            "router_score": 1.0,
            "sovereign_score": 1.0,
            "wrapper_score": 1.0
          },
          "signals": {
            "capability_route": true,
            "founder_gate": true,
            "genesis_philosophy": false,
            "operator_pair": true,
            "providers": [
              "claude",
              "codex"
            ],
            "rtrace": false,
            "vision_keywords": true
          }
        },
        {
          "contract_id": "ASC-0179",
          "path": "docs/contracts/ASC-0179-aios-ingest-protocol-local-first.md",
          "scores": {
            "philosophy_score": 0.0,
            "retriever_score": 0.0,
            "router_score": 0.0,
            "sovereign_score": 1.0,
            "wrapper_score": 1.0
          },
          "signals": {
            "capability_route": false,
            "founder_gate": true,
            "genesis_philosophy": false,
            "operator_pair": true,
            "providers": [
              "claude",
              "local"
            ],
            "rtrace": false,
            "vision_keywords": true
          }
        },
        {
          "contract_id": "ASC-0181",
          "path": "docs/contracts/ASC-0181-aios-workbench-developer-product.md",
          "scores": {
            "philosophy_score": 0.0,
            "retriever_score": 0.0,
            "router_score": 1.0,
            "sovereign_score": 1.0,
            "wrapper_score": 1.0
          },
          "signals": {
            "capability_route": true,
            "founder_gate": true,
            "genesis_philosophy": false,
            "operator_pair": true,
            "providers": [
              "claude",
              "local"
            ],
            "rtrace": false,
            "vision_keywords": true
          }
        },
        {
          "contract_id": "ASC-0182",
          "path": "docs/contracts/ASC-0182-first-matched-run-benchmark-execution.md",
          "scores": {
            "philosophy_score": 0.0,
            "retriever_score": 0.0,
            "router_score": 0.0,
            "sovereign_score": 1.0,
            "wrapper_score": 0.0
          },
          "signals": {
            "capability_route": false,
            "founder_gate": true,
            "genesis_philosophy": false,
            "operator_pair": true,
            "providers": [],
            "rtrace": false,
            "vision_keywords": true
          }
        }
      ],
      "relationship_to_governance_axis": "orthogonal_advisory_axis",
      "schema_version": "aios.persona_audit.v1",
      "scores": {
        "persona_composite": 0.44,
        "philosophy_score": 0.2,
        "retriever_score": 0.0,
        "router_score": 0.6,
        "sovereign_score": 1.0,
        "wrapper_score": 0.4
      },
      "window": 20
    },
    "schema_version": "aios.monitor.assessment.v1",
    "snapshot_generated_at": "2026-05-17T11:36:03+09:00",
    "watched": {
      "alerts": 3,
      "contracts": 187,
      "dispatches": 204,
      "reconciliations_applied": 5,
      "repos": 4
    }
  },
  "next_actions": [
    {
      "action": "collect_result_or_run_watcher",
      "owner": "myworld",
      "reason": "A sent dispatch has no collected result packet for at least one target repo.",
      "severity": "high"
    },
    {
      "action": "hold_for_repo_owner_triage",
      "owner": "CapabilityOS",
      "reason": "A child repo has uncommitted changes that need owner review before new work is stacked on it.",
      "severity": "medium"
    },
    {
      "action": "hold_for_repo_owner_triage",
      "owner": "GenesisOS",
      "reason": "A child repo has uncommitted changes that need owner review before new work is stacked on it.",
      "severity": "medium"
    },
    {
      "action": "review_prompt_prison_escape_vectors",
      "owner": "GenesisOS",
      "reason": "GenesisOS critic found advisory prompt-prison signatures in open contracts.",
      "severity": "info"
    },
    {
      "action": "review_5_persona_axis",
      "owner": "myworld",
      "reason": "AIOS 5-persona cognitive architecture score is advisory and orthogonal to governance.",
      "severity": "info"
    }
  ],
  "os_observatory": {
    "capability": {
      "capability_cards": 17,
      "gaps": 15,
      "headline": "17 cards, 156 observations, 15 gaps",
      "observations": 156,
      "observed_capabilities": 5,
      "result_files": 168,
      "status": "active",
      "top_routes": [
        {
          "id": "cap_hivemind_execution_harness",
          "name": "Hive Mind Execution Harness",
          "observation_count": 26,
          "requires_network": false,
          "risk": "low",
          "score": 57
        },
        {
          "id": "cap_workflow_recipe_map",
          "name": "Workflow Recipe Map",
          "observation_count": 0,
          "requires_network": false,
          "risk": "low",
          "score": 54
        },
        {
          "id": "cap_memoryos_context_build",
          "name": "MemoryOS Context Build",
          "observation_count": 0,
          "requires_network": false,
          "risk": "low",
          "score": 36
        },
        {
          "id": "cap_memoryos_import_run",
          "name": "MemoryOS Import Run",
          "observation_count": 15,
          "requires_network": false,
          "risk": "low",
          "score": 36
        },
        {
          "id": "cap_aios_route_planner",
          "name": "AIOS Capability Route Planner",
          "observation_count": 0,
          "requires_network": false,
          "risk": "low",
          "score": 35
        }
      ]
    },
    "genesis": {
      "authority": "speculative_only",
      "branch_types": [
        "inversion",
        "alien_domain",
        "constraint_removal",
        "failure_as_feature",
        "anti_user_prompt"
      ],
      "branches": 5,
      "headline": "5 speculative worldlines",
      "source_invocation": "chat-ae0b74ec9f46bf2c",
      "status": "active"
    },
    "hive": {
      "dispatch_total": 205,
      "headline": "dispatch_ready",
      "hive_board": {
        "agents": [
          {
            "name": "local-context-compressor",
            "status": "pending"
          },
          {
            "name": "claude-planner",
            "status": "pending"
          },
          {
            "name": "codex-executor",
            "status": "pending"
          },
          {
            "name": "gemini-reviewer",
            "status": "pending"
          },
          {
            "name": "local-log-summarizer",
            "status": "pending"
          },
          {
            "name": "verifier",
            "status": "pending"
          },
          {
            "name": "local-loop",
            "status": "prepared"
          }
        ],
        "artifacts": [
          {
            "exists": false,
            "name": "checks_report",
            "path": ".runs/run_20260516_133235_697d9c/checks_report.json",
            "status": "missing"
          },
          {
            "exists": false,
            "name": "commit_summary",
            "path": ".runs/run_20260516_133235_697d9c/commit_summary.md",
            "status": "missing"
          },
          {
            "exists": true,
            "name": "context_pack",
            "path": ".runs/run_20260516_133235_697d9c/context_pack.md",
            "status": "ok"
          },
          {
            "exists": true,
            "name": "events",
            "path": ".runs/run_20260516_133235_697d9c/events.jsonl",
            "status": "ok"
          },
          {
            "exists": true,
            "name": "final_report",
            "path": ".runs/run_20260516_133235_697d9c/final_report.md",
            "status": "ok"
          },
          {
            "exists": false,
            "name": "git_diff_report",
            "path": ".runs/run_20260516_133235_697d9c/git_diff_report.json",
            "status": "missing"
          },
          {
            "exists": true,
            "name": "handoff",
            "path": ".runs/run_20260516_133235_697d9c/handoff.yaml",
            "status": "ok"
          },
          {
            "exists": true,
            "name": "hive_events",
            "path": ".runs/run_20260516_133235_697d9c/hive_events.jsonl",
            "status": "ok"
          },
          {
            "exists": true,
            "name": "memory_drafts",
            "path": ".runs/run_20260516_133235_697d9c/memory_drafts.json",
            "status": "ok"
          },
          {
            "exists": false,
            "name": "routing_plan",
            "path": ".runs/run_20260516_133235_697d9c/routing_plan.json",
            "status": "missing"
          },
          {
            "exists": false,
            "name": "society_plan",
            "path": ".runs/run_20260516_133235_697d9c/society_plan.json",
            "status": "missing"
          },
          {
            "exists": true,
            "name": "task",
            "path": ".runs/run_20260516_133235_697d9c/task.yaml",
            "status": "ok"
          },
          {
            "exists": true,
            "name": "transcript",
            "path": ".runs/run_20260516_133235_697d9c/transcript.md",
            "status": "ok"
          },
          {
            "exists": true,
            "name": "verification",
            "path": ".runs/run_20260516_133235_697d9c/verification.yaml",
            "status": "ok"
          }
        ],
        "latest_event": "provider_loop_tick",
        "next": {
          "command": "hive run \"provider loop: You are codex@hivemind, invoked by the myworld AIOS child watcher.\n\nCurrent time: 2026-05-16T13:32:26+09:00\nMyWorld root: /home/user/workspaces/jaewon/myworld\nTarget repo: hivemind\nTarget repo path: /home/user/workspaces/jaewon/myworld/hivemind\nContract: ASC-0180\nDispatch: asc-0180\nContract path: docs/contracts/ASC-0180-hive-debate-aios-hosting-trust-model.md\n\nGoal:\nRun a Hive deliberation (ASC-0084 / ASC-0174 format, 6+ rounds, 3 voices) on the question \"how should AIOS hosting relate to the DNA — specifically the Preamble root-of-trust clause and Invariant 7 (privacy boundary) — given that Model A (invisible infra under uri) needs a non-localhost ingest endpoint to serve production users, but any non-localhost AIOS surface is the first AIOS component that is not local-first?\"\n\nRequired reading:\n- /home/user/workspaces/jaewon/myworld/AGENTS.md\n- /home/user/workspaces/jaewon/myworld/docs/AIOS_NORTHSTAR.md\n- /home/user/workspaces/jaewon/myworld/docs/AIOS_DEFINITION.md\n- /home/user/workspaces/jaewon/myworld/docs/AIOS_SHARED_LANGUAGE.md\n- /home/user/workspaces/jaewon/myworld/docs/AIOS_WORK_DISPATCH.md\n- /home/user/workspaces/jaewon/myworld/docs/AIOS_SMART_CONTRACT.md\n- /home/user/workspaces/jaewon/myworld/docs/AIOS_AGENT_PROTOCOL.md\n- /home/user/workspaces/jaewon/myworld/docs/contracts/ASC-0180-hive-debate-aios-hosting-trust-model.md\n- Repo-local AGENTS.md or README.md if present\n\nScope:\nAllowed files JSON:\n[\"hivemind/.runs/aios_hosting_debate/**\", \"hivemind/docs/AGENT_WORKLOG.md\", \"docs/discoveries/2026-05-15-hive-aios-hosting-debate-result.md\", \"docs/contracts/ASC-0180-hive-debate-aios-hosting-trust-model.md\", \"docs/AIOS_AGENT_LEDGER.md\"]\n\nForbidden files JSON:\n[\"any deployment manifest, hosting config, or cloud-provider code — this\"]\n\nOperating rules:\n- Start with a semantic_handshake: name the contract, target repo, confirmed\n  AIOS terms from /home/user/workspaces/jaewon/myworld/docs/AIOS_SHARED_LANGUAGE.md, and ambiguous_terms.\n  If ambiguous_terms is not empty, stop at a checkpoint.\n- Work from inside the target repo.\n- Do not claim AIOS progress unless the work advances one of the AIOS\n  completion levels in /home/user/workspaces/jaewon/myworld/docs/AIOS_DEFINITION.md.\n- Respect repo-local AGENTS.md and existing worklogs.\n- Do only the slice owned by hivemind.\n- Do not touch forbidden paths.\n- Do not paste private raw exports, secrets, stdout/stderr bodies, or local-only data.\n- If the dispatch is already satisfied, verify and write a concise result.\n- If ownership/scope is ambiguous, stop and explain the checkpoint instead of broadening scope.\n- Leave a repo-local worklog entry when the repo has an AGENT_WORKLOG or equivalent.\n- The watcher will write the outbox JSON; your stdout can be a concise human summary.\n\nDo one bounded turn. Do not start another watcher or infinite loop.\"",
          "reason": "route artifact missing"
        },
        "phase": "planned",
        "pipeline": [
          {
            "artifact": "task",
            "path": ".runs/run_20260516_133235_697d9c/task.yaml",
            "status": "done",
            "step": "intake"
          },
          {
            "artifact": "routing_plan",
            "path": ".runs/run_20260516_133235_697d9c/routing_plan.json",
            "status": "pending",
            "step": "route"
          },
          {
            "artifact": "context_pack",
            "path": ".runs/run_20260516_133235_697d9c/context_pack.md",
            "status": "done",
            "step": "context"
          },
          {
            "artifact": "claude_planner",
            "path": ".runs/run_20260516_133235_697d9c/agents/claude/planner_result.yaml",
            "status": "pending",
            "step": "deliberate"
          },
          {
            "artifact": "handoff",
            "path": ".runs/run_20260516_133235_697d9c/handoff.yaml",
            "status": "done",
            "step": "handoff"
          },
          {
            "artifact": "codex_executor",
            "path": ".runs/run_20260516_133235_697d9c/agents/codex/executor_result.yaml",
            "status": "pending",
            "step": "execute"
          },
          {
            "artifact": "verification",
            "path": ".runs/run_20260516_133235_697d9c/verification.yaml",
            "status": "pending",
            "step": "verify"
          },
          {
            "artifact": "memory_drafts",
            "path": ".runs/run_20260516_133235_697d9c/memory_drafts.json",
            "status": "empty",
            "step": "memory"
          },
          {
            "artifact": "final_report",
            "path": ".runs/run_20260516_133235_697d9c/final_report.md",
            "status": "initial",
            "step": "close"
          }
        ],
        "pipeline_done": 3,
        "pipeline_total": 9,
        "project": "Hive Mind",
        "run_id": "run_20260516_133235_697d9c",
        "status": "planned",
        "task": "provider loop: You are codex@hivemind, invoked by the myworld AIOS child watcher.\n\nCurrent time: 2026-05-16T13:32:26+09:00\nMyWorld root: /home/user/workspaces/jaewon/myworld\nTarget repo: hivemind\nTarget repo path: /home/user/workspaces/jaewon/myworld/hivemind\nContract: ASC-0180\nDispatch: asc-0180\nContract path: docs/contracts/ASC-0180-hive-debate-aios-hosting-trust-model.md\n\nGoal:\nRun a Hive deliberation (ASC-0084 / ASC-0174 format, 6+ rounds, 3 voices) on the question \"how should AIOS hosting relate to the DNA — specifically the Preamble root-of-trust clause and Invariant 7 (privacy boundary) — given that Model A (invisible infra under uri) needs a non-localhost ingest endpoint to serve production users, but any non-localhost AIOS surface is the first AIOS component that is not local-first?\"\n\nRequired reading:\n- /home/user/workspaces/jaewon/myworld/AGENTS.md\n- /home/user/workspaces/jaewon/myworld/docs/AIOS_NORTHSTAR.md\n- /home/user/workspaces/jaewon/myworld/docs/AIOS_DEFINITION.md\n- /home/user/workspaces/jaewon/myworld/docs/AIOS_SHARED_LANGUAGE.md\n- /home/user/workspaces/jaewon/myworld/docs/AIOS_WORK_DISPATCH.md\n- /home/user/workspaces/jaewon/myworld/docs/AIOS_SMART_CONTRACT.md\n- /home/user/workspaces/jaewon/myworld/docs/AIOS_AGENT_PROTOCOL.md\n- /home/user/workspaces/jaewon/myworld/docs/contracts/ASC-0180-hive-debate-aios-hosting-trust-model.md\n- Repo-local AGENTS.md or README.md if present\n\nScope:\nAllowed files JSON:\n[\"hivemind/.runs/aios_hosting_debate/**\", \"hivemind/docs/AGENT_WORKLOG.md\", \"docs/discoveries/2026-05-15-hive-aios-hosting-debate-result.md\", \"docs/contracts/ASC-0180-hive-debate-aios-hosting-trust-model.md\", \"docs/AIOS_AGENT_LEDGER.md\"]\n\nForbidden files JSON:\n[\"any deployment manifest, hosting config, or cloud-provider code — this\"]\n\nOperating rules:\n- Start with a semantic_handshake: name the contract, target repo, confirmed\n  AIOS terms from /home/user/workspaces/jaewon/myworld/docs/AIOS_SHARED_LANGUAGE.md, and ambiguous_terms.\n  If ambiguous_terms is not empty, stop at a checkpoint.\n- Work from inside the target repo.\n- Do not claim AIOS progress unless the work advances one of the AIOS\n  completion levels in /home/user/workspaces/jaewon/myworld/docs/AIOS_DEFINITION.md.\n- Respect repo-local AGENTS.md and existing worklogs.\n- Do only the slice owned by hivemind.\n- Do not touch forbidden paths.\n- Do not paste private raw exports, secrets, stdout/stderr bodies, or local-only data.\n- If the dispatch is already satisfied, verify and write a concise result.\n- If ownership/scope is ambiguous, stop and explain the checkpoint instead of broadening scope.\n- Leave a repo-local worklog entry when the repo has an AGENT_WORKLOG or equivalent.\n- The watcher will write the outbox JSON; your stdout can be a concise human summary.\n\nDo one bounded turn. Do not start another watcher or infinite loop.",
        "updated_at": "2026-05-16T13:32:36+09:00"
      },
      "latest_goal": "provider 실패 기억은?",
      "latest_invocation": "chat-ae0b74ec9f46bf2c",
      "next_action": "dispatch_ready",
      "status": "passed"
    },
    "lanes": [
      {
        "headline": "187 contracts / AIOS ready_to_install",
        "id": "myworld",
        "label": "MyWorld",
        "role": "Sovereign control",
        "status": "blocked"
      },
      {
        "headline": "44 accepted / 135 draft memories from 198,717 graph nodes",
        "id": "memory",
        "label": "MemoryOS",
        "role": "Knowledge graph",
        "status": "active"
      },
      {
        "headline": "17 cards, 156 observations, 15 gaps",
        "id": "capability",
        "label": "CapabilityOS",
        "role": "Search and route planner",
        "status": "active"
      },
      {
        "headline": "5 speculative worldlines",
        "id": "genesis",
        "label": "GenesisOS",
        "role": "Worldline generator",
        "status": "active"
      },
      {
        "headline": "dispatch_ready",
        "id": "hive",
        "label": "Hive Mind",
        "role": "Execution wrapper",
        "status": "passed"
      }
    ],
    "memory": {
      "accepted": 44,
      "draft": 135,
      "edges": 306522,
      "headline": "44 accepted / 135 draft memories from 198,717 graph nodes",
      "hyperedges": 35,
      "latest_review_at": "2026-05-15T22:29:52+09:00",
      "memory_objects": 187,
      "nodes": 198717,
      "rejected": 8,
      "retrieval_traces": 3539,
      "retrieval_traces_with_selected": 3426,
      "reviews": 53,
      "signals": [
        {
          "label": "Knowledge graph",
          "unit": "nodes",
          "value": 198717
        },
        {
          "label": "Provenance links",
          "unit": "edges",
          "value": 306522
        },
        {
          "label": "Reviewed memory",
          "unit": "accepted",
          "value": 44
        },
        {
          "label": "Retrieval traces",
          "unit": "traces",
          "value": 3539
        }
      ],
      "sources": 65,
      "status": "active"
    },
    "myworld": {
      "contracts": 187,
      "dispatches": 205,
      "headline": "187 contracts / AIOS ready_to_install",
      "installation": "ready_to_install",
      "round": "passed",
      "status": "blocked"
    }
  },
  "promotions": {
    "items": [
      {
        "contract_seed": ".aios/promotions/promotion-0990071087b3-20260514T031028/contract_seed.md",
        "created_at": "2026-05-14T03:10:28+09:00",
        "dispatch_preview": ".aios/invocations/asc-0145-smoke/dispatch/packets.json",
        "execution_started": false,
        "goal": "ASC-0145 promotion smoke",
        "next_action": "operator_assign_asc_accept_and_dispatch",
        "promotion_id": "promotion-0990071087b3-20260514T031028",
        "receipt": ".aios/promotions/promotion-0990071087b3-20260514T031028/promotion.json",
        "session_envelope_ref": ".aios/invocations/asc-0145-smoke/session_envelope.json",
        "status": "proposed_contract_seed",
        "stop_conditions": [
          "accepted_contract_missing",
          "executor_runs_without_dispatch_packet"
        ]
      }
    ],
    "total": 1
  },
  "repos": {
    "items": [
      {
        "changes": [],
        "dirty": false,
        "exists": true,
        "goal_count": 4,
        "inbox_count": 3,
        "outbox_count": 30,
        "repo": "hivemind",
        "route_count": 4
      },
      {
        "changes": [],
        "dirty": false,
        "exists": true,
        "goal_count": 0,
        "inbox_count": 3,
        "outbox_count": 18,
        "repo": "memoryOS",
        "route_count": 0
      },
      {
        "changes": [
          "?? docs/AIOS_AGENT_LEDGER.md"
        ],
        "dirty": true,
        "exists": true,
        "goal_count": 4,
        "inbox_count": 1,
        "outbox_count": 11,
        "repo": "CapabilityOS",
        "route_count": 3
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
            "inbox": 1,
            "outbox": 11,
            "pending": 0,
            "running": false
          },
          "GenesisOS": {
            "inbox": 0,
            "outbox": 2,
            "pending": 0,
            "running": false
          },
          "hivemind": {
            "inbox": 3,
            "outbox": 30,
            "pending": 0,
            "running": false
          },
          "memoryOS": {
            "inbox": 3,
            "outbox": 18,
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
    "generated_at": "2026-05-17T11:35:32+09:00",
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
          "generated_at": "2026-05-17T11:35:31+09:00",
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
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0041",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0042",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0043",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0044",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0045",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0046",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0047",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0048",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0049",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0050",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0051",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0052",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0053",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0054",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0055",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0056",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0057",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0058",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0059",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0060",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0061",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0062",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0063",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0064",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0065",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0066",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0067",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0068",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0069",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0070",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0071",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0072",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0073",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0074",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0075",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0076",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0077",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0078",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0079",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0080",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0081",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0082",
              "next": "operator_accept_revise_or_cancel",
              "status": "proposed"
            },
            {
              "contract_id": "ASC-0083",
              "next": "operator_accept_revise_or_cancel",
              "status": "proposed"
            },
            {
              "contract_id": "ASC-0084",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0085",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0086",
              "next": "operator_accept_revise_or_cancel",
              "status": "proposed"
            },
            {
              "contract_id": "ASC-0087",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0088",
              "next": "checkpoint_unknown_status",
              "status": "superseded"
            },
            {
              "contract_id": "ASC-0089",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0090",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0091",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0092",
              "next": "operator_accept_revise_or_cancel",
              "status": "proposed"
            },
            {
              "contract_id": "ASC-0093",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0094",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0095",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0096",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0096",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0097",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0098",
              "next": "operator_accept_revise_or_cancel",
              "status": "proposed"
            },
            {
              "contract_id": "ASC-0099",
              "dispatch_id": "asc-0099",
              "next": "ready_for_closeout",
              "pending_results": [],
              "status": "accepted"
            },
            {
              "contract_id": "ASC-0100",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0101",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0102",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0103",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0104",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0105",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0106",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0107",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0108",
              "next": "operator_accept_revise_or_cancel",
              "status": "proposed"
            },
            {
              "contract_id": "ASC-0109",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0110",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0111",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0112",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0113",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0114",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0115",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0116",
              "next": "checkpoint_missing_repos",
              "status": "accepted"
            },
            {
              "contract_id": "ASC-0117",
              "next": "checkpoint_missing_repos",
              "status": "accepted"
            },
            {
              "contract_id": "ASC-0118",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0119",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0120",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0121",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0122",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0123",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0124",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0125",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0126",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0127",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0128",
              "next": "checkpoint_unknown_status",
              "status": "withdrawn"
            },
            {
              "contract_id": "ASC-0129",
              "next": "checkpoint_unknown_status",
              "status": "withdrawn"
            },
            {
              "contract_id": "ASC-0130",
              "next": "checkpoint_unknown_status",
              "status": "withdrawn"
            },
            {
              "contract_id": "ASC-0131",
              "next": "checkpoint_unknown_status",
              "status": "superseded-by-rewrite"
            },
            {
              "contract_id": "ASC-0132",
              "next": "checkpoint_unknown_status",
              "status": "superseded-by-rewrite"
            },
            {
              "contract_id": "ASC-0133",
              "next": "checkpoint_unknown_status",
              "status": "superseded-by-rewrite"
            },
            {
              "contract_id": "ASC-0134",
              "next": "checkpoint_unknown_status",
              "status": "superseded-by-rewrite"
            },
            {
              "contract_id": "ASC-0135",
              "next": "operator_accept_revise_or_cancel",
              "status": "proposed"
            },
            {
              "contract_id": "ASC-0136",
              "next": "checkpoint_unknown_status",
              "status": "superseded-by-rewrite"
            },
            {
              "contract_id": "ASC-0137",
              "next": "operator_accept_revise_or_cancel",
              "status": "proposed"
            },
            {
              "contract_id": "ASC-0138",
              "next": "checkpoint_unknown_status",
              "status": "superseded-by-rewrite"
            },
            {
              "contract_id": "ASC-0139",
              "next": "checkpoint_unknown_status",
              "status": "superseded-by-rewrite"
            },
            {
              "contract_id": "ASC-0140",
              "next": "checkpoint_unknown_status",
              "status": "withdrawn"
            },
            {
              "contract_id": "ASC-0141",
              "next": "operator_accept_revise_or_cancel",
              "status": "proposed"
            },
            {
              "contract_id": "ASC-0142",
              "next": "checkpoint_unknown_status",
              "status": "withdrawn"
            },
            {
              "contract_id": "ASC-0143",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0144",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0145",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0146",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0147",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0148",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0149",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0150",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0151",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0152",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0152",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0153",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0154",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0155",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0156",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0157",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0158",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0159",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0160",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0161",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0162",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0163",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0164",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0165",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0166",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0167",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0168",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0169",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0170",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0171",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0172",
              "next": "checkpoint_unknown_status",
              "status": "withdrawn"
            },
            {
              "contract_id": "ASC-0173",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0174",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0175",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0176",
              "next": "checkpoint_unknown_status",
              "status": "withdrawn"
            },
            {
              "contract_id": "ASC-0177",
              "next": "checkpoint_unknown_status",
              "status": "withdrawn"
            },
            {
              "contract_id": "ASC-0178",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0179",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0180",
              "next": "checkpoint_missing_repos",
              "status": "accepted"
            },
            {
              "contract_id": "ASC-0181",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0182",
              "next": "archive_or_next_contract",
              "status": "closed"
            },
            {
              "contract_id": "ASC-0183",
              "next": "operator_accept_revise_or_cancel",
              "status": "proposed"
            },
            {
              "contract_id": "ASC-0184",
              "next": "checkpoint_missing_repos",
              "status": "accepted"
            },
            {
              "contract_id": "ASC-0185",
              "next": "checkpoint_missing_repos",
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
            "monitor_findings": 5,
            "monitor_health": "blocked",
            "policy_decision_count": 40,
            "policy_generated_at": "2026-05-17T11:35:31+09:00",
            "radar_candidate_count": 60,
            "readiness_level": 6,
            "readiness_level_name": "L6 repeatable"
          },
          "generated_at": "2026-05-17T11:35:31+09:00",
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
              "verification_signal"
            ],
            "blocked": false,
            "blocked_reasons": [],
            "candidate_task": "issue a Hive Mind packet for execution, harness, or verification follow-up",
            "domain": "hivemind",
            "goal_score": 183,
            "path": "myworld/hivemind/docs/HIVE_PRODUCT_EVALUATION.md",
            "policy_decision": "unknown",
            "policy_reason": "",
            "radar_score": 179,
            "signals": {
              "blocker": 6,
              "contract": 1,
              "gap": 1,
              "hivemind": 12,
              "memoryos": 5,
              "next": 9,
              "p0": 1,
              "verify": 4
            }
          },
          "schema_version": "aios.goal_evolution.v1",
          "stop_conditions": [
            "monitor_not_clear"
          ],
          "top_candidates": [
            {
              "alignment_reasons": [
                "verification_signal"
              ],
              "blocked": true,
              "blocked_reasons": [
                "history_source_requires_triage",
                "hold_for_capacity"
              ],
              "candidate_task": "issue a Hive Mind packet for execution, harness, or verification follow-up",
              "domain": "hivemind",
              "goal_score": 365,
              "path": "myworld/hivemind/docs/AGENT_WORKLOG.md",
              "policy_decision": "hold_for_capacity",
              "policy_reason": "open contract count 6 is at capacity 4",
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
                "dispatch_id": "asc-0182",
                "repos": [
                  "myworld"
                ]
              },
              "code": "dispatch_results_pending",
              "owner": "myworld",
              "reason": "A sent dispatch has no collected result packet for at least one target repo.",
              "severity": "high"
            },
            {
              "action": "hold_for_repo_owner_triage",
              "alert": {
                "code": "repo_dirty",
                "entries": [
                  "?? docs/AIOS_AGENT_LEDGER.md"
                ],
                "repo": "CapabilityOS"
              },
              "code": "repo_dirty",
              "owner": "CapabilityOS",
              "reason": "A child repo has uncommitted changes that need owner review before new work is stacked on it.",
              "severity": "medium"
            },
            {
              "action": "hold_for_repo_owner_triage",
              "alert": {
                "code": "repo_dirty",
                "entries": [
                  " M genesisos/cli.py",
                  " M genesisos/critic.py"
                ],
                "repo": "GenesisOS"
              },
              "code": "repo_dirty",
              "owner": "GenesisOS",
              "reason": "A child repo has uncommitted changes that need owner review before new work is stacked on it.",
              "severity": "medium"
            },
            {
              "action": "review_prompt_prison_escape_vectors",
              "alert": {
                "code": "genesis_prompt_prison_advisory",
                "flagged_count": 3,
                "report_schema_version": "aios.genesis_critic_dispatch.v1",
                "sample": [
                  {
                    "confidence": 0.5,
                    "contract_id": "ASC-0183",
                    "escape_vectors": [
                      "force one analogy from a distant domain before deciding",
                      "enumerate assumptions, then negate the top three",
                      "rewrite in plain language before using the jargon again"
                    ],
                    "path": "docs/contracts/ASC-0183-dream-parametric-per-repo-adapters.md",
                    "signature_count": 3,
                    "signatures": [
                      {
                        "escape_vector": "force one analogy from a distant domain before deciding",
                        "evidence": "no cross-domain frame markers found",
                        "signature": "single-frame"
                      },
                      {
                        "escape_vector": "enumerate assumptions, then negate the top three",
                        "evidence": "no explicit assumptions named",
                        "signature": "assumption-silent"
                      },
                      {
                        "escape_vector": "rewrite in plain language before using the jargon again",
                        "evidence": "jargon terms without unfolding: aios, capabilityos, contract, genesisos, hivemind, memoryos",
                        "signature": "terminology-trapped"
                      }
                    ],
                    "status": "proposed"
                  },
                  {
                    "confidence": 0.5,
                    "contract_id": "ASC-0184",
                    "escape_vectors": [
                      "force one analogy from a distant domain before deciding",
                      "enumerate assumptions, then negate the top three",
                      "rewrite in plain language before using the jargon again"
                    ],
                    "path": "docs/contracts/ASC-0184-hooks-deterministic-enforcement.md",
                    "signature_count": 3,
                    "signatures": [
                      {
                        "escape_vector": "force one analogy from a distant domain before deciding",
                        "evidence": "no cross-domain frame markers found",
                        "signature": "single-frame"
                      },
                      {
                        "escape_vector": "enumerate assumptions, then negate the top three",
                        "evidence": "no explicit assumptions named",
                        "signature": "assumption-silent"
                      },
                      {
                        "escape_vector": "rewrite in plain language before using the jargon again",
                        "evidence": "jargon terms without unfolding: agent, aios, contract, ledger",
                        "signature": "terminology-trapped"
                      }
                    ],
                    "status": "accepted"
                  },
                  {
                    "confidence": 0.667,
                    "contract_id": "ASC-0185",
                    "escape_vectors": [
                      "force one analogy from a distant domain before deciding",
                      "enumerate assumptions, then negate the top three",
                      "rewrite in plain language before using the jargon again",
                      "compare the answer in 1h, 1w, and 1y time horizons"
                    ],
                    "path": "docs/contracts/ASC-0185-leased-jobs-queue.md",
                    "signature_count": 4,
                    "signatures": [
                      {
                        "escape_vector": "force one analogy from a distant domain before deciding",
                        "evidence": "no cross-domain frame markers found",
                        "signature": "single-frame"
                      },
                      {
                        "escape_vector": "enumerate assumptions, then negate the top three",
                        "evidence": "no explicit assumptions named",
                        "signature": "assumption-silent"
                      },
                      {
                        "escape_vector": "rewrite in plain language before using the jargon again",
                        "evidence": "jargon terms without unfolding: aios, dispatch, provenance",
                        "signature": "terminology-trapped"
                      },
                      {
                        "escape_vector": "compare the answer in 1h, 1w, and 1y time horizons",
                        "evidence": "no short-term versus long-term alternative found",
                        "signature": "time-frozen"
                      }
                    ],
                    "status": "accepted"
                  }
                ],
                "scanned_count": 4
              },
              "code": "genesis_prompt_prison_advisory",
              "owner": "GenesisOS",
              "reason": "GenesisOS critic found advisory prompt-prison signatures in open contracts.",
              "severity": "info"
            },
            {
              "action": "review_5_persona_axis",
              "alert": {
                "code": "persona_axis_advisory",
                "contracts_scored": 20,
                "persona_composite": 0.44,
                "report_schema_version": "aios.persona_audit.v1"
              },
              "code": "persona_axis_advisory",
              "owner": "myworld",
              "reason": "AIOS 5-persona cognitive architecture score is advisory and orthogonal to governance.",
              "severity": "info"
            }
          ],
          "generated_at": "2026-05-17T11:35:31+09:00",
          "health": "blocked",
          "next_actions": [
            {
              "action": "collect_result_or_run_watcher",
              "owner": "myworld",
              "reason": "A sent dispatch has no collected result packet for at least one target repo.",
              "severity": "high"
            },
            {
              "action": "hold_for_repo_owner_triage",
              "owner": "CapabilityOS",
              "reason": "A child repo has uncommitted changes that need owner review before new work is stacked on it.",
              "severity": "medium"
            },
            {
              "action": "hold_for_repo_owner_triage",
              "owner": "GenesisOS",
              "reason": "A child repo has uncommitted changes that need owner review before new work is stacked on it.",
              "severity": "medium"
            },
            {
              "action": "review_prompt_prison_escape_vectors",
              "owner": "GenesisOS",
              "reason": "GenesisOS critic found advisory prompt-prison signatures in open contracts.",
              "severity": "info"
            },
            {
              "action": "review_5_persona_axis",
              "owner": "myworld",
              "reason": "AIOS 5-persona cognitive architecture score is advisory and orthogonal to governance.",
              "severity": "info"
            }
          ],
          "persona_axis": {
            "authority": "advisory_only",
            "contracts_scored": 20,
            "generated_at": "2026-05-17T11:35:31+09:00",
            "per_contract": [
              {
                "contract_id": "ASC-0159",
                "path": "docs/contracts/ASC-0159-aios-operating-layer-paper-draft.md",
                "scores": {
                  "philosophy_score": 0.0,
                  "retriever_score": 0.0,
                  "router_score": 1.0,
                  "sovereign_score": 1.0,
                  "wrapper_score": 0.0
                },
                "signals": {
                  "capability_route": true,
                  "founder_gate": true,
                  "genesis_philosophy": false,
                  "operator_pair": true,
                  "providers": [
                    "codex"
                  ],
                  "rtrace": false,
                  "vision_keywords": true
                }
              },
              {
                "contract_id": "ASC-0160",
                "path": "docs/contracts/ASC-0160-paper-refinement-loop.md",
                "scores": {
                  "philosophy_score": 1.0,
                  "retriever_score": 0.0,
                  "router_score": 1.0,
                  "sovereign_score": 1.0,
                  "wrapper_score": 0.0
                },
                "signals": {
                  "capability_route": true,
                  "founder_gate": true,
                  "genesis_philosophy": true,
                  "operator_pair": true,
                  "providers": [
                    "codex"
                  ],
                  "rtrace": false,
                  "vision_keywords": true
                }
              },
              {
                "contract_id": "ASC-0161",
                "path": "docs/contracts/ASC-0161-paper-related-work-source-evidence.md",
                "scores": {
                  "philosophy_score": 0.0,
                  "retriever_score": 0.0,
                  "router_score": 1.0,
                  "sovereign_score": 1.0,
                  "wrapper_score": 0.0
                },
                "signals": {
                  "capability_route": true,
                  "founder_gate": true,
                  "genesis_philosophy": false,
                  "operator_pair": true,
                  "providers": [
                    "codex"
                  ],
                  "rtrace": true,
                  "vision_keywords": true
                }
              },
              {
                "contract_id": "ASC-0162",
                "path": "docs/contracts/ASC-0162-direct-cli-vs-aios-benchmark-protocol.md",
                "scores": {
                  "philosophy_score": 0.0,
                  "retriever_score": 0.0,
                  "router_score": 1.0,
                  "sovereign_score": 1.0,
                  "wrapper_score": 0.0
                },
                "signals": {
                  "capability_route": true,
                  "founder_gate": true,
                  "genesis_philosophy": false,
                  "operator_pair": true,
                  "providers": [
                    "codex"
                  ],
                  "rtrace": false,
                  "vision_keywords": true
                }
              },
              {
                "contract_id": "ASC-0163",
                "path": "docs/contracts/ASC-0163-negative-evidence-combinatorial-creativity.md",
                "scores": {
                  "philosophy_score": 1.0,
                  "retriever_score": 0.0,
                  "router_score": 1.0,
                  "sovereign_score": 1.0,
                  "wrapper_score": 1.0
                },
                "signals": {
                  "capability_route": true,
                  "founder_gate": true,
                  "genesis_philosophy": true,
                  "operator_pair": true,
                  "providers": [
                    "claude",
                    "codex",
                    "local",
                    "ollama"
                  ],
                  "rtrace": true,
                  "vision_keywords": true
                }
              },
              {
                "contract_id": "ASC-0164",
                "path": "docs/contracts/ASC-0164-genesisos-child-watcher-surface.md",
                "scores": {
                  "philosophy_score": 0.0,
                  "retriever_score": 0.0,
                  "router_score": 1.0,
                  "sovereign_score": 1.0,
                  "wrapper_score": 0.0
                },
                "signals": {
                  "capability_route": true,
                  "founder_gate": true,
                  "genesis_philosophy": false,
                  "operator_pair": true,
                  "providers": [
                    "codex"
                  ],
                  "rtrace": false,
                  "vision_keywords": true
                }
              },
              {
                "contract_id": "ASC-0165",
                "path": "docs/contracts/ASC-0165-memory-genesis-provider-blindspot-reinforcement.md",
                "scores": {
                  "philosophy_score": 1.0,
                  "retriever_score": 0.0,
                  "router_score": 1.0,
                  "sovereign_score": 1.0,
                  "wrapper_score": 1.0
                },
                "signals": {
                  "capability_route": true,
                  "founder_gate": true,
                  "genesis_philosophy": true,
                  "operator_pair": true,
                  "providers": [
                    "claude",
                    "codex",
                    "local"
                  ],
                  "rtrace": false,
                  "vision_keywords": true
                }
              },
              {
                "contract_id": "ASC-0166",
                "path": "docs/contracts/ASC-0166-provider-pin-required-classification.md",
                "scores": {
                  "philosophy_score": 0.0,
                  "retriever_score": 0.0,
                  "router_score": 0.0,
                  "sovereign_score": 1.0,
                  "wrapper_score": 1.0
                },
                "signals": {
                  "capability_route": false,
                  "founder_gate": true,
                  "genesis_philosophy": false,
                  "operator_pair": true,
                  "providers": [
                    "claude",
                    "codex",
                    "local"
                  ],
                  "rtrace": false,
                  "vision_keywords": true
                }
              },
              {
                "contract_id": "ASC-0167",
                "path": "docs/contracts/ASC-0167-capabilityos-permissioned-constraint-break-route.md",
                "scores": {
                  "philosophy_score": 0.0,
                  "retriever_score": 0.0,
                  "router_score": 0.0,
                  "sovereign_score": 1.0,
                  "wrapper_score": 0.0
                },
                "signals": {
                  "capability_route": false,
                  "founder_gate": true,
                  "genesis_philosophy": false,
                  "operator_pair": true,
                  "providers": [
                    "codex"
                  ],
                  "rtrace": false,
                  "vision_keywords": true
                }
              },
              {
                "contract_id": "ASC-0168",
                "path": "docs/contracts/ASC-0168-hivemind-permission-preflight.md",
                "scores": {
                  "philosophy_score": 0.0,
                  "retriever_score": 0.0,
                  "router_score": 0.0,
                  "sovereign_score": 1.0,
                  "wrapper_score": 0.0
                },
                "signals": {
                  "capability_route": false,
                  "founder_gate": true,
                  "genesis_philosophy": false,
                  "operator_pair": true,
                  "providers": [
                    "codex"
                  ],
                  "rtrace": false,
                  "vision_keywords": true
                }
              },
              {
                "contract_id": "ASC-0169",
                "path": "docs/contracts/ASC-0169-hivemind-aios-packet-runner.md",
                "scores": {
                  "philosophy_score": 0.0,
                  "retriever_score": 0.0,
                  "router_score": 1.0,
                  "sovereign_score": 1.0,
                  "wrapper_score": 0.0
                },
                "signals": {
                  "capability_route": true,
                  "founder_gate": true,
                  "genesis_philosophy": false,
                  "operator_pair": true,
                  "providers": [
                    "local"
                  ],
                  "rtrace": false,
                  "vision_keywords": true
                }
              },
              {
                "contract_id": "ASC-0170",
                "path": "docs/contracts/ASC-0170-hivemind-scoped-writable-provider-execution.md",
                "scores": {
                  "philosophy_score": 0.0,
                  "retriever_score": 0.0,
                  "router_score": 1.0,
                  "sovereign_score": 1.0,
                  "wrapper_score": 0.0
                },
                "signals": {
                  "capability_route": true,
                  "founder_gate": true,
                  "genesis_philosophy": false,
                  "operator_pair": true,
                  "providers": [
                    "codex"
                  ],
                  "rtrace": false,
                  "vision_keywords": true
                }
              },
              {
                "contract_id": "ASC-0171",
                "path": "docs/contracts/ASC-0171-hivemind-permissioned-dangerous-provider-execution.md",
                "scores": {
                  "philosophy_score": 0.0,
                  "retriever_score": 0.0,
                  "router_score": 0.0,
                  "sovereign_score": 1.0,
                  "wrapper_score": 0.0
                },
                "signals": {
                  "capability_route": false,
                  "founder_gate": true,
                  "genesis_philosophy": false,
                  "operator_pair": true,
                  "providers": [
                    "codex"
                  ],
                  "rtrace": false,
                  "vision_keywords": true
                }
              },
              {
                "contract_id": "ASC-0173",
                "path": "docs/contracts/ASC-0173-product-repo-consent-emitted-evidence-ingest.md",
                "scores": {
                  "philosophy_score": 0.0,
                  "retriever_score": 0.0,
                  "router_score": 0.0,
                  "sovereign_score": 1.0,
                  "wrapper_score": 0.0
                },
                "signals": {
                  "capability_route": false,
                  "founder_gate": true,
                  "genesis_philosophy": false,
                  "operator_pair": true,
                  "providers": [
                    "claude"
                  ],
                  "rtrace": false,
                  "vision_keywords": true
                }
              },
              {
                "contract_id": "ASC-0174",
                "path": "docs/contracts/ASC-0174-hive-debate-observer-vs-executor-reframe.md",
                "scores": {
                  "philosophy_score": 1.0,
                  "retriever_score": 0.0,
                  "router_score": 0.0,
                  "sovereign_score": 1.0,
                  "wrapper_score": 1.0
                },
                "signals": {
                  "capability_route": false,
                  "founder_gate": true,
                  "genesis_philosophy": true,
                  "operator_pair": true,
                  "providers": [
                    "claude",
                    "codex"
                  ],
                  "rtrace": false,
                  "vision_keywords": true
                }
              },
              {
                "contract_id": "ASC-0175",
                "path": "docs/contracts/ASC-0175-memoryos-continuous-health-instrumentation.md",
                "scores": {
                  "philosophy_score": 0.0,
                  "retriever_score": 0.0,
                  "router_score": 1.0,
                  "sovereign_score": 1.0,
                  "wrapper_score": 1.0
                },
                "signals": {
                  "capability_route": true,
                  "founder_gate": true,
                  "genesis_philosophy": false,
                  "operator_pair": true,
                  "providers": [
                    "claude",
                    "codex",
                    "local"
                  ],
                  "rtrace": false,
                  "vision_keywords": true
                }
              },
              {
                "contract_id": "ASC-0178",
                "path": "docs/contracts/ASC-0178-aios-authority-model-phase-1.md",
                "scores": {
                  "philosophy_score": 0.0,
                  "retriever_score": 0.0,
                  "router_score": 1.0,
                  "sovereign_score": 1.0,
                  "wrapper_score": 1.0
                },
                "signals": {
                  "capability_route": true,
                  "founder_gate": true,
                  "genesis_philosophy": false,
                  "operator_pair": true,
                  "providers": [
                    "claude",
                    "codex"
                  ],
                  "rtrace": false,
                  "vision_keywords": true
                }
              },
              {
                "contract_id": "ASC-0179",
                "path": "docs/contracts/ASC-0179-aios-ingest-protocol-local-first.md",
                "scores": {
                  "philosophy_score": 0.0,
                  "retriever_score": 0.0,
                  "router_score": 0.0,
                  "sovereign_score": 1.0,
                  "wrapper_score": 1.0
                },
                "signals": {
                  "capability_route": false,
                  "founder_gate": true,
                  "genesis_philosophy": false,
                  "operator_pair": true,
                  "providers": [
                    "claude",
                    "local"
                  ],
                  "rtrace": false,
                  "vision_keywords": true
                }
              },
              {
                "contract_id": "ASC-0181",
                "path": "docs/contracts/ASC-0181-aios-workbench-developer-product.md",
                "scores": {
                  "philosophy_score": 0.0,
                  "retriever_score": 0.0,
                  "router_score": 1.0,
                  "sovereign_score": 1.0,
                  "wrapper_score": 1.0
                },
                "signals": {
                  "capability_route": true,
                  "founder_gate": true,
                  "genesis_philosophy": false,
                  "operator_pair": true,
                  "providers": [
                    "claude",
                    "local"
                  ],
                  "rtrace": false,
                  "vision_keywords": true
                }
              },
              {
                "contract_id": "ASC-0182",
                "path": "docs/contracts/ASC-0182-first-matched-run-benchmark-execution.md",
                "scores": {
                  "philosophy_score": 0.0,
                  "retriever_score": 0.0,
                  "router_score": 0.0,
                  "sovereign_score": 1.0,
                  "wrapper_score": 0.0
                },
                "signals": {
                  "capability_route": false,
                  "founder_gate": true,
                  "genesis_philosophy": false,
                  "operator_pair": true,
                  "providers": [],
                  "rtrace": false,
                  "vision_keywords": true
                }
              }
            ],
            "relationship_to_governance_axis": "orthogonal_advisory_axis",
            "schema_version": "aios.persona_audit.v1",
            "scores": {
              "persona_composite": 0.44,
              "philosophy_score": 0.2,
              "retriever_score": 0.0,
              "router_score": 0.6,
              "sovereign_score": 1.0,
              "wrapper_score": 0.4
            },
            "window": 20
          },
          "schema_version": "aios.monitor.assessment.v1",
          "snapshot_generated_at": "2026-05-17T11:35:31+09:00",
          "watched": {
            "alerts": 3,
            "contracts": 187,
            "dispatches": 204,
            "reconciliations_applied": 5,
            "repos": 4
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
          "ASC-0178"
        ],
        "name": "A 15th \"Bind ASC-0066...\" template clone is autodrafted while this contract is open (signals Packet B did not bind)."
      },
      {
        "contracts": [
          "ASC-0182"
        ],
        "name": "A fixture requires private data → stop, redesign fixture."
      },
      {
        "contracts": [
          "ASC-0184"
        ],
        "name": "A hook would block the autopoietic loop on a false positive → the soft checks fail-open and log; only the privacy hook fails-closed."
      },
      {
        "contracts": [
          "ASC-0181"
        ],
        "name": "A hosting / non-localhost surface is added (that is Model A / ASC-0180)."
      },
      {
        "contracts": [
          "ASC-0182"
        ],
        "name": "A matched pair cannot hold provider/model/snapshot constant → exclude the pair per the protocol's Exclusions, do not fabricate a substitute."
      },
      {
        "contracts": [
          "ASC-0183"
        ],
        "name": "A re-fit adapter regresses on held-out verified invocations → discard the draft, keep the prior adapter, record the regression as negative evidence."
      },
      {
        "contracts": [
          "ASC-0179"
        ],
        "name": "A second, divergent ingestion path is created instead of reusing the ASC-0173 pipeline."
      },
      {
        "contracts": [
          "ASC-0178"
        ],
        "name": "Any reconciliation flip deletes a contract instead of setting a status."
      },
      {
        "contracts": [
          "ASC-0179"
        ],
        "name": "Auth, TLS, or multi-tenant code appears (same reason)."
      },
      {
        "contracts": [
          "ASC-0184"
        ],
        "name": "Enforcement conflicts with an accepted contract → escalate, do not silently override the contract."
      },
      {
        "contracts": [
          "ASC-0185"
        ],
        "name": "If atomic rename is unavailable on the target filesystem → fall back to a lock file, do not silently drop the lease guarantee."
      },
      {
        "contracts": [
          "ASC-0185"
        ],
        "name": "Migration risk: existing in-flight `.aios/inbox` packets must be adopted into the queue without loss → ship a one-time adopt step; do not strand live packets."
      }
    ]
  },
  "workbench": {
    "registered_repo_count": 4,
    "repos": [
      {
        "kind": "product_repo",
        "note": "ASC-0181 Packet A verification — non-uri product repo",
        "observed_capabilities": [
          {
            "id": "cap_demoagent_python",
            "observation_count": 1,
            "observed_sprints": [
              "DEMO-001"
            ]
          },
          {
            "id": "cap_demoagent_sqlite",
            "observation_count": 1,
            "observed_sprints": [
              "DEMO-001"
            ]
          },
          {
            "id": "cap_demoagent_embeddings",
            "observation_count": 1,
            "observed_sprints": [
              "DEMO-001"
            ]
          }
        ],
        "registered_at": "2026-05-16T16:26:33+09:00",
        "repo": "demoagent",
        "sprint_ids": [
          "DEMO-001"
        ],
        "sprints_absorbed": 1
      },
      {
        "kind": "product_repo",
        "note": "workbench init from /tmp/qs-verify-repo",
        "observed_capabilities": [
          {
            "id": "cap_quickstartdemo_python",
            "observation_count": 1,
            "observed_sprints": [
              "QS-001"
            ]
          },
          {
            "id": "cap_quickstartdemo_fastapi",
            "observation_count": 1,
            "observed_sprints": [
              "QS-001"
            ]
          }
        ],
        "registered_at": "2026-05-16T16:38:41+09:00",
        "repo": "quickstartdemo",
        "sprint_ids": [
          "QS-001"
        ],
        "sprints_absorbed": 1
      },
      {
        "kind": "product_repo",
        "note": "workbench init from /tmp/demo-agent-repo",
        "observed_capabilities": [
          {
            "id": "cap_testbench01_python",
            "observation_count": 1,
            "observed_sprints": [
              "TB-001"
            ]
          },
          {
            "id": "cap_testbench01_asyncio",
            "observation_count": 1,
            "observed_sprints": [
              "TB-001"
            ]
          }
        ],
        "registered_at": "2026-05-16T16:34:44+09:00",
        "repo": "testbench01",
        "sprint_ids": [
          "TB-001"
        ],
        "sprints_absorbed": 1
      },
      {
        "kind": "product_repo",
        "note": "first product repo (ASC-0173)",
        "observed_capabilities": [
          {
            "id": "cap_uri_nextjs",
            "observation_count": 3,
            "observed_sprints": [
              "URI-210",
              "URI-211",
              "URI-212"
            ]
          },
          {
            "id": "cap_uri_kakao_map",
            "observation_count": 1,
            "observed_sprints": [
              "URI-210"
            ]
          },
          {
            "id": "cap_uri_vercel_deploy",
            "observation_count": 2,
            "observed_sprints": [
              "URI-210",
              "URI-211"
            ]
          },
          {
            "id": "cap_uri_share_card_og",
            "observation_count": 2,
            "observed_sprints": [
              "URI-210",
              "URI-211"
            ]
          },
          {
            "id": "cap_uri_pilot_template",
            "observation_count": 2,
            "observed_sprints": [
              "URI-210",
              "URI-212"
            ]
          }
        ],
        "registered_at": "2026-05-16T16:26:03+09:00",
        "repo": "uri",
        "sprint_ids": [
          "URI-210",
          "URI-211",
          "URI-212"
        ],
        "sprints_absorbed": 3
      }
    ],
    "schema": "aios.workbench_snapshot.v1"
  }
};

"""Pytest configuration for ``pytest tests/`` — OSS-release skip policy.

This repository (the AIOS control plane) is public, but the four execution
siblings it coordinates — GenesisOS, memoryOS, CapabilityOS, hivemind — and the
private product repo ``uri/`` are **not**. They are wired in as git submodules
that stay EMPTY on a clean public clone. A handful of tests additionally assert
operator-machine state under ``.aios/`` (the dispatch ledger, invocation
receipts, the serving gate) that is never part of the OSS artifact.

Those tests cannot pass from a clean clone because a required *prerequisite is
absent* — **not** because of a product bug. Rather than delete them or let them
fail the release gate, we skip exactly those items, and only when the concrete
prerequisite is missing. Every entry below names the concrete missing path, so
each skip is honest and self-verifying: on a full operator/dev checkout — where
the submodules are populated and the ``.aios/`` state exists — NOTHING is
skipped and the whole suite runs. (Two files guard themselves in-file via
``pytest.importorskip`` / ``pytest.skip(allow_module_level=True)`` —
``test_aios_h1_gate.py`` and ``test_aios_capability_observation_memory_review.py``
— and are intentionally left untouched here.)

A key is a pytest node-id fragment:

* a bare ``<file>.py`` applies to *every* test in that file (the whole file
  targets a private-sibling-backed script that cannot import on a clean clone);
* ``<file>.py::<Class>::<method>`` applies to that *single* test (the file also
  contains tests that run fine on a clean clone — those keep running).

Each value is a repo-root-relative path present on a full checkout and absent on
a clean public clone, plus a human reason naming the missing prerequisite.
"""

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent

# ── Prerequisite markers ─────────────────────────────────────────────────────
# Present on a full operator/dev checkout; absent on a clean public clone.
_GENESIS = ("GenesisOS/genesisos/__init__.py", "the GenesisOS sibling submodule (private research repo)")
_MEMORY = ("memoryOS/memoryos/__init__.py", "the memoryOS sibling submodule (private research repo)")
_MEMORY_AKASHIC = ("memoryOS/memoryos/akashic_ledger.py", "the memoryOS sibling submodule (private research repo)")
_CAPABILITY = ("CapabilityOS/capabilityos/cli.py", "the CapabilityOS sibling submodule (private research repo)")
_HIVE = ("hivemind/hivemind/hive.py", "the hivemind sibling submodule (private research repo)")
_URI = ("uri/docs/URI_NORTHSTAR.md", "the private uri/ product repo")
_DISPATCH_STATE = (".aios/state/dispatches.jsonl", "operator-machine AIOS dispatch/result state")
_SERVING_GATE = (".aios/serving/design_gate.json", "operator-machine AIOS serving-gate state")
_PAPER_0160 = (".aios/invocations/asc-0160-paper-refinement", "operator-machine AIOS invocation receipts")
_PAPER_0163 = (".aios/invocations/asc-0163-negative-evidence-creativity", "operator-machine AIOS invocation receipts")

# ── node-id fragment -> (relative path, reason) ──────────────────────────────
_REQUIREMENTS: dict[str, tuple[str, str]] = {
    # Whole files: every test imports/exec-s a private research sibling.
    "test_aios_accepted_memory_surfaces.py": _MEMORY,
    "test_aios_genesis_analogy.py": _GENESIS,
    "test_aios_genesis_branch.py": _GENESIS,
    "test_aios_genesis_challenge.py": _GENESIS,
    "test_aios_genesis_critic_dispatch.py": _GENESIS,
    "test_aios_genesis_modal.py": _GENESIS,
    "test_aios_genesis_mutate.py": _GENESIS,
    "test_aios_genesis_seed_capture.py": _GENESIS,
    "test_aios_live_hosted_proof.py": _HIVE,
    # Single tests: the file also has clean-clone-safe tests that must keep running.
    "test_aios_akashic.py::TestAiosAkashicParity::test_list_count_matches_load_indexes": _MEMORY_AKASHIC,
    "test_aios_capability_mcp.py::CapabilityMcpTest::test_audit_returns_catalog_state": _CAPABILITY,
    "test_aios_chat_router.py::AiosChatRouterTest::test_action_turn_projects_genesis_friction_when_available": _GENESIS,
    "test_aios_chat_router.py::AiosChatRouterTest::test_genesis_friction_question_answers_without_provider_turn": _GENESIS,
    "test_aios_chat_router.py::AiosChatRouterTest::test_provider_word_does_not_steal_action_turn_from_hive": _GENESIS,
    "test_aios_memory_retrieval_audit.py::AiosMemoryRetrievalAuditTests::test_audit_explains_task_filtered_miss": _MEMORY,
    "test_aios_memory_retrieval_audit.py::AiosMemoryRetrievalAuditTests::test_audit_reports_hit_rate_and_trace_ids": _MEMORY,
    "test_aios_memory_retrieval_audit.py::AiosMemoryRetrievalAuditTests::test_domain_coverage_alarm_when_only_internal": _MEMORY,
    "test_aios_memory_retrieval_audit.py::AiosMemoryRetrievalAuditTests::test_domain_coverage_counts_product": _MEMORY,
    "test_aios_monitor.py::AiosMonitorTest::test_reviewed_genesis_findings_do_not_emit_monitor_advisory": _GENESIS,
    "test_aios_turn_loop.py::TurnLoopTests::test_loop_detected_injects_genesis_direction": _GENESIS,
    "test_aios_web_evidence_memory_review.py::AiosWebEvidenceMemoryReviewTest::test_memoryos_import_run_dry_run_accepts_generated_bundle": _MEMORY,
    "test_aios_institution_readiness.py::AiosInstitutionReadinessTest::test_current_repo_reports_no_real_world_authority_claim": _DISPATCH_STATE,
    "test_aios_invoke.py::AiosInvokeTest::test_capability_executes_tools_is_blocked": _CAPABILITY,
    "test_aios_invoke.py::AiosInvokeTest::test_happy_path_writes_all_artifacts_with_mocked_roles": _CAPABILITY,
    "test_aios_invoke.py::AiosInvokeTest::test_plan_only_does_not_modify_child_source_mtime": _CAPABILITY,
    "test_aios_launcher.py::AiosLauncherTest::test_provider_loop_command_constructs_hive_delegation": _HIVE,
    "test_aios_paper.py::AiosPaperDraftTest::test_asc0163_role_artifacts_are_recorded": _PAPER_0163,
    "test_aios_paper.py::AiosPaperDraftTest::test_refinement_loop_artifacts_are_recorded": _PAPER_0160,
    "test_aios_serving_release_gate.py::AiosServingReleaseGateTest::test_current_repo_serving_release_ready": _SERVING_GATE,
    "test_aios_uri_filter.py::AiosUriFilterTest::test_doc_scout_reports_uri_filter_counts": _URI,
    "test_aios_uri_filter.py::AiosUriFilterTest::test_real_uri_examples_classify_expected_paths": _URI,
    "test_aios_world_readiness.py::AiosWorldReadinessTest::test_current_repo_world_readiness_achieved": _SERVING_GATE,
}


def _missing(relative_path: str) -> bool:
    return not (_REPO_ROOT / relative_path).exists()


def _selector_matches(nodeid: str, selector: str) -> bool:
    if "::" in selector:  # single-test selector
        return selector in nodeid
    # whole-file selector: match the "<dir>/<file>::" boundary exactly.
    return ("/" + selector + "::") in ("/" + nodeid)


def pytest_collection_modifyitems(config, items):
    for item in items:
        for selector, (relative_path, reason) in _REQUIREMENTS.items():
            if _selector_matches(item.nodeid, selector) and _missing(relative_path):
                item.add_marker(
                    pytest.mark.skip(
                        reason=f"requires {reason} at '{relative_path}' "
                        "(absent on a clean public clone / operator machine)"
                    )
                )
                break

---
contract_id: ASC-0243
slug: hosted-backend-selection-and-release-archive-smoke
status: closed
goal: Select AIOS's first hosted worker backend tier and prove install from a clean release/archive tree with credential broker references only.
created: 2026-06-13T00:12:00+09:00
closed: 2026-06-13T00:14:00+09:00
origin: ASC-0242 closed privacy-safe fresh-copy install smoke, but clean release/archive smoke and hosted backend choice remain unproven.
---

# ASC-0243 Hosted Backend Selection And Release Archive Smoke

## Why Now

ASC-0242 proves a working-tree fresh-copy dry-run install. The next deployment
step needs a backend decision and a clean archive/release smoke. Otherwise AIOS
can appear world-ready while still depending on this dirty local workspace.

## External State Checked

Primary sources consulted on 2026-06-13 KST:

- OpenAI Codex docs: Codex Cloud runs in isolated managed containers with setup
  and agent phases; CLI/app sandboxing has filesystem and network controls.
- Anthropic release notes: Claude Managed Agents webhooks, multi-agent
  orchestration, and self-hosted sandboxes are available on Claude Platform on
  AWS.
- Anthropic Claude Code SDK docs: the Agent SDK exposes the Claude Code agent
  loop, tools, hooks, and context management programmatically.
- Google Gemini API docs: Interactions API supports server-side history,
  background processing, and agentic workflows; Deep Research is an agentic
  long-running research workflow; tool combination lets built-in tools and
  custom function calling share tool context.

## Backend Tiers

Recommended first tier order:

1. `local-first release archive`
   - authority: `execute_with_receipt`
   - purpose: prove a clean committed/archive tree installs and runs local
     receipts without hosted credentials.
2. `codex_cloud_optional`
   - authority: `operator_checkpoint_required`
   - purpose: isolated managed coding worker for repo tasks when OpenAI account
     state and environment setup are available.
3. `anthropic_managed_agents_optional`
   - authority: `operator_checkpoint_required`
   - purpose: AWS/self-hosted sandbox route for Claude Managed Agents when
     platform access and IAM policies are configured.
4. `gemini_interactions_research_optional`
   - authority: `recommendation_only`
   - purpose: long-running web/research ingestion through server-side history
     and tool combination, projected into MemoryOS drafts.

## Scope

repos:

- `myworld`
- `hivemind`
- `memoryOS`
- `CapabilityOS`

allowed_files:

- `docs/contracts/ASC-0243-hosted-backend-selection-and-release-archive-smoke.md`
- `docs/AIOS_AGENT_LEDGER.md`
- future release/archive smoke scripts and tests named by this contract

forbidden_files:

- `.env`
- `.env.*`
- provider auth files
- credential vault contents
- raw provider logs
- private history stores

## Required Work

1. Produce a clean archive from committed/selected source files, not dirty
   workspace state.
2. Run `scripts/aios_install.sh` dry-run from that archive with isolated
   `HOME`, `XDG_CONFIG_HOME`, `AIOS_VAULT_DIR`, and `AIOS_SHELL_RC`.
3. Verify provider credential requests become broker receipts.
4. Emit a backend selection receipt explaining whether the first hosted route
   is `codex_cloud_optional`, `anthropic_managed_agents_optional`,
   `gemini_interactions_research_optional`, or local-only until operator
   credentials/accounts are configured.
5. Project the release/archive smoke into MemoryOS Akashic lineage.

## Acceptance Tests

- release/archive smoke exits 0
- no `.git`, `.aios`, `.runs`, provider auth files, or raw private history are
  included in the archive proof
- credential requests are references/receipts only
- backend selection receipt names required operator/account prerequisites
- MemoryOS projection is replayable by work id

## Result

`scripts/aios_release_archive_proof.py` now builds a selected-source
`aios-selected-source.tar.gz` archive from explicit files only:

- `scripts/aios_install.sh`
- `scripts/aios_provider.py`
- `scripts/aios_credential_broker.py`
- `scripts/aios_vault.py`

The proof extracts the archive into an isolated temp root, runs
`scripts/aios_install.sh` in dry-run mode with isolated `HOME`,
`XDG_CONFIG_HOME`, `AIOS_VAULT_DIR`, and `AIOS_SHELL_RC`, verifies provider
status, and emits a backend selection receipt.

Backend selection:

- selected first tier: `local_first_release_archive`
- optional hosted tiers:
  - `codex_cloud_optional`
  - `anthropic_managed_agents_optional`
  - `gemini_interactions_research_optional`

Evidence:

- `python3 -m unittest tests.test_aios_release_archive_proof -v` passed.
- `python3 scripts/aios_release_archive_proof.py --json` passed with
  `ok=true`, `install_returncode=0`, `provider_status_returncode=0`,
  `archive_forbidden_runtime_or_private_paths_present=[]`, and
  `wrote_operator_shell_rc=false`.

Boundary:

This closes selected-source release/archive smoke and backend tier selection.
It does not claim a pushed release tag, PyPI/npm package, live hosted provider
environment, or clean dirty-tree commit.

## Stop Conditions

- `dirty_tree_claimed_as_release`
- `credential_value_in_release_receipt`
- `hosted_backend_selected_without_operator_prereqs`
- `raw_provider_history_in_archive`

## Next

After this closes, AIOS can move from deployment-readiness proofs into actual
operator release: scoped commit, push, release tag/archive, and optional hosted
provider environment setup.

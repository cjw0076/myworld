# AIOS Getting Started

A quick guide to running tasks with the AIOS harness.

## 1. Running a goal

```bash
# Shortest form (zero-friction alias)
aios do "list files in current directory"

# Explicit harness entry
aios harness "fix the bug in auth.py"

# Dry run — shows tool plan without executing
aios harness "search for X" --dry-run

# Restrict to specific tools
aios harness "read config.py" --tools Read,Bash

# Choose provider explicitly
aios harness "write tests for parser.py" --provider codex

# JSON output
aios harness "build and verify" --json
```

The harness auto-routes to the best provider via the role router (see §3).
A run log is written to `.aios/runtime/receipts/` and outcomes are contributed
to AkashicRecord for cross-session learning.

---

## 2. TOOL_REGISTRY — 9 tools

| Tool | Permission | Description |
|------|-----------|-------------|
| `Bash` | workspace | Run a shell command. `{cmd, cwd?}`. Risk-classified (LOW/MED/HIGH). |
| `Read` | read-only | Read a file (first 200 lines). `{path}`. |
| `Edit` | workspace | Replace text in a file. `{path, old, new}`. |
| `Write` | workspace | Write / overwrite a file. `{path, content}`. |
| `WebSearch` | network | DuckDuckGo search, returns top-5 snippets. `{query}`. |
| `Ouroboros` | network | Spec-first pipeline (absorbed v0.42.5). `{goal, mode?}` — modes: `auto`/`interview`/`qa`. |
| `OmxSkill` | workspace | Run an OMX skill via `omx` CLI. `{skill, task}` — skills: `ralph`, `team`, `autoresearch`, … |
| `Aider` | workspace | AI pair-programmer with git integration (Aider-AI/aider). `{message, files?}`. Requires `pip install aider-chat`. |
| `SWEAgent` | workspace | Autonomous issue-fixing agent (SWE-agent). `{problem, repo?}`. Requires sweagent installed. |

HIGH-risk tools (e.g. `SWEAgent`, `rm -rf` patterns) are blocked by the default gate and never auto-executed.

---

## 3. Role router — 18 role types

The harness calls `aios_role_router.route(task)` to pick provider before the
first LLM turn. Role is inferred from keyword/regex intent analysis.

| Role | Provider | When routed |
|------|----------|-------------|
| `executor` | codex | Default implementation lane (add/build/fix/…) |
| `debugger` | codex | Debug/build-fix/compile/investigate intent |
| `test-engineer` | codex | "write tests", "add coverage", specs |
| `code-simplifier` | codex | Refactor/cleanup/simplify intent |
| `explore` | codex | "find files", "where is X", local codebase search |
| `ml-engineer` | codex | ML/model/training/PyTorch/dataset tasks |
| `infrastructure` | codex | CI/CD, Docker, Kubernetes, Terraform, deploy |
| `incident-responder` | codex | Alert/outage/postmortem/on-call triage |
| `security-engineer` | codex | CVE triage, exploit analysis, hardening |
| `writer` | claude | Docs/README/guide/changelog deliverables |
| `code-reviewer` | claude | Review/audit/verify, security-domain checks |
| `quality-reviewer` | claude | Pattern review without implementation intent |
| `designer` | claude | UI/UX/layout/component design |
| `researcher` | claude | External research/landscape/best-practice study |
| `dependency-expert` | claude | Package/SDK/library evaluation |
| `data-analyst` | claude | Data interpretation, EDA, reports |
| `architect` | claude | ADR/system design/blueprint/tradeoff analysis |
| `business-analyst` | claude | Requirements, PRDs, market analysis |

Override with `--provider ollama|claude|codex|gemini` when the auto-route is wrong.

---

## 4. Example commands

```bash
# Example 1 — implement a feature (auto-routed to executor/codex)
aios harness "add pagination to the /api/posts endpoint in routes/posts.py"

# Example 2 — dry-run a security review (auto-routed to code-reviewer/claude)
aios harness "review auth.py for injection vulnerabilities" --dry-run --verbose
```

---

## 5. Key flags

| Flag | Default | Description |
|------|---------|-------------|
| `--dry-run` | false | Plan only; no tool execution |
| `--provider` | auto | Force provider: `ollama`, `claude`, `codex`, `gemini` |
| `--tools` | all | Comma-separated allow-list of tools |
| `--max-turns` | 12 | Maximum ReAct loop iterations |
| `--verbose` | false | Print routing decision and tool list |
| `--json` | false | Output full outcome as JSON |

Source: `scripts/aios_harness.py`, `scripts/aios_role_router.py`

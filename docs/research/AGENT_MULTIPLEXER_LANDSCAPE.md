# Agent Multiplexer Landscape (2025-2026)

> Internal AIOS engineering research. Subject: open-source **multi-agent
> orchestration / agent-multiplexer** tools — "tmux, but for AI agents".
> Goal: reverse-engineer their session model, interface, task routing, and
> architecture, and extract patterns for the AIOS `apps/control/` chat
> surface.
>
> Date: 2026-05-17. No secrets. All claims sourced (links at bottom).

---

## 0. The shape of the space

The "agent multiplexer" category exploded in 2025-2026. The common problem:
provider agent CLIs (Claude Code, Codex, Gemini CLI, Aider, Amp, OpenCode,
Cursor CLI...) are each **single-session REPLs**. Running N of them by hand
means N terminals, N branches, N mental contexts. Multiplexers solve this.

Three axes separate the projects:

| Axis | Options seen in the wild |
|---|---|
| **Isolation primitive** | tmux session/pane · git worktree · Docker container · single-process method calls |
| **Interface** | terminal TUI · native desktop app · web app (kanban) · in-CLI split-pane |
| **Coordination** | none (parallel sandboxes) · shared task list + mailbox · explicit delegation graph |

A key finding: **almost none of them do real task classification / model
routing.** They isolate and present; they do *not* decide *which* agent
should handle *what*. The user still routes. The exceptions are the dedicated
LLM-router projects (§11), which are a separate sub-field. This gap is exactly
where AIOS's contribution lies.

---

## 1. tmux — the ancestor

Not an agent tool, but every project below is a reimplementation or wrapper
of its model, so the vocabulary matters.

- **Session/agent model.** `server → session → window → pane`. A pane is a
  pseudo-terminal (PTY) running one process. Sessions are *detachable*: the
  process keeps running after the client disconnects (`detach`/`attach`).
- **Interface.** Pure TUI. Prefix-key (`C-b`) command grammar. Status bar at
  the bottom shows all windows. `tmux ls` lists sessions; `attach -t` joins.
- **IPC.** A unix domain socket per server. Clients talk to the server over
  it; that is also how external scripts (`tmux send-keys`, `tmux capture-pane`)
  drive sessions — this scripting surface is what every agent tool exploits.
- **State.** In-memory in the server process; `tmux-resurrect`-style plugins
  serialize layout to disk.
- **AIOS borrow.** The **detach/reattach** idea = a long-running agent the
  operator can step away from and rejoin. The **`capture-pane`** idea = you
  can read an agent's scrollback as text at any moment without it being
  "your" session — the basis of cheap observation. `apps/control/` should be
  able to *render* an agent transcript without *owning* the agent process.

---

## 2. Claude Squad (`smtg-ai/claude-squad`)

The reference TUI multiplexer. Binary is `cs`.

1. **Session/agent model.** Each agent = **one tmux session + one git
   worktree**. The worktree puts every agent on its own branch so codebases
   never collide. Supports Claude Code, Codex, Gemini, Aider, OpenCode, Amp
   via configurable launch profiles.
2. **Interface.** Single TUI dashboard. Left = session list (`↑/↓/j/k` to
   navigate); right = a tabbed view per session with a **`preview` tab and a
   `diff` tab** (`tab` toggles). `↵/o` attaches into a session to re-prompt;
   `ctrl-q` detaches back to the dashboard. So: *one* screen lists all agents;
   you *opt in* to the noise of any single agent.
3. **Task classification / routing.** None. The human creates a session
   (`n`/`N`) and types the task. Optional `-y/--autoyes` auto-accepts prompts.
4. **Architecture.** Go binary. Spawns/queries tmux via its socket; manages
   worktrees via `git`. Config + session metadata persisted to
   `~/.claude-squad/config.json`. Background tasks tracked there so the TUI
   can reattach after restart.
5. **AIOS borrow.** The **list-pane + per-agent (preview | diff) tabs** layout
   is the single most copyable UI idea: a roster down the side, and for the
   selected agent a compressed "what it's doing now" view *plus* a "what it
   changed" view — not a raw firehose. AIOS `apps/control/chat.html` should
   have exactly this: agent roster + (live transcript | diff/result) tabs.

---

## 3. cmux (`manaflow-ai/cmux`)

Native macOS terminal+browser multiplexer. Explicitly *not* tmux (built on
Ghostty's libghostty core, Swift/AppKit, GPU-accelerated).

1. **Session/agent model.** `workspace → surfaces (tabs) + split panes`. Each
   pane is a plain terminal process — **no enforced worktree/container
   isolation**. Agent *sessions* are restored via `cmux hooks setup`, which
   installs per-agent hooks that write session mappings to `~/.cmuxterm/`.
2. **Interface.** Native app with a **vertical-tab sidebar**. Each tab shows
   git branch, linked PR status/number, working dir, listening ports, and
   **the latest notification text** for that workspace. This is the cleanest
   "N agents at a glance" surface seen: each agent compresses to one line of
   *status*, not output.
3. **Task classification / routing.** None.
4. **Architecture.** Single native process; child terminal processes per
   pane. **Socket API + CLI** (`cmux notify`, `cmux restore-session`, ...)
   make everything scriptable — create workspaces, split panes, send
   keystrokes. Agents signal the UI via **terminal OSC escape sequences
   (OSC 9 / 99 / 777)** for notifications. State = versioned snapshots under
   `~/Library/Application Support/cmux/`.
5. **AIOS borrow.** Two strong ideas. (a) The **one-line status digest per
   agent** (branch + state + last-notification) — AIOS should compute a
   compact status string per agent rather than streaming raw output to the
   roster. (b) **OSC-style out-of-band notifications**: agents emit
   structured "I need attention / I'm done / I'm blocked" signals on a side
   channel, decoupled from their transcript. AIOS already has the ledger and
   monitors — model agent→control notifications as discrete events, not chat
   lines.

Related: **wmux** (Windows port, same socket protocol), **cmux-agent-mcp**
(exposes cmux as an MCP server so any CLI agent can drive the multiplexer
remotely).

---

## 4. claude-swarm / SwarmSDK (`parruda/swarm`)

The most architecturally interesting for AIOS, because it does *coordination*,
not just isolation.

1. **Session/agent model.** A team of named agents, each with a **role**
   ("Backend developer managing APIs"), a **model** (Claude/OpenAI/Gemini via
   RubyLLM), a **tool allowlist**, and a **`delegates_to`** list. v1 ran N
   real Claude Code processes talking over MCP; **SwarmSDK (v2) collapsed
   this into a single Ruby process** using direct method calls.
2. **Interface.** Library / CLI (`SwarmCLI`), not a TUI. Orchestration is
   declared in YAML, not clicked.
3. **Task classification / routing.** **Explicit, static delegation graph.**
   `lead_reviewer → delegates_to: [security_expert, performance_analyst]`.
   Also **node workflows** — multi-stage pipelines with `depends_on`
   dependencies. The lead agent decides at runtime which subordinate handles
   which aspect, but the *set of routes is author-defined*.
4. **Architecture.** Single-process (v2) — no IPC overhead, unified context.
   12-event **hooks system** (pre/post tool, user message, response) with 6
   action types. Built-in **cost tracking**. Optional **SwarmMemory** =
   persistent knowledge store with FAISS semantic search.
5. **AIOS borrow.** The **role + model + tool-allowlist + delegates_to** tuple
   is essentially an AIOS capability card with routing edges. AIOS's 5-OS
   personas (Wrapper/Retriever/Router/Philosophy/Sovereign) map naturally onto
   this: declare each "agent" as a role with a model and a delegation edge
   set. And **hooks + cost tracking per agent** is directly the kind of
   enforcement/observability ASC-0184 wants. SwarmMemory ≈ MemoryOS.

Adjacent: **ruflo** (ex-Claude-Flow) — heavyweight swarm platform with
self-learning memory and federated comms; **ccswarm** (`nwiizo/ccswarm`) —
Rust, git-worktree-isolated specialized agents; **affaan-m/claude-swarm** —
task-decomposition with a rich terminal UI; Anthropic-native subagents.

---

## 5. Claude Code Agent Teams (Anthropic, native, experimental)

The vendor's own answer, gated behind `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`
(v2.1.32+). Most relevant primitive design for AIOS.

1. **Session/agent model.** One **team lead** (the session you started) +ヾN
   **teammates**, each a *full independent Claude Code instance with its own
   context window*. Teammates do NOT inherit the lead's conversation history —
   only project context (CLAUDE.md, MCP, skills) + a spawn prompt. Unlike
   subagents, you can talk to a teammate *directly*, not only via the lead.
2. **Interface.** Two display modes. **In-process**: all teammates in the
   main terminal, `Shift+Down` cycles through them, type to message the
   selected one, `Ctrl+T` toggles the task list. **Split-panes**: one tmux/
   iTerm2 pane per teammate, click to interact. `"auto"` picks split-panes if
   already inside tmux.
3. **Task classification / routing.** A **shared task list** (states:
   pending / in-progress / completed; tasks can `depend_on` other tasks).
   Lead can assign tasks explicitly, *or* teammates **self-claim** the next
   unblocked task. **File locking** prevents two teammates claiming the same
   task. The lead breaks the user's request into tasks — but this is LLM
   judgment in the lead, not a classifier.
4. **Architecture.** Components: **team lead**, **teammates**, **shared task
   list**, **mailbox** (messaging). Teammate messages auto-deliver to the
   lead (no polling); idle teammates auto-notify. State on disk:
   team config `~/.claude/teams/{name}/config.json` (holds session IDs +
   tmux pane IDs as *runtime* state — do not hand-edit), task list
   `~/.claude/tasks/{name}/`. **Hooks** `TeammateIdle` / `TaskCreated` /
   `TaskCompleted` let you enforce gates (exit code 2 = block + feedback).
   Limits: one team per lead, no nested teams, lead is fixed for life,
   no `/resume` of in-process teammates.
5. **AIOS borrow.** This is the closest existing thing to what AIOS wants and
   the borrow list is long:
   - **Shared task list with `depend_on` + self-claim + file-lock** =
     directly the AIOS contract/dispatch lifecycle, validated at small scale.
   - **Mailbox with auto-delivery + idle auto-notify** = agents push events;
     the control plane never polls. AIOS monitors should follow this.
   - **Hooks that can *block* a task completion** (`TaskCompleted` exit 2) =
     the deterministic-enforcement model of ASC-0184.
   - **Teammate = role definition (subagent type) + model + tool allowlist**,
     reusable. AIOS persona axis should be expressible the same way.
   - **`Shift+Down` to cycle agents in one terminal** = a zero-window-management
     way to multiplex; AIOS chat UI can do the same with a roster + hotkey.

---

## 6. Crystal → Nimbalyst (`stravu/crystal`)

Multi-session Claude Code/Codex **desktop GUI**. Crystal deprecated Feb 2026,
succeeded by **Nimbalyst**.

1. **Session/agent model.** Each session = a **git worktree** auto-created/
   managed by the app, against a single project dir; multiple concurrent
   sessions per project, each on its own branch.
2. **Interface.** Electron desktop app. Designed for **running the *same*
   task several ways and comparing** ("test, compare approaches"). Nimbalyst
   adds a **kanban** board + **inline AI diffs**.
3. **Task classification / routing.** None — human-driven.
4. **Architecture.** Electron (Node main + Chromium renderer). Spawns Claude
   Code/Codex as child processes against worktrees.
5. **AIOS borrow.** The **"run one prompt N ways, compare diffs side by side"**
   pattern — useful for an AIOS "explore/inversion" mode (cf. ASC-0186):
   fan a single goal to multiple personas, then present a *comparison*, not a
   merge.

---

## 7. Conductor (`conductor.build`)

Mac app, free, Apple-Silicon only.

1. **Session/agent model.** Each agent gets an isolated **git worktree** copy
   of the codebase ("threads"). Runs Claude Code, Codex, others in parallel.
2. **Interface.** Native Mac app. Key idea: a **diff-first review model** —
   "instead of scanning entire file trees, you review only what changed";
   each thread presents its work as a **clean diff**, merged from one place.
3. **Routing.** None.
4. **Architecture.** Native app over `git worktree`; reuses your existing
   Claude Code auth (API key / Pro / Max).
5. **AIOS borrow.** **Diff-first as the default review surface.** When an
   AIOS agent finishes, the operator should land on *the diff*, not a wall of
   reasoning text. Output of work = the change, summarized.

---

## 8. vibe-kanban (`BloopAI/vibe-kanban`)

Web-based kanban orchestrator. Apache-2.0, community-maintained after Bloop's
2026 shutdown.

1. **Session/agent model.** Tasks modeled as cards / GitHub issues. Each
   workspace = an agent + a **git worktree branch + a terminal + a dev
   server**. 10+ pluggable agents (Claude Code, Codex, Gemini, Copilot, Amp,
   Cursor, OpenCode, Droid, CCR, Qwen).
2. **Interface.** **Web app, kanban board** with To Do / In Progress / Review
   / Done columns. Workspaces panel, built-in browser with devtools/device
   emulation, **inline diff review**. Cards can be created via MCP. Workflow
   slogan: "describe the work, review the diff, ship it."
3. **Task classification / routing.** No algorithmic routing; the *kanban
   column* is the state machine, and MCP-driven card creation lets an agent
   *decompose* work into more cards.
4. **Architecture.** **Rust backend + TypeScript/Node frontend**, PostgreSQL
   state (sqlx). `npx vibe-kanban` single-command launch. `DISABLE_WORKTREE_CLEANUP`
   controls orphan workspace GC.
5. **AIOS borrow.** **Kanban columns as the multi-agent state machine** —
   To Do / In Progress / **Review** / Done maps almost 1:1 onto AIOS contract
   status (proposed / accepted / *review* / closed). The **Review column** is
   the human gate = AIOS's draft-first invariant rendered as UI. And
   **MCP-card-creation = an agent decomposing a goal into sub-contracts** —
   a concrete pattern for AIOS task splitting.

Adjacent web/kanban tools: **automagik-forge** (multi-agent kanban + MCP),
**amux** (`mixpeek/amux` — browser/phone control plane, kanban + notes + CRM
+ agent-to-agent orchestration).

---

## 9. uzi (`devflowinc/uzi`)

CLI for running *large numbers* of agents in parallel. Go binary,
`go install`.

1. **Session/agent model.** Per agent: **git worktree + tmux session + its
   own dev server on an allocated port**. Built for *many* agents at once.
2. **Interface.** CLI. `uzi.yaml` configures `devCommand` + `portRange`.
   Real-time monitoring of agent status + code changes. **`uzi checkpoint`**
   merges a chosen agent's result into main with one command.
3. **Routing.** None — the model is "run the *same* task on many agents,
   then pick the winner."
4. **Architecture.** Go; Worktree Manager + tmux session manager + port
   allocator. Auto-handles agent confirmation prompts.
5. **AIOS borrow.** **Automatic port allocation per agent** matters if AIOS
   ever runs agents that each spin a dev server. More important: the
   **checkpoint = "promote one branch, discard the rest"** primitive — a
   clean disposal model for AIOS explore-mode branches.

Adjacent: **workmux** (`raine/workmux` — worktrees + tmux windows), **dmux**.

---

## 10. container-use (`dagger/container-use`) & Sculptor (`imbue-ai/sculptor`)

The **container-isolation** branch of the family. Stronger sandbox than
worktrees (a rogue agent can't touch your machine).

**container-use** — an **MCP server** that gives each agent its own
Docker-container dev environment, *each backed by a git branch* (container +
branch = a versioned, persistent workspace). Plugs into any MCP-compatible
agent (Claude Code, Cursor). Dagger under the hood; needs Docker + Git.
Real-time visibility + simple intervention points.

**Sculptor** (Imbue) — Mac desktop app; each parallel agent in its **own
Docker container** ("no git-worktree hassle, no dependency reinstalls per
agent"). **Pairing Mode**: one click syncs an agent's container work into
your local repo + git state so you can take over in your IDE. Supports
Claude Code + Codex.

**AIOS borrow.** (a) **container-use proves the isolation primitive can be an
MCP server** — AIOS could expose "give me an isolated workspace" as an MCP
tool that any persona calls, rather than baking isolation into the control
app. (b) **Sculptor's Pairing Mode** = a clean "promote sandbox → real
workspace, hand control to human" transition; AIOS needs an equivalent
operator-takeover gesture. (c) container+branch = sandbox *with* provenance,
which fits the append-only-audit invariant.

---

## 11. The routing sub-field (LLM routers)

Since §1-10 mostly *don't* route, here's the field that does — relevant to
the founder's "task classification is rough" complaint.

- **RouteLLM** (ICLR 2025): a **matrix-factorization router** + a cheap/
  strong model pair. Hit 95% of GPT-4 quality with **26% strong-model calls**;
  with LLM-judge data augmentation, 95% quality at **14%** strong calls.
- **LLMRouter** (`ulab-uiuc/LLMRouter`): library, 16+ routing models in 4
  families — single-round, multi-round, agentic, personalized routers.
- **NVIDIA llm-router**: classifier-based pre-routing to the best model.
- **Routing paradigms that matter for AIOS:**
  - **Pre-generation routing** — classify the query *before* dispatch
    (keyword match, embedding similarity, or a small classifier like
    DistilBERT) → pick model/agent.
  - **Post-generation routing** — answer with a cheap model first, run a
    quality check, **escalate to a stronger model only if it fails a
    threshold.** Cheap, and degrades gracefully.
  - **Service-registry pattern** — a matrix of available models/backends with
    cost, load, and health; an orchestrator selects the (model, backend)
    pair and handles cold starts.

**AIOS borrow.** This is the missing organ. AIOS's `aios_chat_router.py` +
`apps/control/` should adopt **two-tier routing**: (1) a fast pre-router
(small classifier or even rules) sorts a chat turn into a coarse class —
trivial/chat vs. retrieval vs. multi-step build vs. needs-divergence — and
maps the class to a persona/model; (2) a **post-generation escalation** check
catches misroutes — if the cheap path's answer fails a confidence/quality
gate, re-run on a stronger persona. RouteLLM's numbers say most turns can be
served cheap if the gate is good. The **service registry = CapabilityOS**:
it already is the matrix of routes with cost/health — wire the router to
*query CapabilityOS* instead of hardcoding.

---

## 12. tmuxai (`alvinunreal/tmuxai`)

Different category — not a multiplexer but worth one note. A **single
AI assistant that observes a tmux window**: a chat pane + an exec pane; it
*reads all panes' visible content* to stay context-aware, and a "watch mode"
proactively suggests. **Borrow:** the **observe-by-reading-the-screen** model
is a cheap way for an AIOS supervisor to understand agent state without
structured IPC — capture transcript, summarize, decide. Pairs with §1's
`capture-pane` point.

---

## 13. Synthesis — what AIOS `apps/control/` should copy

**A. Presenting multi-agent output without overwhelming the user**

1. **Roster + detail-tabs, not a firehose** (Claude Squad). Side roster of
   all agents; selecting one shows `(live transcript | diff/result)` tabs.
   The user opts into noise.
2. **One-line status digest per agent** (cmux). Compute a compact string —
   `branch · state · last-event` — for the roster. Raw output stays behind a
   click.
3. **Out-of-band event channel** (cmux OSC, Agent-Teams mailbox). Agents emit
   discrete `done / blocked / needs-input` events on a side channel, separate
   from chat text. Control plane reacts to events; never polls. AIOS monitors
   + ledger already fit this.
4. **Diff-first review** (Conductor, vibe-kanban, Crystal). When work finishes,
   land the operator on *the change*, summarized — not the reasoning trace.
5. **Kanban columns as the state machine** (vibe-kanban). To Do / In Progress
   / **Review** / Done ≈ AIOS contract lifecycle; the Review column *is* the
   draft-first human gate.
6. **Aggregate, dedup, flag conflicts** (multi-agent review practice). When
   several personas weigh in, remove duplicates, highlight anything flagged
   by multiple agents, and surface contradictions explicitly.

**B. Task classification / routing**

7. **Two-tier routing** (RouteLLM / LLMRouter). Fast pre-router classifies
   the turn into a coarse class → persona/model; post-generation quality gate
   escalates misroutes to a stronger persona. Most turns served cheap.
8. **Route against a live registry, not hardcoded** (service-registry
   pattern). The router queries **CapabilityOS** (the cost/health/route
   matrix) per turn — don't bake routes into `aios_chat_router.py`.
9. **Shared task list with `depend_on` + self-claim + file-lock**
   (Agent Teams). Decomposed work items in one list; agents claim the next
   unblocked one; locking prevents double-claim. = AIOS dispatch, validated.
10. **Roles as (model + tool-allowlist + delegates_to)** (SwarmSDK,
    Agent-Teams subagent types). Express each AIOS persona this way; routing
    edges are explicit and reusable.
11. **Decomposition as card/contract creation via MCP** (vibe-kanban). An
    agent that needs to split work *creates sub-contracts*, rather than
    spawning hidden sub-processes — keeps provenance in the audit trail.
12. **Blocking hooks on task lifecycle** (Agent-Teams `TaskCompleted` exit 2).
    Deterministic gates on create/complete = the enforcement model AIOS
    ASC-0184 already wants — apply it to chat-routed tasks too.

**Isolation note.** For AIOS's own agents, the worktree model (Claude Squad /
Conductor / uzi) is the cheap default; the container model (Sculptor /
container-use) is the safe upgrade and, per container-use, can be exposed
*as an MCP tool* so personas request isolation rather than the control app
managing it.

---

## Sources

- Claude Squad — https://github.com/smtg-ai/claude-squad · https://smtg-ai.github.io/claude-squad/
- cmux — https://github.com/manaflow-ai/cmux · https://cmux.com/
- wmux — https://github.com/amirlehmam/wmux
- cmux-agent-mcp — https://github.com/multiagentcognition/cmux-agent-mcp
- amux — https://github.com/mixpeek/amux
- claude-swarm / SwarmSDK — https://github.com/parruda/swarm
- ccswarm — https://github.com/nwiizo/ccswarm
- affaan-m/claude-swarm — https://github.com/affaan-m/claude-swarm
- ruflo — https://github.com/ruvnet/ruflo
- Claude Code Agent Teams — https://code.claude.com/docs/en/agent-teams
- Crystal / Nimbalyst — https://github.com/stravu/crystal · https://nimbalyst.com/crystal/
- Conductor — https://www.conductor.build/ · https://docs.conductor.build/
- vibe-kanban — https://github.com/BloopAI/vibe-kanban · https://vibekanban.com/
- automagik-forge — https://github.com/namastexlabs/automagik-forge
- uzi — https://github.com/devflowinc/uzi
- workmux — https://github.com/raine/workmux
- container-use — https://github.com/dagger/container-use · https://dagger.io/blog/agent-container-use/
- Sculptor — https://github.com/imbue-ai/sculptor · https://imbue.com/sculptor/
- tmuxai — https://github.com/alvinunreal/tmuxai · https://tmuxai.dev/
- LLMRouter — https://github.com/ulab-uiuc/LLMRouter
- NVIDIA llm-router — https://github.com/NVIDIA-AI-Blueprints/llm-router
- RouteLLM (ICLR 2025) — referenced via https://www.burnwise.io/blog/llm-model-routing-guide
- awesome-agent-orchestrators — https://github.com/andyrewlee/awesome-agent-orchestrators

(function () {
  const snapshot = window.AIOS_CONTROL_SNAPSHOT;
  let liveEventCount = 0;

  function qs(id) {
    return document.getElementById(id);
  }

  function text(value, fallback = "unknown") {
    return value === undefined || value === null || value === "" ? fallback : String(value);
  }

  function number(value) {
    return new Intl.NumberFormat().format(Number(value || 0));
  }

  function el(tag, className, content) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (content !== undefined) node.textContent = content;
    return node;
  }

  function pill(label, status) {
    const node = el("span", "pill");
    const dot = el("i", `dot ${String(status || "").toLowerCase()}`);
    node.append(dot, document.createTextNode(label));
    return node;
  }

  function renderStatus(data) {
    const monitor = data.monitor || {};
    const evolution = (data.goals || {}).evolution || {};
    const round = data.round_controller || {};
    const strip = qs("status-strip");
    strip.replaceChildren(
      pill(`Monitor ${text(monitor.health)}`, monitor.health),
      pill(`AIOS ${text((data.installation || {}).status, "unknown")}`, (data.installation || {}).status),
      pill(text(evolution.readiness, "readiness unknown"), "pass"),
      pill(`Contracts ${text((data.contracts || {}).total, 0)}`, "active"),
      pill(`Dispatches ${text((data.dispatches || {}).total, 0)}`, "released"),
      pill(`Round ${text(round.status || round.latest_status, "observing")}`, "clear")
    );
  }

  function renderGoal(data) {
    const active = (data.goals || {}).active || {};
    const evolution = (data.goals || {}).evolution || {};
    const activeText = active.slug || "AIOS control plane";
    qs("goal-title").textContent = active.slug ? `${activeText} / ${text(evolution.recommendation, "no recommendation")}` : activeText;
    if (qs("side-active-goal")) qs("side-active-goal").textContent = activeText;
    if (qs("side-active-status")) qs("side-active-status").textContent = text(evolution.readiness, "On track");
  }

  function renderLoopMap(data) {
    const inputs = data.aios_inputs || {};
    const nodes = [
      ["Goal", text(((data.goals || {}).evolution || {}).recommendation, "waiting for recommendation")],
      ["MemoryOS", (inputs.memory_traces || []).slice(0, 2).join(", ") || "no trace in latest contracts"],
      ["CapabilityOS", (inputs.capability_routes || []).slice(0, 2).join(", ") || "no route in latest contracts"],
      ["Hive Mind", (inputs.hive_runs || []).slice(0, 2).join(", ") || "no run in latest contracts"],
      ["Learn", ((data.next_actions || [])[0] || {}).action || "continue observing"],
    ];
    qs("loop-map").replaceChildren(
      ...nodes.map(([title, body]) => {
        const node = el("div", "loop-node");
        node.append(el("b", "", title), el("span", "", body));
        return node;
      })
    );
  }

  function renderExecutionLens(data) {
    const grid = qs("execution-lens-grid");
    const status = qs("execution-lens-status");
    if (!grid || !status) return;

    const invocations = ((data.invocations || {}).latest || []);
    const latestInvocation = invocations[0] || {};
    const latestDispatch = (((data.dispatches || {}).latest || []))[0] || {};
    const inputs = data.aios_inputs || {};
    const hiveRuns = (inputs.hive_runs || []).slice(0, 8);
    const nextAction = text(latestInvocation.next_action || latestDispatch.reason || "continue observing");
    const statusValue = text(latestInvocation.overall_status || latestDispatch.status || "idle");
    const latestRun = text(latestInvocation.invocation_id || latestDispatch.dispatch_id || latestDispatch.contract_id || "none");
    const latestGoal = text(latestInvocation.goal || latestDispatch.goal || "no goal captured");
    const nextActionBadge = el("span", "execution-detail", nextAction);

    status.textContent = statusValue === "accepted" || statusValue === "completed" ? "Execution complete" : "Execution watching";

    const stats = [
      ["Execution state", statusValue, "hive status from latest invocation or dispatch"],
      ["Latest run", latestRun, "latest runnable unit captured by control plane"],
      ["Latest goal", latestGoal, "goal currently being routed"],
      ["Next operator cue", nextAction, "AIOS next gate action"],
      ["Hive traces", hiveRuns.length ? hiveRuns.join(" · ") : "no recent run ID", "from contracts and invocation artifacts"],
      ["Dispatches", `${text((data.dispatches || {}).total, 0)}`, "records in .aios/state/dispatches.jsonl"],
      ["Artifacts", `${((data.invocations || {}).latest || []).length}`, "recent invocation envelopes available"],
    ];

    grid.replaceChildren(
      ...stats.map(([title, value, detail]) => {
        const card = el("article", "execution-lens-card");
        card.append(
          el("strong", "execution-lens-card-title", title),
          el("span", "execution-lens-card-value", value),
          el("small", "execution-lens-card-detail", detail)
        );
        if (title === "Next operator cue") {
          card.append(nextActionBadge);
        }
        return card;
      })
    );
  }

  function renderContracts(data) {
    const contracts = data.contracts || {};
    qs("contract-total").textContent = `${contracts.total || 0} total`;
    qs("contract-flow").replaceChildren(
      ...(contracts.latest || []).slice(0, 8).map((row) => {
        const item = el("div", "flow-row");
        item.append(
          pill(text(row.id), row.status),
          el("strong", "", text(row.slug)),
          el("span", "", text(row.status))
        );
        return item;
      })
    );
  }

  function renderDispatches(data) {
    const dispatches = data.dispatches || {};
    const counts = dispatches.counts || {};
    const total = Math.max(1, Object.values(counts).reduce((sum, value) => sum + Number(value || 0), 0));
    qs("dispatch-total").textContent = `${dispatches.total || 0} tracked`;
    qs("dispatch-meters").replaceChildren(
      ...Object.entries(counts)
        .sort((a, b) => b[1] - a[1])
        .map(([status, count]) => {
          const row = el("div", "meter");
          const bar = el("span", "bar");
          const fill = el("i");
          fill.style.width = `${Math.max(6, (Number(count) / total) * 100)}%`;
          bar.append(fill);
          row.append(el("strong", "", status), bar, el("span", "", String(count)));
          return row;
        })
    );
    qs("snapshot-time").textContent = text(data.generated_at);
    qs("dispatch-table").replaceChildren(
      ...(dispatches.latest || []).slice(0, 10).map((row) => {
        const item = el("div", "dispatch-row");
        item.append(
          el("strong", "", text(row.dispatch_id)),
          el("span", "", text(row.goal || row.contract_id)),
          pill(text(row.status), row.status),
          el("span", "", `sent ${row.sent.length} / collected ${row.collected.length}`)
        );
        return item;
      })
    );
  }

  function renderRepos(data) {
    const repos = ((data.repos || {}).items || []);
    qs("repo-count").textContent = `${repos.length} repos`;
    qs("repo-list").replaceChildren(
      ...repos.map((repo) => {
        const row = el("div", "repo-row");
        row.append(
          el("strong", "", repo.repo),
          pill(repo.dirty ? "dirty" : "clean", repo.dirty ? "held" : "clear"),
          el("span", "small", `inbox ${repo.inbox_count} · outbox ${repo.outbox_count} · goals ${repo.goal_count} · routes ${repo.route_count}`)
        );
        return row;
      })
    );
  }

  function renderRoutes(data) {
    const inputs = data.aios_inputs || {};
    const lanes = [
      ["Memory traces", inputs.memory_traces || []],
      ["Capability routes", inputs.capability_routes || []],
      ["Hive runs", inputs.hive_runs || []],
    ];
    qs("input-count").textContent = `${lanes.reduce((sum, lane) => sum + lane[1].length, 0)} refs`;
    qs("route-lanes").replaceChildren(
      ...lanes.map(([title, items]) => {
        const row = el("div", "route-row");
        row.append(el("strong", "", title), el("span", "", items.length ? items.join(" · ") : "none"));
        return row;
      })
    );
  }

  function renderStops(data) {
    const stops = ((data.stop_lanes || {}).items || []).slice(0, 8);
    qs("stop-count").textContent = `${stops.length} lanes`;
    qs("stop-list").replaceChildren(
      ...stops.map((stop) => {
        const row = el("div", "stop-row");
        row.append(el("strong", "", stop.name), el("span", "", stop.contracts.join(", ")));
        return row;
      })
    );
  }

  function renderSimple(data) {
    const monitor = data.monitor || {};
    const health = monitor.health === "clear" ? "All systems are healthy." : "Some work needs operator attention.";
    const counts = (data.contracts || {}).counts || {};
    const waiting = Number(counts.proposed || 0) + Number(counts.accepted || 0) + Number(((data.memory_draft_queue || {}).total) || 0);
    const latest = ((data.dispatches || {}).latest || [])[0];
    qs("simple-health").textContent = health;
    qs("simple-activity").textContent = latest
      ? `Latest work is ${text(latest.status, "moving")} and waiting for the next check.`
      : "No recent work has been recorded.";
    qs("simple-decisions").textContent = waiting
      ? `${waiting} items may need review before they can finish.`
      : "There are no review items in the current snapshot.";
  }

  function renderInstallation(data) {
    const install = data.installation || {};
    const status = qs("runtime-status");
    if (status) status.textContent = text(install.status, "unknown");
    const grid = qs("runtime-grid");
    if (!grid) return;
    const command = install.command || {};
    const service = install.service || {};
    const control = install.control_center || {};
    const loop = install.loop || {};
    const chair = install.gate_chair || {};
    const cards = [
      {
        title: "Command",
        state: command.launcher_installed ? "installed" : command.available ? "available" : "missing",
        value: command.launcher_installed ? "aios" : "aios install",
        detail: command.path || "global command not installed",
      },
      {
        title: "Background",
        state: service.active ? "running" : service.installed ? "installed" : "missing",
        value: service.active ? "running" : service.installed ? "installed" : "not installed",
        detail: service.enabled ? `service ${service.enabled}` : "user service",
      },
      {
        title: "Control Center",
        state: control.running ? "running" : "held",
        value: control.running ? "open" : "closed",
        detail: control.url || "http://127.0.0.1:8765/",
      },
      {
        title: "Loop",
        state: loop.running ? "running" : "held",
        value: loop.running ? "awake" : "stopped",
        detail: loop.latest_next || loop.latest_status || "round controller",
      },
      {
        title: "Gate Chair",
        state: chair.enabled ? chair.state || "internal" : "held",
        value: chair.enabled ? text(chair.mode, "internal") : "disabled",
        detail: (chair.latest_turn && chair.latest_turn.status) ? `${chair.latest_turn.status} · ${text(chair.detail)}` : text(chair.detail, "gate pack required"),
      },
    ];
    const probeStatus = el("small", "runtime-probe-status");
    const probeButton = el("button", "runtime-probe-button", "Test Gate Chair");
    probeButton.type = "button";
    probeButton.addEventListener("click", async () => {
      probeStatus.textContent = "Testing";
      probeButton.disabled = true;
      try {
        const response = await fetch("/api/gate_chair_probe", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ conversation_id: "gate-chair-probe" }),
        });
        const payload = await response.json();
        if (!response.ok || !payload.ok) {
          probeStatus.textContent = payload.reason || "Probe failed";
          return;
        }
        const status = payload.gate_chair_status || {};
        probeStatus.textContent = `${status.status || "unknown"} · ${status.mode || "unknown"}`;
      } catch (_error) {
        probeStatus.textContent = "Probe API unavailable";
      } finally {
        probeButton.disabled = false;
      }
    });
    const evalStatus = el("small", "runtime-probe-status");
    const evalButton = el("button", "runtime-probe-button", "Eval Chair");
    const evalReport = el("div", "runtime-eval-report");
    const runtimeStatus = el("small", "runtime-probe-status");
    async function setChairRuntime(mode) {
      runtimeStatus.textContent = "Saving";
      try {
        const response = await fetch("/api/gate_chair_runtime", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            confirm: true,
            mode,
            model: mode === "ollama" ? "qwen2.5:7b" : mode === "claude" ? "claude-opus-4-6" : "",
          }),
        });
        const payload = await response.json();
        if (!response.ok || !payload.ok) {
          runtimeStatus.textContent = payload.reason || "Runtime save failed";
          return;
        }
        const config = payload.runtime_config || {};
        const fragments = [`${config.mode || mode} ${config.status === "candidate" ? "candidate saved" : "saved"}`];
        if (config.command_available === false) {
          fragments.push("command missing");
        }
        if (config.fallback_expected) {
          fragments.push("internal fallback expected");
        }
        if (payload.activation_required) {
          fragments.push("eval before activation");
        }
        runtimeStatus.textContent = fragments.join(" · ");
      } catch (_error) {
        runtimeStatus.textContent = "Runtime API unavailable";
      }
    }
    const internalButton = el("button", "runtime-probe-button", "Use Internal");
    internalButton.type = "button";
    internalButton.addEventListener("click", () => setChairRuntime("internal_evidence_synthesizer"));
    const ollamaButton = el("button", "runtime-probe-button", "Try Ollama");
    ollamaButton.type = "button";
    ollamaButton.addEventListener("click", () => setChairRuntime("ollama"));
    const claudeButton = el("button", "runtime-probe-button", "Try Claude");
    claudeButton.type = "button";
    claudeButton.addEventListener("click", () => setChairRuntime("claude"));
    const codexButton = el("button", "runtime-probe-button", "Try Codex");
    codexButton.type = "button";
    codexButton.addEventListener("click", () => setChairRuntime("codex"));
    const geminiButton = el("button", "runtime-probe-button", "Try Gemini");
    geminiButton.type = "button";
    geminiButton.addEventListener("click", () => setChairRuntime("gemini"));
    evalButton.type = "button";
    evalButton.addEventListener("click", async () => {
      evalStatus.textContent = "Evaluating";
      evalReport.replaceChildren();
      evalButton.disabled = true;
      try {
        const response = await fetch("/api/gate_chair_eval", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ mode: "both" }),
        });
        const payload = await response.json();
        if (!response.ok || !payload.ok) {
          evalStatus.textContent = payload.reason || "Eval failed";
          return;
        }
        const scores = payload.scores || {};
        const readiness = payload.promotion_ready ? "promotion ready" : "not ready";
        evalStatus.textContent = `${readiness} · ${payload.verdict || "observed"} · internal ${text(scores.internal, "-")} / current ${text(scores.current, "-")}`;
        if (payload.readiness_reason) {
          evalReport.append(el("small", "runtime-eval-reason", payload.readiness_reason));
        }
        const report = artifactPreviewControl(payload.report_path, "runtime-eval-open");
        if (report) evalReport.append(report);
        if (payload.promotion_ready && payload.report_path) {
          const promoteButton = el("button", "runtime-probe-button", "Promote Chair");
          promoteButton.type = "button";
          promoteButton.addEventListener("click", async () => {
            evalStatus.textContent = "Promoting";
            promoteButton.disabled = true;
            try {
              const promoteResponse = await fetch("/api/gate_chair_promote", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  confirm: true,
                  report_path: payload.report_path,
                }),
              });
              const promoted = await promoteResponse.json();
              if (!promoteResponse.ok || !promoted.ok) {
                evalStatus.textContent = promoted.reason || "Promotion failed";
                return;
              }
              const config = promoted.runtime_config || {};
              evalStatus.textContent = `${config.mode || "Chair"} promoted`;
            } catch (_error) {
              evalStatus.textContent = "Promotion API unavailable";
            } finally {
              promoteButton.disabled = false;
            }
          });
          evalReport.append(promoteButton);
        }
      } catch (_error) {
        evalStatus.textContent = "Eval API unavailable";
      } finally {
        evalButton.disabled = false;
      }
    });
    const commandRow = el("div", "runtime-command-row");
    (install.commands || ["aios install", "aios open", "aios status --json", "aios stop"]).forEach((cmd) => {
      commandRow.append(el("code", "", cmd));
    });
    commandRow.append(probeButton, probeStatus, evalButton, evalStatus, internalButton, ollamaButton, claudeButton, codexButton, geminiButton, runtimeStatus, evalReport);
    grid.replaceChildren(
      ...cards.map((card) => {
        const item = el("article", `runtime-card ${card.state}`);
        item.append(
          pill(card.title, card.state),
          el("strong", "", card.value),
          el("span", "", card.detail)
        );
        return item;
      }),
      commandRow
    );
  }

  function renderCompletion(data) {
    const c = data.completion || {};
    const crits = c.criteria || [];
    const verdict = qs("completion-verdict");
    if (verdict) verdict.textContent = text(c.verdict, "Checking AIOS completion");
    const status = qs("completion-status");
    if (status) {
      status.textContent = text(c.criteria_met, "—");
      status.className = "live-status";
    }
    const grid = qs("completion-grid");
    if (!grid) return;
    if (!crits.length) {
      grid.replaceChildren(el("article", "runtime-card", "completion check unavailable"));
      return;
    }
    grid.replaceChildren(
      ...crits.map((cr) => {
        const card = el("article", "runtime-card");
        const state = cr.met ? "running" : (cr.partial ? "held" : "missing");
        card.append(
          pill(cr.met ? "met" : (cr.partial ? "partial" : "open"), state),
          el("strong", "", text(cr.criterion)),
          el("span", "", text(cr.evidence, ""))
        );
        return card;
      })
    );
  }

  function renderWorkbench(data) {
    const wb = data.workbench || {};
    const repos = wb.repos || [];
    const status = qs("workbench-status");
    if (status) {
      status.textContent = repos.length
        ? `${repos.length} repo${repos.length === 1 ? "" : "s"}`
        : "No repos";
    }
    const grid = qs("workbench-grid");
    if (!grid) return;
    if (!repos.length) {
      const empty = el("article", "runtime-card");
      empty.append(
        pill("Workbench", "held"),
        el("strong", "", "No product repos registered"),
        el("span", "", "Run: aios init")
      );
      grid.replaceChildren(empty);
      return;
    }
    grid.replaceChildren(
      ...repos.slice(0, 8).map((repo) => {
        const card = el("article", "runtime-card");
        const caps = repo.observed_capabilities || [];
        card.append(
          pill(repo.repo, repo.sprints_absorbed > 0 ? "running" : "held"),
          el("strong", "", `${repo.sprints_absorbed} sprint${repo.sprints_absorbed === 1 ? "" : "s"} absorbed`),
          el("span", "", caps.length
            ? `${caps.length} observed capabilit${caps.length === 1 ? "y" : "ies"}: ${caps.map((c) => c.id).join(", ")}`
            : "no capabilities observed yet")
        );
        if (repo.sprint_ids && repo.sprint_ids.length) {
          card.append(el("small", "", repo.sprint_ids.join(", ")));
        }
        return card;
      })
    );
  }

  function renderPromotionQueue(data) {
    const promotions = data.promotions || {};
    const items = promotions.items || [];
    const status = qs("promotion-status");
    if (status) status.textContent = `${promotions.total || 0} item${Number(promotions.total || 0) === 1 ? "" : "s"}`;
    const grid = qs("promotion-queue-grid");
    if (!grid) return;
    if (!items.length) {
      const empty = el("article", "promotion-queue-card empty");
      empty.append(pill("Queue", "held"), el("strong", "", "No reviewed promotions"), el("span", "", "Create one from a reviewed session."));
      grid.replaceChildren(empty);
      return;
    }
    grid.replaceChildren(
      ...items.slice(0, 6).map((item) => {
        const card = el("article", "promotion-queue-card");
        const rows = [
          ["envelope", item.session_envelope_ref],
          ["seed", item.contract_seed],
          ["dispatch", item.dispatch_preview],
          ["next", item.next_action],
        ].filter((row) => row[1]);
        const rowList = el("div", "promotion-queue-rows");
        rowList.append(
          ...rows.map(([label, value]) => {
            const row = el("div", "promotion-queue-row");
            row.append(el("strong", "", label), el("span", "", value));
            return row;
          })
        );
        card.append(
          pill(text(item.status, "promotion"), item.status),
          el("strong", "", text(item.goal || item.promotion_id, "promotion")),
          el("small", "", text(item.created_at, "created")),
          rowList
        );
        return card;
      })
    );
  }

  async function requestMemoryDraftReview(item, status, button) {
    button.disabled = true;
    status.textContent = "Sending to MemoryOS";
    try {
      const response = await fetch("/api/memory_draft_review", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source_artifact: item.source_artifact,
          draft_id: item.draft_id,
          confirm: true,
        }),
      });
      const payload = await response.json();
      if (!response.ok || !payload.ok) {
        status.textContent = payload.reason || "Review request failed";
        button.disabled = false;
        return;
      }
      const receipt = payload.receipt || {};
      status.textContent = `Queued ${text(receipt.request_id, "request")}`;
      button.textContent = "Queued";
    } catch (_error) {
      status.textContent = "Review API unavailable";
      button.disabled = false;
    }
  }

  function renderMemoryDraftQueue(data) {
    const queue = data.memory_draft_queue || {};
    const items = queue.items || [];
    const status = qs("memory-draft-status");
    if (status) status.textContent = `${queue.total || 0} draft${Number(queue.total || 0) === 1 ? "" : "s"}`;
    const grid = qs("memory-draft-grid");
    if (!grid) return;
    if (!items.length) {
      const empty = el("article", "memory-draft-card empty");
      empty.append(
        pill("MemoryOS", "held"),
        el("strong", "", "No draft memories waiting"),
        el("span", "", "Chat and GenesisOS signals will appear here before review.")
      );
      grid.replaceChildren(empty);
      return;
    }
    grid.replaceChildren(
      ...items.slice(0, 8).map((item) => {
        const card = el("article", `memory-draft-card ${text(item.type, "draft")}`);
        const refs = (item.raw_refs || []).slice(0, 3).join(" · ");
        const source = item.source_artifact ? artifactPreviewControl(item.source_artifact, "memory-draft-open") : null;
        const actions = el("div", "memory-draft-actions");
        const alreadyQueued = item.review_state && item.review_state !== "operator_review_required";
        const review = el("button", "memory-draft-review", alreadyQueued ? "Queued" : "Request Review");
        review.type = "button";
        review.disabled = Boolean(alreadyQueued);
        const reviewDetail = item.review_result || item.review_state || "Draft only";
        const reviewStatus = el("small", "memory-draft-review-status", reviewDetail);
        review.addEventListener("click", () => requestMemoryDraftReview(item, reviewStatus, review));
        actions.append(review, reviewStatus);
        card.append(
          pill(text(item.type, "memory draft"), item.status),
          el("strong", "", text(item.content_preview, "No preview available")),
          el("small", "", `${text(item.conversation_id, "conversation")} · ${text(item.origin, "origin")} · ${text(item.review_state, "review")}`),
          el("span", "memory-draft-ref", refs || text(item.genesis_ref, "provenance pending"))
        );
        if (item.review_result_ref) {
          const result = artifactPreviewControl(item.review_result_ref, "memory-draft-result-open");
          if (result) card.append(result);
        }
        if (source) card.append(source);
        card.append(actions);
        return card;
      })
    );
  }

  function setMode(mode) {
    const selected = mode === "operator" ? "operator" : "simple";
    document.body.classList.toggle("simple-mode", selected === "simple");
    document.body.classList.toggle("operator-mode", selected === "operator");
    localStorage.setItem("aios-control-mode", selected);
    document.querySelectorAll("[data-mode]").forEach((button) => {
      button.setAttribute("aria-pressed", button.dataset.mode === selected ? "true" : "false");
    });
  }

  function installModeToggle() {
    document.querySelectorAll("[data-mode]").forEach((button) => {
      button.addEventListener("click", () => setMode(button.dataset.mode));
    });
    setMode(localStorage.getItem("aios-control-mode") || "operator");
  }

  function roleLabel(role) {
    const labels = {
      genesis: "GenesisOS",
      memory: "MemoryOS",
      capability: "CapabilityOS",
      hive: "Hive Mind",
    };
    return labels[role] || role;
  }

  function artifactForRole(role, artifacts) {
    const keys = {
      genesis: "genesis",
      memory: "memory_context_pack",
      capability: "capability_route",
      hive: "hive_execution_plan",
    };
    return artifacts[keys[role] || role] || artifacts[`${role}_context_pack`] || artifacts[`${role}_route`] || "";
  }

  function artifactLabel(key) {
    const labels = {
      genesis: "branches",
      memory_context_pack: "context",
      memory_request: "request",
      capability_route: "route",
      hive_execution_plan: "plan",
      dispatch_packets: "packets",
    };
    return labels[key] || key;
  }

  function renderSessionSummary(target, receipt, envelope) {
    const roleStatuses = envelope.role_statuses || receipt.role_statuses || {};
    const artifacts = envelope.role_artifacts || {};
    const executor = envelope.executor_assignment || {};
    const roles = Object.entries(roleStatuses).map(([role, status]) => {
      const card = el("div", "session-role");
      const artifact = artifactForRole(role, artifacts);
      card.append(
        pill(roleLabel(role), status),
        el("strong", "", status),
        el("span", "", artifact || "artifact pending")
      );
      const open = artifactPreviewControl(artifact, "session-artifact-open");
      if (open) card.append(open);
      return card;
    });
    const summary = el("div", "session-summary");
    summary.append(
      el("strong", "", text(receipt.invocation_id, "invocation")),
      el("span", "", text(receipt.overall_status, "status unknown")),
      el("span", "", `next ${text(receipt.next_action, "review")}`),
      el("span", "", `executor ${text(executor.default_executor, "codex")} via ${text(executor.execution_owner, "hivemind")}`)
    );
    const envelopeRow = el("div", "session-envelope");
    const envelopePath = text(receipt.session_envelope || (envelope.role_artifacts || {}).session_envelope, "");
    envelopeRow.append(el("strong", "", "envelope"), el("span", "", envelopePath || "pending"));
    const envelopeOpen = artifactPreviewControl(envelopePath, "session-artifact-open");
    if (envelopeOpen) envelopeRow.append(envelopeOpen);
    const roleGrid = el("div", "session-role-grid");
    roleGrid.append(...roles);
    target.replaceChildren(summary, envelopeRow, roleGrid);
  }

  function renderSessionResult(receipt, envelope) {
    const target = qs("session-result");
    renderSessionSummary(target, receipt, envelope);
    renderSessionPromotion(target, receipt);
    renderAgentWork({
      invocation_id: receipt.invocation_id,
      goal: envelope.goal,
      created_at: receipt.created_at || envelope.created_at,
      overall_status: receipt.overall_status,
      next_action: receipt.next_action,
      session_envelope: receipt.session_envelope,
      role_statuses: envelope.role_statuses || receipt.role_statuses || {},
      role_artifacts: envelope.role_artifacts || {},
      executor_assignment: envelope.executor_assignment || {},
    });
  }

  function renderPromotionRows(target, receipt) {
    const paths = receipt.artifact_paths || {};
    const rows = [
      ["promotion", receipt.promotion_id],
      ["status", receipt.status],
      ["session_envelope", (receipt.session_envelope || {}).ref],
      ["contract_seed", paths.contract_seed],
      ["dispatch_preview", paths.dispatch_preview],
      ["next", receipt.next_action],
    ].filter((row) => row[1]);
    target.replaceChildren(
      ...rows.map(([label, value]) => {
        const row = el("div", "promotion-result-row");
        row.append(el("strong", "", label), el("span", "", value));
        const open = artifactPreviewControl(value, "promotion-artifact-open");
        if (open) row.append(open);
        return row;
      })
    );
  }

  function renderSessionPromotion(target, receipt) {
    const envelopeRef = receipt.session_envelope;
    if (!envelopeRef) return;
    const card = el("div", "session-promotion");
    const copy = el("div", "session-promotion-copy");
    copy.append(
      el("strong", "", "Promote reviewed session"),
      el("span", "", envelopeRef)
    );
    const confirmLabel = el("label", "promotion-confirm");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    confirmLabel.append(checkbox, el("span", "", "I reviewed this envelope"));
    const button = el("button", "", "Promote");
    button.type = "button";
    const status = el("small", "promotion-status", "Waiting for review confirmation");
    const result = el("div", "promotion-result");
    button.addEventListener("click", async () => {
      if (!checkbox.checked) {
        status.textContent = "Review confirmation required";
        checkbox.focus();
        return;
      }
      button.disabled = true;
      status.textContent = "Promoting";
      try {
        const response = await fetch("/api/promote_session", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_envelope: envelopeRef, confirm: true }),
        });
        const payload = await response.json();
        if (!response.ok || !payload.ok) {
          status.textContent = payload.reason || "Promotion blocked";
          return;
        }
        status.textContent = "Promotion ready";
        renderPromotionRows(result, payload.receipt || {});
      } catch (error) {
        status.textContent = "Promotion API is not running";
      } finally {
        button.disabled = false;
      }
    });
    card.append(copy, confirmLabel, button, status, result);
    target.append(card);
  }

  function renderAgentWork(invocation) {
    if (!invocation) return;
    qs("agent-work-title").textContent = invocation.goal || invocation.invocation_id || "Latest session";
    qs("agent-work-status").textContent = `${text(invocation.overall_status, "unknown")} · ${text(invocation.next_action, "review")}`;
    const artifacts = invocation.role_artifacts || {};
    const previews = invocation.artifact_previews || {};
    const roleStatuses = invocation.role_statuses || {};
    const roles = ["genesis", "memory", "capability", "hive"].map((role) => {
      const card = el("article", `agent-card ${role}`);
      const artifactPath = artifactForRole(role, artifacts);
      const previewEntry = Object.values(previews).find((item) => item && item.path === artifactPath) || {};
      card.append(
        pill(roleLabel(role), roleStatuses[role] || "waiting"),
        el("strong", "", text(roleStatuses[role], "waiting")),
        el("span", "", artifactPath || "No artifact yet")
      );
      const open = artifactPreviewControl(artifactPath, "agent-artifact-open");
      if (open) card.append(open);
      card.append(el("p", "agent-preview", previewEntry.preview ? `${previewEntry.preview}${previewEntry.truncated ? "..." : ""}` : "Preview pending"));
      return card;
    });
    const executor = invocation.executor_assignment || {};
    const executorCard = el("article", "agent-card executor");
    executorCard.append(
      pill("Executor", invocation.overall_status),
      el("strong", "", text(executor.default_executor, "unassigned")),
      el("span", "", text(executor.execution_owner, "hivemind"))
    );
    qs("agent-role-grid").replaceChildren(...roles, executorCard);
    const artifactRows = Object.entries(artifacts)
      .filter((row) => row[1])
      .map(([key, value]) => {
        const item = el("div", "artifact-item");
        const preview = previews[key] || {};
        item.append(
          el("strong", "", artifactLabel(key)),
          el("span", "artifact-path", value)
        );
        const open = artifactPreviewControl(value, "artifact-lane-open");
        if (open) item.append(open);
        item.append(el("p", "artifact-preview", preview.preview ? `${preview.preview}${preview.truncated ? "..." : ""}` : "Preview pending"));
        return item;
      });
    const envelope = el("div", "artifact-item");
    const sessionEnvelope = text(invocation.session_envelope, "");
    envelope.append(el("strong", "", "envelope"), el("span", "artifact-path", sessionEnvelope || "pending"));
    const envelopeOpen = artifactPreviewControl(sessionEnvelope, "artifact-lane-open");
    if (envelopeOpen) envelope.append(envelopeOpen);
    qs("artifact-lane").replaceChildren(envelope, ...artifactRows.slice(0, 7));
  }

  function renderLatestInvocation(data) {
    const latest = (((data.invocations || {}).latest || [])[0]) || null;
    if (latest) renderAgentWork(latest);
  }

  function renderWorkTimeline(data) {
    const rows = ((data.dispatches || {}).latest || []).slice(0, 6).map((dispatch) => {
      const row = el("div", "timeline-row");
      row.append(
        pill(text(dispatch.status, "unknown"), dispatch.status),
        el("strong", "", text(dispatch.dispatch_id)),
        el("span", "", text(dispatch.goal || dispatch.contract_id)),
        el("span", "", `sent ${dispatch.sent.length} · collected ${dispatch.collected.length}`)
      );
      return row;
    });
    qs("work-timeline").replaceChildren(...rows);
  }

  function renderHiveTui(data) {
    const board = (data.os_observatory || {}).hive_board
      || ((data.os_observatory || {}).hive || {}).hive_board
      || (data.hive_board || {});
    const status = qs("hive-board-status");
    const overview = qs("hive-board-overview");
    const pipeline = qs("hive-board-pipeline");
    const agents = qs("hive-board-agents");
    const artifacts = qs("hive-board-artifacts");

    if (!overview || !pipeline || !agents || !artifacts) return;
    if (!board || !board.run_id) {
      status.textContent = "No active run";
      overview.textContent = "Hive has no current run state.";
      pipeline.replaceChildren(el("div", "hive-board-item", "No run loaded."));
      agents.replaceChildren(el("div", "hive-board-item", "No run loaded."));
      artifacts.replaceChildren(el("div", "hive-board-item", "No run loaded."));
      return;
    }

    const phaseText = text(board.phase, "unknown phase");
    const projectText = text(board.project, "Hive Mind");
    const taskText = text(board.task, "No task captured");
    const updatedAt = text(board.updated_at, "No timestamp");
    const message = text(board.message, "");
    const next = board.next || {};

    status.textContent = text(next.command, "Watching");
    overview.replaceChildren(
      el("p", "hive-board-overview-title", `${text(board.run_id)} • ${phaseText}`),
      el("p", "hive-board-overview-meta", `${projectText} · updated ${updatedAt}${board.pipeline_done != null ? ` · ${text(board.pipeline_done)}/${text(board.pipeline_total)} pipeline steps` : ""}`),
      el("p", "hive-board-overview-task", taskText),
      el("p", "hive-board-overview-note", message || `Next: ${text(next.command)} (${text(next.reason)})`)
    );

    const pipelineItems = (board.pipeline || []).slice(0, 20).map((item) => {
      const row = el("div", `hive-board-item status-${text(item.status)}`);
      row.append(
        el("strong", "", text(item.step)),
        el("span", "", `${text(item.path)} · ${text(item.status)}`)
      );
      const open = artifactPreviewControl(item.path, "hive-artifact-open");
      if (open) row.append(open);
      return row;
    });
    pipeline.replaceChildren(...(pipelineItems.length ? pipelineItems : [el("div", "hive-board-item", "No pipeline artifacts found.")]));

    const agentItems = (board.agents || []).slice(0, 20).map((entry) => {
      if (!entry || typeof entry !== "object") return null;
      const row = el("div", `hive-board-item status-${text(entry.status || "unknown")}`);
      row.append(
        el("strong", "", text(entry.name)),
        el("span", "", `${text(entry.role, "agent")} · ${text(entry.status || "unknown")}`)
      );
      return row;
    }).filter(Boolean);
    agents.replaceChildren(...(agentItems.length ? agentItems : [el("div", "hive-board-item", "No agent state found.")]));

    const artifactItems = (board.artifacts || []).slice(0, 40).map((entry) => {
      if (!entry || typeof entry !== "object") return null;
      const row = el("div", `hive-board-item status-${text(entry.status)}`);
      row.append(
        el("strong", "", text(entry.name)),
        el("span", "", `${text(entry.path)} · ${text(entry.status)}`)
      );
      const open = artifactPreviewControl(entry.path, "hive-artifact-open");
      if (open) row.append(open);
      return row;
    }).filter(Boolean);
    artifacts.replaceChildren(...(artifactItems.length ? artifactItems : [el("div", "hive-board-item", "No artifacts found.")]));
  }

  function renderGenesisLens(data) {
    const lens = data.genesis_lens || {};
    const status = qs("genesis-lens-status");
    if (status) {
      status.textContent = `${text(lens.authority, "speculative_only")} · ${text(lens.source_invocation, "no invocation")}`;
    }
    const branches = (lens.branches || []).slice(0, 5);
    const grid = qs("genesis-branch-grid");
    if (!grid) return;
    if (!branches.length) {
      const empty = el("div", "genesis-empty");
      empty.textContent = "No GenesisOS branches in the latest session.";
      grid.replaceChildren(empty);
      return;
    }
    grid.replaceChildren(
      ...branches.map((branch) => {
        const card = el("article", `genesis-branch ${text(branch.type, "branch")}`);
        card.append(
          pill(text(branch.type, "branch"), "active"),
          el("strong", "", text(branch.premise, "Premise pending")),
          el("span", "branch-break", text(branch.what_it_breaks, "No break recorded")),
          el("p", "", text(branch.why_it_might_matter, "No rationale recorded")),
          el("small", "", text(branch.risk, "Speculative only"))
        );
        return card;
      })
    );
  }

  function renderFrictionRadar(data) {
    const radar = data.friction_radar || {};
    const items = (radar.items || []).slice(0, 4);
    const status = qs("friction-radar-status");
    if (status) status.textContent = `${items.length} need${items.length === 1 ? "" : "s"}`;
    const grid = qs("friction-grid");
    if (!grid) return;
    grid.replaceChildren(
      ...items.map((item) => {
        const card = el("article", `friction-card ${text(item.severity, "info")}`);
        card.append(
          pill(text(item.owner, "myworld"), item.severity),
          el("strong", "", text(item.need, "review")),
          el("span", "", text(item.reason, "No reason recorded")),
          el("small", "", text(item.source, "monitor"))
        );
        return card;
      })
    );
  }

  function metric(label, value, unit) {
    const row = el("div", "os-metric");
    row.append(el("strong", "", number(value)), el("span", "", unit ? `${label} ${unit}` : label));
    return row;
  }

  function renderOsObservatory(data) {
    const observatory = data.os_observatory || {};
    const lanes = observatory.lanes || [];
    const status = qs("os-observatory-status");
    if (status) status.textContent = `${lanes.length || 0} OS lanes`;

    const orbit = qs("os-orbit");
    if (orbit) {
      const center = el("article", "os-orbit-center");
      center.append(
        el("span", "", "AIOS"),
        el("strong", "", text((observatory.myworld || {}).status, "unknown")),
        el("small", "", text((observatory.myworld || {}).headline, "control plane waiting"))
      );
      const nodes = lanes.map((lane) => {
        const node = el("article", `os-orbit-node ${text(lane.id, "lane")}`);
        node.append(el("span", "", text(lane.role)), el("strong", "", text(lane.label)), el("small", "", text(lane.status)));
        return node;
      });
      orbit.replaceChildren(center, ...nodes);
    }

    const grid = qs("os-lane-grid");
    if (!grid) return;
    const memory = observatory.memory || {};
    const capability = observatory.capability || {};
    const genesis = observatory.genesis || {};
    const hive = observatory.hive || {};
    const myworld = observatory.myworld || {};
    const cards = [
      {
        id: "memory",
        title: "MemoryOS",
        subtitle: "Knowledge graph",
        status: memory.status,
        headline: memory.headline,
        metrics: [
          ["nodes", memory.nodes, ""],
          ["edges", memory.edges, ""],
          ["accepted", memory.accepted, ""],
          ["draft", memory.draft, ""],
          ["retrieval", memory.retrieval_traces, "traces"],
          ["hypergraph", memory.hyperedges, "hyperedges"],
        ],
        detail: `${number(memory.memory_objects)} memory objects · ${number(memory.reviews)} reviews · ${number(memory.sources)} sources`,
      },
      {
        id: "capability",
        title: "CapabilityOS",
        subtitle: "Search and route planner",
        status: capability.status,
        headline: capability.headline,
        metrics: [
          ["cards", capability.capability_cards, ""],
          ["observations", capability.observations, ""],
          ["gaps", capability.gaps, ""],
          ["observed", capability.observed_capabilities, "capabilities"],
        ],
        detail: (capability.top_routes || []).slice(0, 3).map((route) => `${route.id} (${route.score})`).join(" · ") || "No recommendation route yet",
      },
      {
        id: "genesis",
        title: "GenesisOS",
        subtitle: "Worldline generator",
        status: genesis.status,
        headline: genesis.headline,
        metrics: [
          ["branches", genesis.branches, ""],
        ],
        detail: `${text(genesis.authority, "speculative_only")} · ${(genesis.branch_types || []).join(" · ") || "Waiting for divergence artifact"}`,
      },
      {
        id: "hive",
        title: "Hive Mind",
        subtitle: "Execution wrapper",
        status: hive.status,
        headline: hive.headline,
        metrics: [
          ["dispatches", hive.dispatch_total, ""],
          ["latest", hive.latest_invocation ? 1 : 0, "invocation"],
        ],
        detail: hive.latest_goal || hive.latest_invocation || "No latest execution goal",
      },
      {
        id: "myworld",
        title: "MyWorld",
        subtitle: "Sovereign control",
        status: myworld.status,
        headline: myworld.headline,
        metrics: [
          ["contracts", myworld.contracts, ""],
          ["dispatches", myworld.dispatches, ""],
        ],
        detail: `round ${text(myworld.round, "unknown")}`,
      },
    ];

    grid.replaceChildren(
      ...cards.map((card) => {
        const item = el("article", `os-lane-card ${card.id}`);
        const head = el("div", "os-lane-card-head");
        head.append(pill(card.title, card.status), el("span", "", card.subtitle));
        const metrics = el("div", "os-metric-grid");
        metrics.append(...card.metrics.map(([label, value, unit]) => metric(label, value, unit)));
        item.append(head, el("strong", "os-lane-headline", text(card.headline, "waiting")), metrics, el("p", "os-lane-detail", text(card.detail, "No detail")));
        return item;
      })
    );
  }

  function installSessionForm() {
    const form = qs("session-form");
    if (!form) return;
    const input = qs("session-input");
    const contract = qs("session-contract-id");
    const button = qs("session-submit");
    const status = qs("session-status");
    const result = qs("session-result");
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const goal = input.value.trim();
      const contractId = contract.value.trim();
      result.replaceChildren();
      if (!goal) {
        status.textContent = "Goal required";
        input.focus();
        return;
      }
      button.disabled = true;
      status.textContent = "Creating session";
      try {
        const response = await fetch("/api/session", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ goal, contract_id: contractId }),
        });
        const payload = await response.json();
        if (!response.ok || !payload.ok) {
          status.textContent = payload.reason || "Session failed";
          return;
        }
        status.textContent = "Session ready";
        renderSessionResult(payload.receipt || {}, payload.session_envelope || {});
      } catch (error) {
        status.textContent = "Local session API is not running";
      } finally {
        button.disabled = false;
      }
    });
  }

  function chatWsUrl() {
    const params = new URLSearchParams(window.location.search);
    if (params.get("chatWs")) return params.get("chatWs");
    const port = params.get("wsPort") || "8766";
    return `ws://${window.location.hostname || "127.0.0.1"}:${port}/chat`;
  }

  function chatMeta(result) {
    const chair = result.gate_chair_status || {};
    const memory = result.memory_context || {};
    const memoryCount = Number(memory.context_items || 0);
    const substrate = result.chosen_substrate || "";
    const parts = [
      "AIOS Gate",
      substrate === "aios_gate" ? "direct" : "",
      chair.attempted ? `Chair ${chair.mode || chair.status || "active"}` : "",
      memoryCount ? `MemoryOS ${memoryCount}` : "",
    ].filter(Boolean);
    return parts.join(" · ");
  }

  function chatEvidenceItems(result) {
    if (!result || typeof result !== "object") return [];
    const items = [];
    const memory = result.memory_context || {};
    const seenMemory = new Set();
    (memory.negative_evidence || []).slice(0, 3).forEach((item) => {
      if (!item || !item.id) return;
      seenMemory.add(item.id);
      const refs = Array.isArray(item.raw_refs) && item.raw_refs.length ? ` · ${item.raw_refs[0]}` : "";
      items.push({ key: `negative:${item.id}`, value: `${item.content || ""}${refs}` });
    });
    (memory.selected_memories || []).slice(0, 4).forEach((item) => {
      if (!item || !item.id) return;
      if (seenMemory.has(item.id)) return;
      const refs = Array.isArray(item.raw_refs) && item.raw_refs.length ? ` · ${item.raw_refs[0]}` : "";
      items.push({ key: `memory:${item.id}`, value: `${item.content || ""}${refs}` });
    });
    const genesis = result.genesis_friction || {};
    (genesis.frictions || []).slice(0, 3).forEach((item) => {
      if (!item || !item.branch_id) return;
      const need = item.need ? ` -> ${item.need}` : "";
      items.push({ key: `genesis:${item.branch_id}`, value: `${item.discomfort || item.type || "friction"}${need}` });
    });
    if (result.provider_turn) {
      items.push({ key: "provider_turn", value: result.provider_turn });
    }
    if (result.gate_chair_turn) {
      items.push({ key: "gate_chair_turn", value: result.gate_chair_turn });
    }
    if (result.gate_chair_status && result.gate_chair_status.attempted) {
      const chair = result.gate_chair_status;
      items.push({ key: "gate_chair_status", value: `${chair.status || "unknown"} · executed=${Boolean(chair.executed)}` });
    }
    Object.entries(result.artifact_paths || {})
      .filter((entry) => entry[1])
      .slice(0, 4)
      .forEach(([key, value]) => items.push({ key, value }));
    return items;
  }

  function artifactPath(value) {
    const path = String(value || "").trim();
    if (!path || path.includes("\n")) return "";
    return path.startsWith(".aios/") || path.startsWith("docs/") || path.startsWith("apps/control/") ? path : "";
  }

  function artifactAuthority(value) {
    const path = artifactPath(value);
    if (path.startsWith(".aios/invocations/")) return { call: "ingest", authority: "AIOS invocation record" };
    if (path.startsWith(".aios/chat/")) return { call: "close", authority: "AIOS chat record" };
    if (path.startsWith(".aios/outbox/")) return { call: "close", authority: "dispatch result" };
    if (path.startsWith(".aios/promotions/")) return { call: "promote", authority: "MyWorld promotion" };
    if (path.startsWith("docs/contracts/")) return { call: "promote", authority: "MyWorld contract" };
    if (path.startsWith("docs/discoveries/")) return { call: "observe", authority: "MyWorld discovery" };
    if (path.startsWith("apps/control/")) return { call: "observe", authority: "Control UI schema" };
    return { call: "observe", authority: "AIOS artifact" };
  }

  function authorityBadge(value) {
    const info = artifactAuthority(value);
    return el("span", "authority-badge", `${info.call} · ${info.authority}`);
  }

  function setArtifactHash(path) {
    const params = new URLSearchParams(window.location.hash.slice(1));
    params.set("artifact", path);
    window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}#${params.toString()}`);
  }

  function artifactFromHash() {
    const params = new URLSearchParams(window.location.hash.slice(1));
    return artifactPath(params.get("artifact") || "");
  }

  function clearArtifactHash() {
    const params = new URLSearchParams(window.location.hash.slice(1));
    params.delete("artifact");
    const suffix = params.toString();
    window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}${suffix ? `#${suffix}` : ""}`);
  }

  async function openArtifact(path, target, options = {}) {
    target.textContent = "Loading artifact...";
    try {
      const response = await fetch("/api/artifact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path }),
      });
      const payload = await response.json();
      if (!response.ok || !payload.ok) {
        target.textContent = payload.reason || "Artifact unavailable";
        return;
      }
      const body = payload.json ? JSON.stringify(payload.json, null, 2) : payload.text;
      target.textContent = body || "(empty artifact)";
      target.dataset.artifactPath = payload.path || path;
      if (options.updateHash !== false) setArtifactHash(payload.path || path);
    } catch (error) {
      target.textContent = "Artifact API unavailable";
    }
  }

  async function copyText(value, status) {
    try {
      await navigator.clipboard.writeText(String(value || ""));
      if (status) status.textContent = "Copied";
    } catch (error) {
      if (status) status.textContent = "Copy unavailable";
    }
  }

  function artifactPreviewControl(value, className) {
    const path = artifactPath(value);
    if (!path) return null;
    const wrap = el("div", className || "artifact-open-control");
    const button = el("button", "artifact-open", "Open");
    button.type = "button";
    const copyPath = el("button", "artifact-copy", "Copy path");
    copyPath.type = "button";
    const copyBody = el("button", "artifact-copy", "Copy preview");
    copyBody.type = "button";
    const status = el("small", "artifact-copy-status");
    const preview = el("pre", "artifact-open-preview");
    button.addEventListener("click", () => openArtifact(path, preview));
    copyPath.addEventListener("click", () => copyText(path, status));
    copyBody.addEventListener("click", () => copyText(preview.textContent, status));
    const actions = el("div", "artifact-open-actions");
    actions.append(button, copyPath, copyBody, status);
    wrap.append(authorityBadge(path), actions, preview);
    return wrap;
  }

  function artifactHashPanel() {
    let panel = qs("artifact-hash-panel");
    if (panel) return panel;
    panel = el("aside", "artifact-hash-panel");
    panel.id = "artifact-hash-panel";
    const head = el("div", "artifact-hash-head");
    const title = el("strong", "", "Artifact preview");
    const close = el("button", "artifact-hash-close", "Close");
    close.type = "button";
    close.addEventListener("click", () => {
      clearArtifactHash();
      panel.remove();
    });
    head.append(title, close);
    const pathLabel = el("small", "artifact-hash-path");
    const preview = el("pre", "artifact-hash-preview");
    panel.append(head, pathLabel, preview);
    document.body.append(panel);
    return panel;
  }

  function restoreArtifactHash() {
    const path = artifactFromHash();
    if (!path) {
      const existing = qs("artifact-hash-panel");
      if (existing) existing.remove();
      return;
    }
    const panel = artifactHashPanel();
    const pathLabel = panel.querySelector(".artifact-hash-path");
    const preview = panel.querySelector(".artifact-hash-preview");
    if (pathLabel) pathLabel.textContent = path;
    if (preview) openArtifact(path, preview, { updateHash: false });
  }

  function appendInlineEvidence(row, result) {
    const items = chatEvidenceItems(result);
    if (!items.length) return;
    const details = el("details", "inline-chat-evidence");
    const summary = el("summary", "", `Trace ${items.length}`);
    const lane = el("div", "inline-chat-artifacts");
    items.forEach((item) => {
      const entry = el("div", "inline-chat-artifact");
      entry.append(el("small", "", `${item.key}: ${item.value}`));
      const path = artifactPath(item.value);
      if (path) {
        const button = el("button", "inline-chat-open", "Open");
        button.type = "button";
        const preview = el("pre", "inline-chat-preview");
        button.addEventListener("click", () => openArtifact(path, preview));
        entry.append(authorityBadge(path), button, preview);
      }
      lane.append(entry);
    });
    details.append(summary, lane);
    row.append(details);
  }

  function addInlineChatMessage(role, body, meta, result) {
    const row = el("article", `inline-chat-message ${role}`);
    row.append(el("span", "inline-chat-role", role === "user" ? "You" : "AIOS"));
    row.append(el("p", "", body));
    if (role === "assistant" && meta) row.append(el("span", "inline-chat-meta", meta));
    appendInlineEvidence(row, result);
    const thread = qs("inline-chat-thread");
    thread.append(row);
    thread.scrollTop = thread.scrollHeight;
  }

  function installInlineChat() {
    const form = qs("inline-chat-form");
    if (!form) return;
    const input = qs("inline-chat-input");
    const conversation = qs("inline-chat-conversation");
    const button = qs("inline-chat-submit");
    const status = qs("inline-chat-status");
    let socket = null;
    async function sendViaHttp(message, conversationId) {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, conversation_id: conversationId }),
      });
      const payload = await response.json();
      if (!response.ok || !payload.ok) {
        throw new Error(payload.reason || "chat_failed");
      }
      return payload.result || {};
    }
    function connect() {
      if (!("WebSocket" in window)) {
        status.textContent = "Unavailable";
        return;
      }
      socket = new WebSocket(chatWsUrl());
      socket.addEventListener("open", () => {
        status.textContent = "Connected";
      });
      socket.addEventListener("message", (event) => {
        let frame;
        try {
          frame = JSON.parse(event.data);
        } catch (_error) {
          status.textContent = "Unreadable";
          return;
        }
        if (frame.type === "chat_ready") {
          status.textContent = "Ready";
          return;
        }
        if (frame.type === "chat_error") {
          status.textContent = frame.reason || "Chat error";
          button.disabled = false;
          return;
        }
        if (frame.type === "chat_response") {
          const result = frame.result || {};
          addInlineChatMessage("assistant", result.response || "AIOS returned no text.", chatMeta(result), result);
          status.textContent = "Ready";
          button.disabled = false;
        }
      });
      socket.addEventListener("close", () => {
        status.textContent = "HTTP fallback";
        window.setTimeout(connect, 2000);
      });
      socket.addEventListener("error", () => {
        status.textContent = "HTTP fallback";
        button.disabled = false;
      });
    }
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const message = input.value.trim();
      if (!message) {
        input.focus();
        return;
      }
      const conversationId = conversation.value || "control-center";
      addInlineChatMessage("user", message, conversationId, {});
      input.value = "";
      button.disabled = true;
      status.textContent = "Routing";
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ message, conversation_id: conversationId }));
        return;
      }
      try {
        const result = await sendViaHttp(message, conversationId);
        addInlineChatMessage("assistant", result.response || "AIOS returned no text.", chatMeta(result), result);
        status.textContent = "Ready via HTTP";
      } catch (error) {
        status.textContent = "Chat failed";
      } finally {
        button.disabled = false;
      }
    });
    document.querySelectorAll("[data-chat-prompt]").forEach((promptButton) => {
      promptButton.addEventListener("click", () => {
        input.value = promptButton.dataset.chatPrompt || "";
        input.focus();
      });
    });
    if (qs("inline-chat-thread").children.length === 0) {
      addInlineChatMessage(
        "assistant",
        "안녕. 바로 물어봐. 필요한 기억, 도구 경로, 실행 판단은 AIOS가 뒤에서 붙일게.",
        "AIOS Gate · ready",
        {}
      );
    }
    connect();
  }

  function renderAskResult(receipt) {
    const paths = receipt.artifact_paths || {};
    const rows = [
      ["ask", receipt.ask_id],
      ["status", receipt.status],
      ["instruction", paths.instruction],
      ["praxis", paths.praxis],
      ["contract_seed", paths.contract_seed],
    ].filter((row) => row[1]);
    qs("ask-result").replaceChildren(
      ...rows.map(([label, value]) => {
        const row = el("div", "ask-result-row");
        row.append(el("strong", "", label), el("span", "", value));
        return row;
      })
    );
  }

  function installAskForm() {
    const form = qs("ask-form");
    if (!form) return;
    const input = qs("ask-input");
    const button = qs("ask-submit");
    const status = qs("ask-status");
    const result = qs("ask-result");
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const goal = input.value.trim();
      result.replaceChildren();
      if (!goal) {
        status.textContent = "Goal required";
        input.focus();
        return;
      }
      button.disabled = true;
      status.textContent = "Creating ask";
      try {
        const response = await fetch("/api/ask", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            goal,
            draft_contract: qs("ask-draft-contract").checked,
          }),
        });
        const payload = await response.json();
        if (!response.ok || !payload.ok) {
          status.textContent = payload.reason || "Ask failed";
          return;
        }
        status.textContent = "Ask created";
        renderAskResult(payload.receipt || {});
      } catch (error) {
        status.textContent = "Local ask API is not running";
      } finally {
        button.disabled = false;
      }
    });
  }

  function describeEvent(frame) {
    const event = frame.event || {};
    if (event.kind === "task.created") return "A new task was created.";
    if (event.kind === "task.updated") return "A task was updated.";
    if (event.kind === "monitor.event") return `Monitor update: ${text((event.payload || {}).line, "activity recorded")}`;
    return "New system activity was recorded.";
  }

  function applyLiveFrame(frame) {
    if (!frame) return;
    if (frame.type === "heartbeat") {
      qs("live-status").textContent = `Live ${text((frame.monitor || {}).health, "unknown")}`;
      qs("simple-health").textContent =
        (frame.monitor || {}).health === "clear" ? "All systems are healthy." : "Some work needs operator attention.";
      return;
    }
    if (frame.type !== "event") return;
    liveEventCount += 1;
    qs("live-event-count").textContent = `${liveEventCount} received`;
    const row = el("div", "live-event");
    row.append(el("strong", "", describeEvent(frame)), el("span", "", text(frame.ts_iso)));
    const list = qs("live-events");
    list.prepend(row);
    while (list.children.length > 20) list.removeChild(list.lastChild);
    qs("simple-activity").textContent = describeEvent(frame);
  }

  function render(data) {
    if (!data) {
      qs("goal-title").textContent = "Snapshot missing";
      qs("status-strip").replaceChildren(pill("Run scripts/aios_control_snapshot.py", "held"));
      return;
    }
    renderGoal(data);
    renderStatus(data);
    renderCompletion(data);
    renderInstallation(data);
    renderWorkbench(data);
    renderLoopMap(data);
    renderExecutionLens(data);
    renderContracts(data);
    renderDispatches(data);
    renderRepos(data);
    renderRoutes(data);
    renderStops(data);
    renderSimple(data);
    renderHiveTui(data);
    renderLatestInvocation(data);
    renderWorkTimeline(data);
    renderPromotionQueue(data);
    renderMemoryDraftQueue(data);
    renderGenesisLens(data);
    renderFrictionRadar(data);
    renderOsObservatory(data);
  }

  window.AIOSControl = {
    applyLiveFrame,
    render,
    setMode,
  };

  render(snapshot);
  installModeToggle();
  installSessionForm();
  installInlineChat();
  installAskForm();
  restoreArtifactHash();
  window.addEventListener("hashchange", restoreArtifactHash);
})();

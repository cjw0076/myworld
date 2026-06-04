(function () {
  const snapshot = window.AIOS_CONTROL_SNAPSHOT;
  let liveEventCount = 0;
  let controlVisualWorkflow = null;

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

  function focusInlineChat(prompt, statusText = "Prompt prepared") {
    const input = qs("inline-chat-input");
    if (!input) return;
    input.value = prompt;
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.focus();
    const status = qs("inline-chat-status");
    if (status) status.textContent = statusText;
    const conversation = qs("conversation");
    if (conversation) conversation.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function chatPromptButton(label, prompt, className = "aios-inline-action") {
    const button = el("button", className, label);
    button.type = "button";
    button.addEventListener("click", () => focusInlineChat(prompt));
    return button;
  }

  function askActionButton(label, goal, className = "aios-inline-action") {
    const button = el("button", className, label);
    button.type = "button";
    button.addEventListener("click", () => submitAskGoal(goal, button));
    return button;
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

  function renderCommandEvidence(data) {
    const grid = qs("command-evidence-grid");
    const list = qs("command-receipt-list");
    if (!grid || !list) return;
    renderOsLiveLoop(data);
    const contracts = (data.contracts || {}).counts || {};
    const dispatches = (data.dispatches || {}).counts || {};
    const memory = ((data.os_observatory || {}).memory) || {};
    const capability = ((data.os_observatory || {}).capability) || {};
    const genesis = ((data.os_observatory || {}).genesis) || {};
    const chair = ((data.installation || {}).gate_chair) || {};
    const stats = [
      ["Contracts", Number(contracts.accepted || 0) + Number(contracts.proposed || 0), "review"],
      ["Dispatch", Number(dispatches.released || 0) + Number(dispatches.collected || 0), "sent + done"],
      ["Memory", memory.accepted || 0, "accepted"],
      ["Routes", capability.capability_cards || 0, "cards"],
      ["Genesis", genesis.branches || 0, "branches"],
    ];
    grid.replaceChildren(
      ...stats.map(([label, value, detail]) => {
        const card = el("article", "command-evidence-stat");
        card.append(el("strong", "", number(value)), el("span", "", label), el("small", "", detail));
        return card;
      })
    );

    const invocation = (((data.invocations || {}).latest || [])[0]) || {};
    const latestAsk = (((data.asks || {}).latest || [])[0]) || {};
    const latestOffline = (((data.offline_user || {}).latest || [])[0]) || {};
    const governedAsk = qs("command-governed-ask");
    if (governedAsk) {
      const askCard = latestAsk.ask_id ? renderGovernedAskCard(latestAsk, data) : null;
      const offlineCard = latestOffline.path ? renderOfflineUserCard(latestOffline) : null;
      governedAsk.replaceChildren(...[offlineCard, askCard].filter(Boolean));
      governedAsk.hidden = !askCard && !offlineCard;
    }
    const previews = invocation.artifact_previews || {};
    const latestDispatches = ((data.dispatches || {}).latest || []).slice(0, 2);
    const latestMemoryDispatch = ((data.dispatches || {}).latest || []).find((item) => (item.memory_context || {}).memory_backed);
    const latestMemoryContext = (latestMemoryDispatch || {}).memory_context || {};
    const routeSteps = [
      {
        label: "Gate",
        state: text((data.monitor || {}).health, "clear"),
        detail: text((((data.goals || {}).evolution || {}).readiness), "intake ready"),
      },
      {
        label: "Memory",
        state: text(memory.status, "waiting"),
        detail: latestMemoryContext.retrieval_trace
          ? `${latestMemoryContext.retrieval_trace} · signal ${text(latestMemoryContext.signal_coverage)}`
          : `${number(memory.retrieval_traces_with_selected || memory.retrieval_traces || 0)} traces`,
      },
      {
        label: "Capability",
        state: text(capability.status, "waiting"),
        detail: `${number(capability.capability_cards || 0)} cards`,
      },
      {
        label: "Genesis",
        state: text(genesis.status, "waiting"),
        detail: `${number(genesis.branches || 0)} lanes`,
      },
      {
        label: "Hive",
        state: text(((data.os_observatory || {}).hive || {}).status, "waiting"),
        detail: text(((data.os_observatory || {}).hive || {}).next_action, "dispatch"),
      },
      {
        label: "Proofs",
        state: "audit",
        detail: `${text((data.completion || {}).criteria_met, "review")} · ${number((data.contracts || {}).total || 0)} contracts`,
      },
    ];
    const receipts = [
      ...Object.entries(previews).slice(0, 4).map(([label, preview]) => ({
        label,
        path: preview.path,
        status: preview.truncated ? "preview" : "complete",
      })),
      ...latestDispatches.map((item) => ({
        label: item.dispatch_id || item.contract_id || "dispatch",
        path: item.contract_id || item.status,
        status: item.status || "dispatch",
      })),
      ...(latestMemoryContext.retrieval_trace ? [{
        label: "Memory trace",
        path: latestMemoryContext.context_pack || latestMemoryContext.session_envelope_ref || latestMemoryContext.packet,
        status: latestMemoryContext.signal_coverage ? `signal ${latestMemoryContext.signal_coverage}` : "rtrace",
      }] : []),
    ].filter((item) => item.path);

    const decisionMap = el("article", "command-decision-map");
    const decisionHead = el("div", "command-decision-head");
    decisionHead.append(el("strong", "", "Decision Map"), el("span", "", "why AIOS chose this route"));
    const decisionFlow = el("div", "command-decision-flow");
    const memoryGraph = memory.graph_preview || {};
    const capabilityPreview = capability.route_preview || {};
    const genesisPreview = (data.genesis_lens || {}).worldline_preview || {};
    const runtimePreview = chair.runtime_preview || {};
    const decisionNodes = [
      {
        label: "Chair",
        state: chair.demoted ? "fallback" : text(chair.effective_mode || chair.mode, "internal"),
        detail: `${(runtimePreview.nodes || []).length} runtime node${(runtimePreview.nodes || []).length === 1 ? "" : "s"}`,
      },
      {
        label: "Memory",
        state: latestMemoryContext.retrieval_trace ? "retrieved" : text(memory.status, "waiting"),
        detail: latestMemoryContext.retrieval_trace || `${(memoryGraph.edges || []).length} evidence edge${(memoryGraph.edges || []).length === 1 ? "" : "s"}`,
      },
      {
        label: "Capability",
        state: text(capability.status, "ready"),
        detail: `${(capabilityPreview.edges || []).length} route edge${(capabilityPreview.edges || []).length === 1 ? "" : "s"}`,
      },
      {
        label: "Genesis",
        state: text(genesis.status, "speculative"),
        detail: `${(genesisPreview.edges || []).length} worldline edge${(genesisPreview.edges || []).length === 1 ? "" : "s"}`,
      },
      {
        label: "Hive",
        state: text(((data.os_observatory || {}).hive || {}).status, "waiting"),
        detail: text(((data.os_observatory || {}).hive || {}).next_action, "dispatch"),
      },
    ];
    decisionNodes.forEach((node, index) => {
      const step = el("div", `command-decision-node ${String(node.state || "").toLowerCase().replace(/[^a-z0-9_-]+/g, "-")}`);
      step.append(el("i", "", String(index + 1)), el("strong", "", node.label), el("span", "", node.state), el("small", "", node.detail));
      decisionFlow.append(step);
    });
    decisionMap.append(decisionHead, decisionFlow);

    const routeRail = el("article", "command-route-rail");
    const routeHead = el("div", "command-route-head");
    routeHead.append(el("strong", "", "Live OS Route"), el("span", "", text(invocation.invocation_id || "current turn")));
    routeRail.append(routeHead);
    const routeList = el("div", "command-route-list");
    routeSteps.forEach((step, index) => {
      const row = el("div", `command-route-step ${String(step.state || "").toLowerCase().replace(/[^a-z0-9_-]+/g, "-")}`);
      row.append(el("i", "", String(index + 1)), el("strong", "", step.label), el("span", "", step.state), el("small", "", step.detail));
      routeList.append(row);
    });
    routeRail.append(routeList);

    list.replaceChildren(
      decisionMap,
      routeRail,
      ...(receipts.length ? receipts.slice(0, 6).map((item) => {
        const row = el("div", "command-receipt-row");
        const head = el("div", "command-receipt-row-head");
        head.append(el("strong", "", artifactLabel(text(item.label))), pill(text(item.status), item.status));
        const path = el("span", "command-receipt-path", text(item.path));
        path.title = text(item.path);
        row.append(head, path);
        const open = artifactPreviewControl(item.path, "command-receipt-open");
        if (open) row.append(open);
        return row;
      }) : [el("div", "command-receipt-row empty", "No recent receipts found.")])
    );
  }

  function renderGovernedAskCard(ask, data) {
    const card = el("div", "command-receipt-row governed-ask-row");
    const head = el("div", "command-receipt-row-head");
    head.append(el("strong", "", "Governed Ask"), pill(text(ask.status, "ask"), ask.status));
    const goal = el("span", "command-receipt-path", text(ask.goal, ask.ask_id));
    goal.title = text(ask.goal, ask.ask_id);
    const facts = el("div", "governed-ask-facts");
    [
      ["ask", ask.ask_id],
      ["next", ask.next_action],
      ["roles", Object.entries(ask.role_statuses || {}).map(([role, status]) => `${role}:${status}`).join(" · ")],
    ].filter((row) => row[1]).forEach(([label, value]) => {
      const chip = el("span", "", `${label}: ${value}`);
      chip.title = value;
      facts.append(chip);
    });
    const actions = el("div", "governed-ask-actions");
    [
      [ask.contract_seed, "Contract seed"],
      [ask.instruction, "Instruction"],
      [ask.praxis, "Praxis"],
      [ask.receipt, "Receipt"],
    ].forEach(([path, label]) => {
      if (!path) return;
      const open = artifactPreviewControl(path, "command-receipt-open");
      if (open) {
        const wrapper = el("div", "governed-ask-open");
        wrapper.append(el("small", "", label), open);
        actions.append(wrapper);
      }
    });
    card.append(head, goal, facts);
    if (ask.materialized_contract) {
      const materialized = artifactPreviewControl(ask.materialized_contract, "command-receipt-open");
      const done = el("div", "governed-ask-materialize done");
      done.append(el("small", "", `Proposed ${text(ask.materialized_contract_id, "contract")}`));
      if (materialized) done.append(materialized);
      actions.append(done);
    } else if (ask.contract_seed && ask.receipt) {
      const materialize = el("div", "governed-ask-materialize");
      const input = document.createElement("input");
      const suggestedAsc = text(((data.promotions || {}).next_contract_id), "ASC-0000");
      input.type = "text";
      input.placeholder = suggestedAsc;
      input.value = suggestedAsc;
      input.setAttribute("aria-label", "ASC id for governed ask");
      const button = el("button", "command-receipt-open", "Propose Contract");
      button.type = "button";
      const status = el("small", "governed-ask-status", "");
      button.addEventListener("click", async () => {
        const ascId = input.value.trim().toUpperCase();
        if (!/^ASC-\d{4}$/.test(ascId)) {
          status.textContent = "Use ASC-0000 format";
          input.focus();
          return;
        }
        button.disabled = true;
        status.textContent = "Creating proposed contract";
        try {
          const response = await fetch("/api/materialize_ask_contract", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              ask_receipt: ask.receipt,
              asc_id: ascId,
              confirm: true,
            }),
          });
          const payload = await response.json();
          if (!response.ok || !payload.ok) {
            status.textContent = payload.reason || "Contract proposal blocked";
            return;
          }
          const materialization = payload.materialization || {};
          status.textContent = `Proposed ${text(materialization.contract_path, ascId)}`;
        } catch (_error) {
          status.textContent = "Materialization API unavailable";
        } finally {
          button.disabled = false;
        }
      });
      materialize.append(input, button, status);
      actions.append(materialize);
    }
    if (actions.children.length) card.append(actions);
    return card;
  }

  function renderOfflineUserCard(packet) {
    const card = el("div", "command-receipt-row offline-user-row");
    const draftItem = packet.memory_draft_source && packet.memory_draft_id
      ? { source_artifact: packet.memory_draft_source, draft_id: packet.memory_draft_id }
      : null;
    const head = el("div", "command-receipt-row-head");
    head.append(el("strong", "", "Offline User Agent"), pill(text(packet.packet_type, "frontier"), packet.status || "draft"));
    const title = el("span", "command-receipt-path", text(packet.title, packet.path));
    title.title = text(packet.title, packet.path);
    const facts = el("div", "governed-ask-facts offline-user-facts");
    [
      ["contract", packet.contract_id],
      ["next", packet.next_action],
      ["boundary", packet.privacy_boundary || packet.stop_condition || packet.next_question],
    ].filter((row) => row[1]).forEach(([label, value]) => {
      const chip = el("span", "", `${label}: ${value}`);
      chip.title = value;
      facts.append(chip);
    });
    const actions = el("div", "governed-ask-actions offline-user-actions");
    const open = artifactPreviewControl(packet.path, "command-receipt-open");
    if (open) actions.append(open);
    if (draftItem) {
      const queued = packet.memory_review_state && packet.memory_review_state !== "operator_review_required";
      const canRereview = packet.memory_review_result === "needs_more_evidence" && Number(packet.evidence_count || 0) > 0;
      const review = el("button", "command-receipt-open offline-user-review", canRereview ? "Request Re-review" : (queued ? "Review Queued" : "Request Review"));
      review.type = "button";
      review.disabled = Boolean(queued && !canRereview);
      const reviewStatus = el("small", "offline-user-review-status", packet.memory_review_result || packet.memory_review_state || "MemoryOS draft");
      review.addEventListener("click", () => requestMemoryDraftReview(draftItem, reviewStatus, review));
      actions.append(review, reviewStatus);
    }
    const prepare = el("button", "command-receipt-open", "Prepare Observation");
    prepare.type = "button";
    prepare.addEventListener("click", () => {
      const prompt = [
        "이 offline-user-agent packet을 읽고, user@offline에게 요청할 관찰을 더 안전하고 작게 다듬어줘.",
        `packet=${packet.path}`,
        `type=${text(packet.packet_type)}`,
        `title=${text(packet.title)}`,
        `privacy_boundary=${text(packet.privacy_boundary, "private/raw data must stay offline")}`,
      ].join("\n");
      focusInlineChat(prompt, "Offline observation prompt prepared");
    });
    actions.append(prepare);
    card.append(head, title, facts, actions);
    if (draftItem && packet.memory_review_result === "needs_more_evidence") {
      const evidence = el("div", "memory-draft-evidence-form offline-user-evidence-form");
      if (packet.evidence_count) {
        evidence.append(el(
          "small",
          "memory-draft-evidence-summary",
          `${Number(packet.evidence_count)} evidence item${Number(packet.evidence_count) === 1 ? "" : "s"} · ${text(packet.latest_evidence_note || packet.latest_evidence_artifact, "latest evidence")}`
        ));
      }
      const note = document.createElement("textarea");
      note.placeholder = "Operator evidence note";
      note.rows = 2;
      note.setAttribute("aria-label", "Offline user memory evidence note");
      const artifact = document.createElement("input");
      artifact.type = "text";
      artifact.placeholder = ".aios/... or docs/...";
      artifact.setAttribute("aria-label", "Offline user memory evidence artifact");
      const evidenceButton = el("button", "memory-draft-evidence-button", "Add Evidence");
      evidenceButton.type = "button";
      const evidenceStatus = el("small", "memory-draft-evidence-status", "");
      evidenceButton.addEventListener("click", () => recordMemoryReviewEvidence(draftItem, evidenceStatus, evidenceButton, note, artifact));
      evidence.append(note, artifact, evidenceButton, evidenceStatus);
      card.append(evidence);
    }
    return card;
  }

  function renderOsLiveLoop(data) {
    const target = qs("os-live-loop");
    if (!target) return;
    const observatory = data.os_observatory || {};
    const memory = observatory.memory || {};
    const capability = observatory.capability || {};
    const genesis = observatory.genesis || {};
    const hive = observatory.hive || {};
    const monitor = data.monitor || {};
    const chair = ((data.installation || {}).gate_chair) || {};
    const centerState = chair.demoted ? "fallback" : text(chair.effective_mode || chair.mode, "chair");
    const nodes = [
      {
        key: "memory",
        title: "MemoryOS",
        status: text(memory.status, "retrieving"),
        detail: `${number(memory.accepted || 0)} memories · ${number(memory.retrieval_traces_with_selected || memory.retrieval_traces || 0)} traces`,
      },
      {
        key: "capability",
        title: "Capability",
        status: text(capability.status, "routing"),
        detail: `${number(capability.capability_cards || 0)} routes · tools`,
      },
      {
        key: "genesis",
        title: "GenesisOS",
        status: text(genesis.status, "challenging"),
        detail: `${number(genesis.branches || 0)} branches`,
      },
      {
        key: "myworld",
        title: "MyWorld",
        status: text(monitor.health, "watching"),
        detail: `${number(((monitor.watched || {}).contracts) || (data.contracts || {}).total || 0)} contracts`,
      },
    ];
    const surface = el("div", "os-live-loop-surface");
    const center = el("div", `os-live-loop-center ${String(centerState).toLowerCase().replace(/[^a-z0-9_-]+/g, "-")}`);
    center.append(el("span", "", "Hive Mind"), el("strong", "", text(hive.status, centerState)), el("small", "", text(hive.next_action || chair.effective_mode || "executor loop")));
    surface.append(center);
    nodes.forEach((node, index) => {
      const card = el("div", `os-live-loop-node ${node.key} ${String(node.status).toLowerCase().replace(/[^a-z0-9_-]+/g, "-")}`);
      card.append(el("i", "", String(index + 1)), el("strong", "", node.title), el("span", "", node.status), el("small", "", node.detail));
      surface.append(card);
    });
    const footer = el("div", "os-live-loop-footer");
    footer.append(
      pill(text(monitor.health, "clear"), monitor.health),
      el("span", "", `Gate chair: ${centerState}`),
      el("span", "", `${number((data.dispatches || {}).total || 0)} dispatches`)
    );
    target.replaceChildren(surface, footer);
  }

  function renderIntentLens(data) {
    const lens = qs("intent-lens");
    if (!lens) return;
    const actions = (data.next_actions || []).slice(0, 2);
    const monitorHealth = text((data.monitor || {}).health, "unknown");
    const active = ((data.goals || {}).active || {});
    const evolution = ((data.goals || {}).evolution || {});
    const memory = (((data.os_observatory || {}).memory) || {});
    const capability = (((data.os_observatory || {}).capability) || {});
    const firstAction = actions[0] || {
      action: "continue_conversation",
      owner: "AIOS",
      reason: "No explicit blocker found in the current snapshot.",
      severity: monitorHealth === "clear" ? "clear" : "review",
    };
    const cues = [
      {
        label: "Intent",
        value: text(evolution.recommendation || active.slug, "continue AIOS work"),
        detail: text(firstAction.reason, "AIOS is ready to continue."),
      },
      {
        label: "Next owner",
        value: text(firstAction.owner, "AIOS"),
        detail: text(firstAction.action, "continue_conversation").replace(/_/g, " "),
      },
      {
        label: "Context",
        value: `${number(memory.retrieval_traces_with_selected || 0)} memory traces`,
        detail: `${number(capability.capability_cards || 0)} capability routes available`,
      },
    ];
    lens.replaceChildren(
      ...cues.map((cue) => {
        const card = el("article", "intent-lens-card");
        card.append(el("span", "", cue.label), el("strong", "", cue.value), el("small", "", cue.detail));
        return card;
      })
    );
  }

  function renderAnticipatorySurface(data) {
    const surface = qs("anticipatory-surface");
    if (!surface) return;
    const monitor = data.monitor || {};
    const contracts = ((data.contracts || {}).latest || []);
    const dispatches = ((data.dispatches || {}).latest || []);
    const latestAsk = (((data.asks || {}).latest || [])[0]) || {};
    const openContract = contracts.find((item) => ["accepted", "proposed"].includes(text(item.status, "").toLowerCase())) || {};
    const latestDispatch = dispatches[0] || {};
    const nextAction = ((data.next_actions || [])[0]) || {};
    const active = ((data.goals || {}).active || {});
    const genesis = ((data.genesis_lens || {}).worldline_preview || {});
    const genesisBranches = (genesis.nodes || []).filter((node) => node.type === "branch");
    const predictedOwner = text(
      nextAction.owner || (openContract.id ? "myworld" : "") || latestDispatch.repo || latestAsk.next_owner || "AIOS"
    );
    const predictedAction = text(
      nextAction.action
        || (openContract.id ? `review ${openContract.id}` : "")
        || latestAsk.next_action
        || latestDispatch.reason
        || "continue_conversation"
    ).replace(/_/g, " ");
    const why = text(
      nextAction.reason
        || openContract.goal
        || latestAsk.goal
        || latestDispatch.goal
        || "AIOS has no blocking stop condition; the next step is to keep the loop inspectable."
    );
    const health = text(monitor.health, "unknown");
    const branchHint = genesisBranches[0]
      ? text(genesisBranches[0].detail || genesisBranches[0].label, "")
      : "GenesisOS strongest discomfort: reactive passivity";
    const prompt = [
      "AIOS가 operator가 아무것도 하지 않을 때 다음에 해야 할 일을 제안해줘.",
      `predicted_owner=${predictedOwner}`,
      `predicted_action=${predictedAction}`,
      `why=${why}`,
      `health=${health}`,
      "실행하지 말고 MemoryOS/CapabilityOS/GenesisOS/Hive 증거와 stop condition을 먼저 보여줘.",
    ].join("\n");
    const goal = [
      "Turn the AIOS anticipatory surface into the next governed work item.",
      `Current predicted owner: ${predictedOwner}.`,
      `Current predicted action: ${predictedAction}.`,
      `Reason: ${why}.`,
      "Keep it audit-visible and do not execute hidden child-repo work.",
    ].join(" ");
    const header = el("div", "anticipatory-head");
    header.append(el("span", "", "Next If Idle"), pill(health, health));
    const body = el("div", "anticipatory-body");
    body.append(
      el("strong", "", predictedAction),
      el("p", "", why)
    );
    const facts = el("div", "anticipatory-facts");
    [
      ["owner", predictedOwner],
      ["source", text(openContract.id || latestAsk.ask_id || latestDispatch.dispatch_id || active.slug, "live snapshot")],
      ["genesis", branchHint],
    ].forEach(([label, value]) => {
      const chip = el("span", "", `${label}: ${value}`);
      chip.title = value;
      facts.append(chip);
    });
    const actions = el("div", "anticipatory-actions");
    actions.append(
      chatPromptButton("Explain", prompt, "anticipatory-action"),
      askActionButton("Govern", goal, "anticipatory-action primary")
    );
    surface.replaceChildren(header, body, facts, actions);
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
    const qualityCounts = contracts.quality_counts || {};
    const weakCount = Number(qualityCounts.weak_proposed || 0);
    qs("contract-total").textContent = weakCount ? `${contracts.total || 0} total · ${weakCount} revise` : `${contracts.total || 0} total`;
    qs("contract-flow").replaceChildren(
      ...(contracts.latest || []).slice(0, 8).map((row) => {
        const item = el("div", "flow-row");
        const qualityState = text(row.quality_state, row.status);
        if (qualityState === "weak_proposed") item.classList.add("contract-weak");
        const detail = el("div", "contract-quality");
        detail.append(pill(qualityState === "weak_proposed" ? "Revise" : qualityState, qualityState === "weak_proposed" ? "held" : row.status));
        if ((row.quality_warnings || []).length) {
          detail.append(el("span", "", row.quality_warnings.slice(0, 2).join(" · ")));
        } else {
          detail.append(el("span", "", text(row.review_action || row.status)));
        }
        if (qualityState === "weak_proposed" && row.path) {
          const action = el("div", "contract-review-action");
          const confirm = el("label", "contract-review-confirm");
          const checkbox = document.createElement("input");
          checkbox.type = "checkbox";
          confirm.append(checkbox, el("span", "", "reviewed"));
          const button = el("button", "contract-supersede-button", "Supersede");
          button.type = "button";
          const status = el("small", "contract-review-status", "");
          button.addEventListener("click", async () => {
            if (!checkbox.checked) {
              status.textContent = "Review confirmation required";
              checkbox.focus();
              return;
            }
            button.disabled = true;
            status.textContent = "Superseding";
            try {
              const response = await fetch("/api/contract_review_action", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  contract_path: row.path,
                  action: "mark_superseded",
                  reason: (row.quality_warnings || []).join(", ") || "weak proposed contract",
                  confirm: true,
                }),
              });
              const payload = await response.json();
              if (!response.ok || !payload.ok) {
                status.textContent = payload.reason || "Review action blocked";
                return;
              }
              status.textContent = "Superseded; refresh snapshot";
            } catch (_error) {
              status.textContent = "Review API unavailable";
            } finally {
              button.disabled = false;
            }
          });
          action.append(confirm, button, status);
          detail.append(action);
        }
        item.append(
          pill(text(row.id), row.status),
          el("strong", "", text(row.slug)),
          detail
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
        const memoryContext = row.memory_context || {};
        item.append(
          el("strong", "", text(row.dispatch_id)),
          el("span", "", text(row.goal || row.contract_id)),
          pill(text(row.status), row.status),
          el("span", "", `sent ${row.sent.length} / collected ${row.collected.length}`)
        );
        if (memoryContext.retrieval_trace) {
          item.append(el("span", "dispatch-memory-trace", `MemoryOS ${memoryContext.retrieval_trace} · signal ${text(memoryContext.signal_coverage)}`));
        }
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

  function renderRoster(data) {
    const roster = data.roster || {};
    const agents = roster.agents || [];
    const summary = qs("roster-summary");
    if (summary) {
      const blocked = Number(roster.blocked_count || 0);
      const needs = Number(roster.needs_input_count || 0);
      summary.textContent = `${agents.length} agents`
        + (blocked ? ` · ${blocked} blocked` : "")
        + (needs ? ` · ${needs} need input` : "");
    }
    const list = qs("roster-list");
    if (!list) return;
    list.replaceChildren(
      ...agents.map((agent) => {
        const event = String(agent.event || "idle");
        const card = el("div", `roster-card ${event}`);
        const head = el("div", "roster-card-head");
        head.append(el("strong", "", text(agent.agent)), pill(event, event));
        card.append(head, el("span", "roster-repo", text(agent.repo)),
          el("span", "roster-digest", text(agent.status_digest)));
        return card;
      })
    );
  }

  function renderContractBoard(data) {
    const board = data.contract_board || {};
    const columns = board.columns || {};
    const order = board.column_order || [];
    const counts = board.counts || {};
    const summary = qs("contract-board-summary");
    if (summary) {
      summary.textContent = order.map((col) => `${col} ${counts[col] || 0}`).join(" · ");
    }
    const root = qs("contract-board");
    if (!root) return;
    root.replaceChildren(
      ...order.map((columnName) => {
        const column = el("div", `board-column ${columnName}`);
        const head = el("div", "board-column-head");
        head.append(el("strong", "", columnName), el("span", "", String(counts[columnName] || 0)));
        column.append(head);
        const cards = columns[columnName] || [];
        cards.slice(0, 12).forEach((card) => {
          const item = el("div", "board-card");
          item.append(el("strong", "", text(card.contract_id)),
            el("span", "board-card-title", text(card.title)));
          column.append(item);
        });
        if (cards.length > 12) {
          column.append(el("span", "board-card-more", `+${cards.length - 12} more`));
        }
        return column;
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
    const chairRecovery = chair.recovery_proof || {};
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
        state: chair.demoted ? "held" : chair.enabled ? chair.state || "internal" : "held",
        value: chair.enabled ? text(chair.effective_mode || chair.mode, "internal") : "disabled",
        detail: chair.demoted
          ? `demoted from ${text(chair.configured_mode, "runtime")} · ${text((chair.demotion || {}).failure_count, "0")} failure(s)`
          : chairRecovery.recovery_ref
            ? `recovered from ${text(chair.configured_mode, "runtime")} · ${text(chairRecovery.superseded_failure_count, "0")} superseded failure(s)`
          : (chair.latest_turn && chair.latest_turn.status) ? `${chair.latest_turn.status} · ${text(chair.detail)}` : text(chair.detail, "gate pack required"),
      },
    ];
    function runtimeMap(preview) {
      const nodes = (preview.nodes || []).slice(0, 12);
      const edges = (preview.edges || []).slice(0, 18);
      const card = el("article", "runtime-flow-card");
      const head = el("div", "runtime-flow-head");
      head.append(el("strong", "", "Gate Runtime Map"), el("span", "", "configured -> effective -> latest turn"));
      const surface = el("div", "runtime-flow-surface");
      const nodeIds = new Set(nodes.map((node) => node.id));
      edges.filter((edge) => nodeIds.has(edge.from) && nodeIds.has(edge.to)).forEach((edge) => {
        const fromNode = nodes.find((node) => node.id === edge.from);
        const toNode = nodes.find((node) => node.id === edge.to);
        if (!fromNode || !toNode) return;
        const x1 = Number(fromNode.x || 0);
        const y1 = Number(fromNode.y || 0);
        const x2 = Number(toNode.x || 0);
        const y2 = Number(toNode.y || 0);
        const line = el("i", `runtime-flow-edge ${text(edge.kind, "link")}`);
        const dx = x2 - x1;
        const dy = y2 - y1;
        line.style.left = `${x1}%`;
        line.style.top = `${y1}%`;
        line.style.width = `${Math.max(8, Math.hypot(dx, dy))}%`;
        line.style.transform = `rotate(${Math.atan2(dy, dx)}rad)`;
        surface.append(line);
      });
      nodes.forEach((node) => {
        const nodeEl = el("div", `runtime-flow-node ${text(node.type, "node")} ${text(node.state, "")}`);
        nodeEl.style.left = `${Number(node.x || 0)}%`;
        nodeEl.style.top = `${Number(node.y || 0)}%`;
        nodeEl.title = text(node.detail || node.label);
        nodeEl.append(el("strong", "", text(node.label, node.type)), el("span", "", text(node.type)));
        surface.append(nodeEl);
      });
      if (!nodes.length) {
        surface.append(el("div", "runtime-flow-empty", "No Gate Chair runtime evidence found."));
      }
      card.append(head, surface);
      return card;
    }
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
    const matrixStatus = el("small", "runtime-probe-status");
    const matrixButton = el("button", "runtime-probe-button", "Compare Chairs");
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
    matrixButton.type = "button";
    matrixButton.addEventListener("click", async () => {
      matrixStatus.textContent = "Comparing";
      evalReport.replaceChildren();
      matrixButton.disabled = true;
      try {
        const response = await fetch("/api/gate_chair_eval", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            candidate_matrix: true,
            candidates: ["claude", "codex"],
            request_memory_review: true,
            prompts: ["AIOS에는 gate 역할의 Agent가 있나? 아니면 시스템 답변밖에 못하나?"],
          }),
        });
        const payload = await response.json();
        if (!response.ok || !payload.ok) {
          matrixStatus.textContent = payload.reason || "Compare failed";
          return;
        }
        const baseline = payload.baseline || {};
        const best = payload.best_candidate || {};
        const readiness = payload.promotion_ready ? "promotion ready" : "hold";
        matrixStatus.textContent = `${readiness} · ${payload.recommendation || "observed"} · baseline ${text(baseline.average_score, "-")} · best ${text(best.mode, "-")} ${text(best.average_score, "-")}`;
        const candidates = Array.isArray(payload.candidates) ? payload.candidates : [];
        if (candidates.length) {
          const list = el("div", "runtime-candidate-list");
          candidates.slice(0, 4).forEach((candidate) => {
            const row = el("small", "runtime-eval-reason");
            const failureCount = candidate.failure_count === undefined ? "-" : String(candidate.failure_count);
            const external = candidate.external_runtime_observed ? "external" : "internal";
            row.textContent = `${text(candidate.mode, "candidate")} · score ${text(candidate.average_score, "-")} · failures ${failureCount} · ${external}`;
            list.append(row);
          });
          evalReport.append(list);
        }
        const report = artifactPreviewControl(payload.report_path, "runtime-eval-open");
        if (report) evalReport.append(report);
      } catch (_error) {
        matrixStatus.textContent = "Compare API unavailable";
      } finally {
        matrixButton.disabled = false;
      }
    });
    const commandRow = el("div", "runtime-command-row");
    (install.commands || ["aios install", "aios open", "aios status --json", "aios stop"]).forEach((cmd) => {
      commandRow.append(el("code", "", cmd));
    });
    if (chairRecovery.recovery_ref) {
      const recovery = artifactPreviewControl(chairRecovery.recovery_ref, "runtime-eval-open");
      if (recovery) {
        const recoveryWrap = el("div", "runtime-eval-report");
        recoveryWrap.append(
          el("small", "runtime-eval-reason", `Recovery proof · current ${text(chairRecovery.recovery_current_score, "-")} / internal ${text(chairRecovery.recovery_internal_score, "-")}`),
          recovery
        );
        commandRow.append(recoveryWrap);
      }
    }
    commandRow.append(probeButton, probeStatus, evalButton, evalStatus, matrixButton, matrixStatus, internalButton, ollamaButton, claudeButton, codexButton, geminiButton, runtimeStatus, evalReport);
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
      runtimeMap(chair.runtime_preview || {}),
      commandRow
    );
  }

  function completionBlockers(data) {
    const blockers = [];
    const monitor = data.monitor || {};
    const findings = Array.isArray(monitor.findings) ? monitor.findings : [];
    findings.forEach((finding) => {
      const severity = text(finding.severity || finding.status || finding.type, "attention");
      const message = text(finding.message || finding.reason || finding.check || finding.id, "");
      if (message) {
        blockers.push({
          severity,
          owner: text(finding.owner || finding.code, "monitor"),
          message,
          action: text(finding.action, "review"),
        });
      }
    });
    ((data.repos || {}).items || []).forEach((repo) => {
      if (repo.dirty) {
        blockers.push({
          severity: "medium",
          owner: text(repo.repo),
          message: "unreviewed local changes",
          action: "hold_for_repo_owner_triage",
        });
      }
    });
    if (monitor.health && !["clear", "passed", "healthy"].includes(String(monitor.health).toLowerCase())) {
      blockers.unshift({
        severity: "medium",
        owner: "myworld",
        message: `monitor health is ${monitor.health}`,
        action: "review_monitor_findings",
      });
    }
    const seen = new Set();
    return blockers.filter((blocker) => {
      const key = `${blocker.severity}:${blocker.owner}:${blocker.message}:${blocker.action}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    }).slice(0, 6);
  }

  function renderCompletion(data) {
    const c = data.completion || {};
    const crits = c.criteria || [];
    const blockers = completionBlockers(data);
    const verdict = qs("completion-verdict");
    if (verdict) {
      verdict.textContent = blockers.length
        ? "AIOS readiness audit — attention needed"
        : "AIOS readiness audit — no active blockers";
    }
    const status = qs("completion-status");
    if (status) {
      const criteriaStatus = text(c.criteria_met, "criteria checking");
      status.textContent = blockers.length ? `${criteriaStatus} · ${blockers.length} review(s)` : criteriaStatus;
      status.className = "live-status";
    }
    const grid = qs("completion-grid");
    if (!grid) return;
    const cards = [];
    if (blockers.length) {
      const blockerCard = el("article", "runtime-card held readiness-blocker-card");
      const blockerList = el("div", "readiness-blocker-list");
      blockers.forEach((blocker) => {
        const row = el("div", `readiness-blocker-row ${String(blocker.severity).toLowerCase()}`);
        row.append(
          pill(text(blocker.severity, "review"), blocker.severity),
          el("strong", "", text(blocker.owner, "owner")),
          el("span", "", text(blocker.message, "review required")),
          el("small", "", text(blocker.action, "review"))
        );
        blockerList.append(row);
      });
      blockerCard.append(
        pill("hold", "held"),
        el("strong", "", "Do not declare complete yet"),
        blockerList
      );
      cards.push(blockerCard);
    }
    if (!crits.length && !cards.length) {
      grid.replaceChildren(el("article", "runtime-card", "readiness check unavailable"));
      return;
    }
    cards.push(
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
    grid.replaceChildren(...cards);
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
          ["contract", item.materialized_contract],
          ["materialization", item.materialization_receipt],
          ["dispatch", item.dispatch_preview],
          ["next", item.next_action],
        ].filter((row) => row[1]);
        const rowList = el("div", "promotion-queue-rows");
        rowList.append(
          ...rows.map(([label, value]) => {
            const row = el("div", "promotion-queue-row");
            if (label === "next") row.classList.add("promotion-next-row");
            const valueNode = el("span", "", value);
            valueNode.title = value;
            row.append(el("strong", "", label), valueNode);
            return row;
          })
        );
        card.append(
          pill(text(item.status, "promotion"), item.status),
          el("strong", "", text(item.goal || item.promotion_id, "promotion")),
          el("small", "", text(item.created_at, "created")),
          rowList
        );
        if (item.quality_state && item.quality_state !== "actionable") {
          const quality = el("div", `promotion-quality ${String(item.quality_state).replace(/[^a-z0-9_-]+/gi, "-")}`);
          quality.append(
            pill(text(item.quality_state), item.quality_state),
            el("span", "", text(item.quality_reason, "review before materialization"))
          );
          if (item.quality_evidence) {
            quality.append(el("small", "", text(item.quality_evidence)));
          }
          card.append(quality);
        }
        if (item.materialized_contract) {
          card.append(artifactPreviewControl(item.materialized_contract, "promotion-contract-open"));
        } else if (item.contract_seed && item.receipt && !["solved_by_later_receipt", "mitigated_by_visual_focus"].includes(item.quality_state)) {
          const controls = el("div", "promotion-materialize");
          const input = document.createElement("input");
          const suggestedAsc = text(item.next_contract_id || promotions.next_contract_id, "ASC-0000");
          input.type = "text";
          input.placeholder = suggestedAsc;
          input.value = suggestedAsc;
          input.setAttribute("aria-label", "ASC id");
          const button = el("button", "promotion-materialize-button", "Create Contract");
          button.type = "button";
          const materializeStatus = el("small", "promotion-materialize-status", "");
          button.addEventListener("click", async () => {
            const ascId = input.value.trim().toUpperCase();
            if (!/^ASC-\d{4}$/.test(ascId)) {
              materializeStatus.textContent = "Use ASC-0000 format";
              input.focus();
              return;
            }
            button.disabled = true;
            materializeStatus.textContent = "Creating proposed contract";
            try {
              const response = await fetch("/api/materialize_promotion_contract", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  promotion_receipt: item.receipt,
                  asc_id: ascId,
                  confirm: true,
                }),
              });
              const payload = await response.json();
              if (!response.ok || !payload.ok) {
                materializeStatus.textContent = payload.reason || "Contract creation blocked";
                return;
              }
              const materialization = payload.materialization || {};
              materializeStatus.textContent = `Proposed ${text(materialization.contract_path, ascId)}`;
            } catch (_error) {
              materializeStatus.textContent = "Materialization API unavailable";
            } finally {
              button.disabled = false;
            }
          });
          controls.append(input, button, materializeStatus);
          card.append(controls);
        } else if (["solved_by_later_receipt", "mitigated_by_visual_focus"].includes(item.quality_state)) {
          card.append(el("small", "promotion-materialize-held", "No ASC needed unless reopened."));
        }
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

  async function recordMemoryReviewEvidence(item, status, button, noteInput, artifactInput) {
    const note = noteInput.value.trim();
    const evidenceArtifact = artifactInput.value.trim();
    if (!note && !evidenceArtifact) {
      status.textContent = "Add a note or artifact path";
      noteInput.focus();
      return;
    }
    button.disabled = true;
    status.textContent = "Recording evidence";
    try {
      const response = await fetch("/api/memory_review_evidence", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source_artifact: item.source_artifact,
          draft_id: item.draft_id,
          note,
          evidence_artifact: evidenceArtifact,
          confirm: true,
        }),
      });
      const payload = await response.json();
      if (!response.ok || !payload.ok) {
        status.textContent = payload.reason || "Evidence blocked";
        return;
      }
      const receipt = payload.receipt || {};
      status.textContent = `Evidence recorded ${text(receipt.evidence_id, "")}`;
      noteInput.value = "";
      artifactInput.value = "";
    } catch (_error) {
      status.textContent = "Evidence API unavailable";
    } finally {
      button.disabled = false;
    }
  }

  function renderMemoryLibrary(data) {
    const memory = ((data.os_observatory || {}).memory) || {};
    const status = qs("memory-library-status");
    const grid = qs("memory-library-grid");
    if (!grid) return;

    const accepted = Number(memory.accepted || 0);
    const draft = Number(memory.draft || 0);
    const rejected = Number(memory.rejected || 0);
    const traces = Number(memory.retrieval_traces || 0);
    const selected = Number(memory.retrieval_traces_with_selected || 0);
    const selectivity = traces ? (selected / traces) * 100 : 0;
    const nodes = Number(memory.nodes || 0);
    const edges = Number(memory.edges || 0);
    const provenanceDensity = nodes ? (edges / nodes) : 0;
    const reviewTotal = accepted + draft + rejected;
    const acceptanceShare = reviewTotal ? (accepted / reviewTotal) * 100 : 0;
    const hyperedges = Number(memory.hyperedges || 0);
    const sources = Number(memory.sources || 0);
    const latestInvocation = (((data.invocations || {}).latest || [])[0]) || {};
    const latestPreviews = latestInvocation.artifact_previews || {};
    const memoryContext = latestPreviews.memory_context_pack || {};
    const memoryRequest = latestPreviews.memory_request || {};
    const recentTraces = memory.recent_traces || [];
    const graphControl = memory.graph_control || {};
    const latestGraphControl = graphControl.latest || {};
    const selectedIdMatch = String(memoryContext.preview || "").match(/selected_memory_ids:\s*\[([^\]]+)/);
    const latestSelectedIds = selectedIdMatch ? selectedIdMatch[1].split(",").map((item) => item.replace(/["\s]/g, "")).filter(Boolean) : [];
    const traceMatch = String(memoryContext.preview || "").match(/trace_id:\s*([a-zA-Z0-9_-]+)/);
    const latestTraceId = traceMatch ? traceMatch[1] : "";

    if (status) {
      status.textContent = `${number(memory.memory_objects)} objects · ${number(traces)} traces`;
    }

    if (!memory.status && !memory.memory_objects && !nodes) {
      const empty = el("article", "memory-library-card empty");
      empty.append(
        pill("MemoryOS", "held"),
        el("strong", "", "MemoryOS evidence unavailable"),
        el("span", "", "Run a snapshot refresh after MemoryOS emits graph, review, and retrieval data.")
      );
      grid.replaceChildren(empty);
      return;
    }

    function gauge(label, value, detail, statusName) {
      const percent = clampPercent(value);
      const card = el("article", `memory-library-card ${statusName || ""}`);
      const track = el("div", "memory-library-meter");
      const fill = el("i");
      fill.style.width = `${Math.max(4, percent)}%`;
      track.append(fill);
      card.append(
        pill(label, statusName || memory.status),
        el("strong", "", `${Math.round(percent)}%`),
        track,
        el("span", "", detail)
      );
      return card;
    }

    function graphMap(preview) {
      const map = el("div", "memory-graph-map");
      const graphPreview = preview || {};
      const previewNodes = graphPreview.nodes || [];
      const previewEdges = graphPreview.edges || [];
      if (previewNodes.length) {
        const byId = new Map(previewNodes.map((node) => [text(node.id, ""), node]));
        previewEdges.forEach((edge) => {
          const start = byId.get(text(edge.from, ""));
          const end = byId.get(text(edge.to, ""));
          if (!start || !end) return;
          const line = el("b", `memory-graph-edge ${text(edge.kind, "edge")}`);
          const dx = Number(end.x || 0) - Number(start.x || 0);
          const dy = Number(end.y || 0) - Number(start.y || 0);
          line.style.left = `${Number(start.x || 0)}%`;
          line.style.top = `${Number(start.y || 0)}%`;
          line.style.width = `${Math.max(8, Math.hypot(dx, dy))}%`;
          line.style.transform = `rotate(${Math.atan2(dy, dx) * 180 / Math.PI}deg)`;
          map.append(line);
        });
        previewNodes.forEach((item) => {
          const node = el("div", `memory-graph-node ${text(item.type, "memory")} ${text(item.status, "")}`);
          node.style.left = `${Number(item.x || 50)}%`;
          node.style.top = `${Number(item.y || 50)}%`;
          node.title = [item.label, item.detail].filter(Boolean).join(" - ");
          node.append(el("span", "", text(item.label, "node")));
          map.append(node);
        });
        return map;
      }
      const positions = [
        [12, 20], [24, 42], [19, 68], [36, 27], [44, 56], [38, 78],
        [56, 20], [63, 44], [58, 70], [76, 28], [83, 56], [72, 78],
        [31, 14], [49, 38], [68, 15], [87, 34], [15, 50], [52, 86],
      ];
      positions.forEach(([x, y], index) => {
        const node = el("div", `memory-graph-node memory ${index % 5 === 0 ? "accepted" : index % 4 === 0 ? "draft" : index % 7 === 0 ? "source" : ""}`);
        node.style.left = `${x}%`;
        node.style.top = `${y}%`;
        map.append(node);
      });
      [[0, 4, 26], [1, 5, -18], [3, 7, 14], [6, 10, 28], [8, 11, -24], [12, 14, 9], [4, 13, -35], [7, 15, 18], [16, 2, 44], [9, 10, -12]].forEach(([from, to, rotate]) => {
        const start = positions[from];
        const end = positions[to];
        const line = el("b", "memory-graph-edge");
        const dx = end[0] - start[0];
        const dy = end[1] - start[1];
        line.style.left = `${start[0]}%`;
        line.style.top = `${start[1]}%`;
        line.style.width = `${Math.max(14, Math.hypot(dx, dy) * 2.2)}%`;
        line.style.transform = `rotate(${rotate}deg)`;
        map.append(line);
      });
      return map;
    }

    const summary = el("article", "memory-library-card summary");
    const reviewStrip = el("div", "memory-library-strip");
    reviewStrip.append(
      el("span", "", `${number(accepted)} accepted`),
      el("span", "", `${number(draft)} draft`),
      el("span", "", `${number(rejected)} rejected`)
    );
    summary.append(
      pill("MemoryOS", memory.status),
      el("strong", "", text(memory.headline, "Memory graph waiting")),
      reviewStrip,
      el("small", "", `latest review ${text(memory.latest_review_at, "not recorded")}`)
    );

    const userBoard = el("article", "memory-library-card user-board");
    const reviewDebt = draft + rejected;
    const retrievalReady = selectivity > 0 ? "retrieval ready" : "retrieval weak";
    const graphState = latestGraphControl.status === "budget_exhausted" ? "graph budget held" : text(latestGraphControl.status, "graph pending");
    const userMetrics = el("div", "os-product-metrics");
    userMetrics.append(
      metric("usable memories", accepted, ""),
      metric("review debt", reviewDebt, ""),
      metric("retrieval traces", traces, ""),
      metric("graph edges", edges, "")
    );
    const userActions = el("div", "os-product-actions");
    userActions.append(
      askActionButton("Ask Memory", `MemoryOS 상태를 사용자 관점으로 설명해줘. accepted=${number(accepted)}, draft=${number(draft)}, rejected=${number(rejected)}, traces=${number(traces)}, selected=${number(selected)}, latest_graph_status=${graphState}. 지금 내가 어떤 기억을 믿고 써도 되는지, 어떤 기억은 review가 필요한지 알려줘.`),
      askActionButton("Find Missing", "MemoryOS가 아직 놓치고 있는 founder 작업방식/실패기억/프로젝트 맥락을 찾아서 다음 memory draft 후보로 정리해줘.")
    );
    userBoard.append(
      pill("MemoryOS", retrievalReady),
      el("strong", "", "What AIOS can remember for you"),
      el("span", "", `${number(accepted)} accepted memories are usable now; ${number(reviewDebt)} memory items still need review before they become trusted context.`),
      userMetrics,
      el("small", "", `${retrievalReady} · ${graphState} · ${provenanceDensity.toFixed(2)} links/node`),
      userActions
    );

    const graph = el("article", "memory-library-card graph map");
    const graphMetrics = el("div", "memory-library-metrics");
    graphMetrics.append(
      metric("graph nodes", nodes, ""),
      metric("provenance edges", edges, ""),
      metric("sources", sources, ""),
      metric("hyperedges", hyperedges, "")
    );
    graph.append(
      pill("Hypergraph", hyperedges ? "active" : "held"),
      el("strong", "", `${number(nodes)} nodes mapped`),
      graphMap(memory.graph_preview),
      graphMetrics,
      el("span", "", `${provenanceDensity.toFixed(2)} provenance links per graph node`)
    );

    const graphControlCard = el("article", "memory-library-card graph-control");
    const gcStops = latestGraphControl.stop_conditions || [];
    const gcStatus = text(latestGraphControl.status, "waiting");
    const gcRatio = latestGraphControl.bound_ratio === undefined || latestGraphControl.bound_ratio === null
      ? "n/a"
      : Number(latestGraphControl.bound_ratio || 0).toFixed(2);
    const gcStrip = el("div", "memory-library-strip");
    gcStrip.append(
      el("span", "", `${number(graphControl.run_count || 0)} runs`),
      el("span", "", `ratio ${gcRatio}`),
      el("span", "", `${number(latestGraphControl.queryable_surface_count || 0)} surface`)
    );
    graphControlCard.append(
      pill("Graph Control", gcStops.length ? "held" : (latestGraphControl.id ? "active" : "waiting")),
      el("strong", "", latestGraphControl.id ? text(latestGraphControl.id, "latest graph-control run") : "No graph-control run yet"),
      gcStrip,
      el("span", "", gcStops.length ? `stop: ${gcStops.join(" · ")}` : `status: ${gcStatus}`),
      el("small", "", `${latestGraphControl.halt_auto_consolidation ? "auto-consolidation halted" : "auto-consolidation clear"} · ${text(latestGraphControl.captured_at, "capture pending")}`)
    );

    const retrieval = gauge(
      "Retrieval",
      selectivity,
      `${number(selected)} traces selected memories from ${number(traces)} retrieval runs`,
      selectivity ? "active" : "held"
    );
    if (latestTraceId || latestSelectedIds.length || memoryContext.path) {
      const traceBox = el("div", "memory-trace-box");
      traceBox.append(
        el("strong", "", latestTraceId || "latest context trace"),
        el("span", "", latestSelectedIds.length ? `${latestSelectedIds.length} selected memories · ${latestSelectedIds.slice(0, 2).join(" · ")}` : text(memoryContext.path, "context pack pending"))
      );
      const open = artifactPreviewControl(memoryContext.path, "memory-trace-open");
      if (open) traceBox.append(open);
      retrieval.append(traceBox);
    }

    const traceBoard = el("article", "memory-library-card retrieval-board");
    const traceItems = recentTraces.slice(0, 3).map((trace) => {
      const row = el("div", "memory-retrieval-row");
      const coverage = trace.signal_coverage === undefined || trace.signal_coverage === null
        ? "coverage unknown"
        : `${Math.round(Number(trace.signal_coverage || 0) * 100)}% coverage`;
      const selectedMemories = (trace.selected_memories || []).slice(0, 3).map((memoryItem) => {
        const card = el("div", "memory-selected-card");
        const confidence = memoryItem.confidence === undefined || memoryItem.confidence === null
          ? "confidence n/a"
          : `${Math.round(Number(memoryItem.confidence || 0) * 100)}% confidence`;
        card.append(
          el("strong", "", text(memoryItem.id, "memory")),
          el("span", "", text(memoryItem.content_preview, "Memory object not found")),
          el("small", "", `${text(memoryItem.status, "status")} · ${confidence} · ${text(memoryItem.evidence_state, "evidence")}`),
          el("small", "memory-selected-source", text(memoryItem.source_path || (memoryItem.raw_refs || [])[0], "provenance pending"))
        );
        return card;
      });
      row.append(
        el("strong", "", text(trace.id, "retrieval trace")),
        el("span", "", text(trace.query, "query not recorded")),
        el("small", "", `${number(trace.selected_count || 0)} selected · ${coverage} · ${text(trace.role, "role")} · ${text(trace.privacy_filter, "privacy")}`),
        ...(selectedMemories.length ? selectedMemories : [el("small", "memory-selected-empty", "No selected memories in this trace")])
      );
      return row;
    });
    traceBoard.append(
      pill("Retrieval Trace", recentTraces.length ? "active" : "held"),
      el("strong", "", recentTraces.length ? "Why MemoryOS selected context" : "No retrieval trace payload"),
      ...(traceItems.length ? traceItems : [el("span", "", "Run MemoryOS context build or an AIOS chat turn to create RetrievalTrace evidence.")])
    );

    const review = gauge(
      "Review",
      acceptanceShare,
      `${number(accepted)} accepted from ${number(reviewTotal)} reviewed or pending memory objects`,
      acceptanceShare ? "clear" : "held"
    );
    if (memoryRequest.path) {
      const requestBox = el("div", "memory-trace-box provenance");
      requestBox.append(
        el("strong", "", "Latest request"),
        el("span", "", text(memoryRequest.preview, memoryRequest.path))
      );
      const open = artifactPreviewControl(memoryRequest.path, "memory-trace-open");
      if (open) requestBox.append(open);
      review.append(requestBox);
    }

    const signals = el("article", "memory-library-card signals");
    const signalRows = (memory.signals || []).slice(0, 4).map((signal) => {
      const row = el("div", "memory-library-signal");
      row.append(el("strong", "", number(signal.value)), el("span", "", `${text(signal.label)} · ${text(signal.unit, "count")}`));
      return row;
    });
    signals.append(
      pill("Signals", "active"),
      el("strong", "", "Index health"),
      ...(signalRows.length ? signalRows : [el("span", "", "No MemoryOS signal list in snapshot")])
    );

    grid.replaceChildren(userBoard, summary, graph, graphControlCard, retrieval, traceBoard, review, signals);
  }

  function renderCapabilityRouter(data) {
    const capability = ((data.os_observatory || {}).capability) || {};
    const status = qs("capability-router-status");
    const grid = qs("capability-router-grid");
    if (!grid) return;

    const cards = Number(capability.capability_cards || 0);
    const observed = Number(capability.observed_capabilities || 0);
    const observations = Number(capability.observations || 0);
    const gaps = Number(capability.gaps || 0);
    const results = Number(capability.result_files || 0);
    const topRoutes = capability.top_routes || [];
    const sourceModes = capability.source_modes || [];
    const providerRoutes = capability.provider_routes || [];
    const gapSamples = capability.gap_samples || [];
    const webRoute = capability.web_route || {};
    const constraintRoute = capability.constraint_route || {};
    const routePreview = capability.route_preview || {};
    const coverage = cards ? (observed / cards) * 100 : 0;
    const gapPressure = cards ? (gaps / cards) * 100 : 0;
    const networkRoutes = topRoutes.filter((route) => route.requires_network).length;
    const latestInvocation = (((data.invocations || {}).latest || [])[0]) || {};
    const capabilityPreview = (latestInvocation.artifact_previews || {}).capability_route || {};

    if (status) {
      status.textContent = `${number(cards)} cards · ${number(observations)} observations`;
    }

    if (!capability.status && !cards && !topRoutes.length) {
      const empty = el("article", "capability-router-card empty");
      empty.append(
        pill("CapabilityOS", "held"),
        el("strong", "", "Capability route evidence unavailable"),
        el("span", "", "Run a snapshot refresh after CapabilityOS emits cards, observations, gaps, and routes.")
      );
      grid.replaceChildren(empty);
      return;
    }

    function meter(label, value, detail, state) {
      const percent = clampPercent(value);
      const card = el("article", `capability-router-card ${state || ""}`);
      const track = el("div", "capability-router-meter");
      const fill = el("i");
      fill.style.width = `${Math.max(4, percent)}%`;
      track.append(fill);
      card.append(
        pill(label, state || capability.status),
        el("strong", "", `${Math.round(percent)}%`),
        track,
        el("span", "", detail)
      );
      return card;
    }

    const summary = el("article", "capability-router-card summary");
    const summaryMetrics = el("div", "capability-router-metrics");
    summaryMetrics.append(
      metric("cards", cards, ""),
      metric("observations", observations, ""),
      metric("gaps", gaps, ""),
      metric("result files", results, "")
    );
    summary.append(
      pill("CapabilityOS", capability.status),
      el("strong", "", text(capability.headline, "Capability catalog waiting")),
      summaryMetrics,
      el("span", "", `${number(networkRoutes)} web/network route${networkRoutes === 1 ? "" : "s"} in current shortlist`)
    );

    const userBoard = el("article", "capability-router-card user-board");
    const bestProvider = providerRoutes[0] || {};
    const permissionCount = (constraintRoute.permission_questions || []).length;
    const sourceSummary = sourceModes.slice(0, 4).map((mode) => `${text(mode.mode, "source")}:${number(mode.count)}`).join(" · ");
    const routeRisk = gaps ? "route review needed" : "routes clear";
    const userMetrics = el("div", "os-product-metrics");
    userMetrics.append(
      metric("tool cards", cards, ""),
      metric("observations", observations, ""),
      metric("known gaps", gaps, ""),
      metric("permissions", permissionCount, "")
    );
    const userActions = el("div", "os-product-actions");
    userActions.append(
      askActionButton("Route Task", `CapabilityOS에게 지금 작업의 도구/검색/모델 route를 결정하게 해줘. cards=${number(cards)}, observations=${number(observations)}, gaps=${number(gaps)}, source_modes=${sourceSummary || "none"}, best_provider=${text(bestProvider.agent, "unknown")}. 나쁜 도구와 fallback도 함께 알려줘.`),
      askActionButton("Ask Permission", "CapabilityOS permission questions 중 지금 작업에 필요한 것만 사용자에게 물어볼 수 있게 간단한 승인 질문으로 바꿔줘.")
    );
    userBoard.append(
      pill("CapabilityOS", routeRisk),
      el("strong", "", "How AIOS chooses tools and providers"),
      el("span", "", `${number(cards)} tool cards and ${number(observations)} observations guide route choice; ${number(gaps)} known gaps should be avoided or resolved before execution.`),
      userMetrics,
      el("small", "", `${sourceSummary || "source modes pending"} · fallback: ${text(bestProvider.agent, "not selected")}`),
      userActions
    );

    const coverageCard = meter(
      "Route coverage",
      coverage,
      `${number(observed)} observed capabilities from ${number(cards)} catalog cards`,
      coverage ? "active" : "held"
    );
    const gapCard = meter(
      "Gap pressure",
      gapPressure,
      `${number(gaps)} known tool or route gaps that AIOS should avoid or resolve`,
      gaps ? "attention" : "clear"
    );
    const gapActions = el("div", "capability-gap-actions");
    [
      ["Avoid", "Do not auto-run tools with missing proof, unclear auth, or stale source data."],
      ["Resolve", "Ask CapabilityOS for fallback route before provider or web execution."],
      ["Escalate", "Require operator confirmation for paid, private, destructive, or credentialed routes."],
    ].forEach(([label, detail]) => {
      const row = el("div", "capability-gap-row");
      row.append(el("strong", "", label), el("span", "", detail));
      gapActions.append(row);
    });
    gapSamples.slice(0, 3).forEach((gap) => {
      const row = el("div", "capability-gap-row sample");
      row.append(
        el("strong", "", text(gap.reason, "gap")),
        el("span", "", `${text(gap.detail, "review required")} · ${text(gap.evidence_ref, "no evidence ref")}`)
      );
      gapActions.append(row);
    });
    gapActions.append(chatPromptButton("Review Gaps", `CapabilityOS gap pressure가 ${Math.round(gapPressure)}%야. ${number(gaps)}개 gap 중 지금 AIOS 개발에서 피해야 할 나쁜 도구/불완전 route와 대체 route를 정리해줘.`));
    gapCard.append(gapActions);

    function routeMap(preview) {
      const map = el("div", "capability-route-map");
      const nodes = preview.nodes || [];
      const edges = preview.edges || [];
      const byId = new Map(nodes.map((node) => [text(node.id, ""), node]));
      edges.forEach((edge) => {
        const start = byId.get(text(edge.from, ""));
        const end = byId.get(text(edge.to, ""));
        if (!start || !end) return;
        const line = el("b", `capability-route-edge ${text(edge.kind, "edge")}`);
        const dx = Number(end.x || 0) - Number(start.x || 0);
        const dy = Number(end.y || 0) - Number(start.y || 0);
        line.style.left = `${Number(start.x || 0)}%`;
        line.style.top = `${Number(start.y || 0)}%`;
        line.style.width = `${Math.max(8, Math.hypot(dx, dy))}%`;
        line.style.transform = `rotate(${Math.atan2(dy, dx) * 180 / Math.PI}deg)`;
        map.append(line);
      });
      nodes.forEach((node) => {
        const item = el("div", `capability-route-node ${text(node.type, "route")} ${text(node.state, "")}`);
        item.style.left = `${Number(node.x || 50)}%`;
        item.style.top = `${Number(node.y || 50)}%`;
        item.title = [node.label, node.detail].filter(Boolean).join(" - ");
        item.append(el("strong", "", text(node.label, "node")), el("span", "", text(node.detail, "")));
        map.append(item);
      });
      if (!nodes.length) {
        map.append(el("span", "capability-route-map-empty", "CapabilityOS has not emitted route preview graph evidence yet."));
      }
      return map;
    }

    const routeMapCard = el("article", "capability-router-card route-map");
    routeMapCard.append(
      pill("Route Evidence Map", (routePreview.nodes || []).length ? "active" : "held"),
      el("strong", "", "Why this route is recommended"),
      routeMap(routePreview),
      el("small", "", "Routes connect to fallbacks, source evidence, known gaps, and provider takeover candidates.")
    );

    const routeBoard = el("article", "capability-router-card route-board");
    const routeRows = topRoutes.slice(0, 5).map((route) => {
      const row = el("div", "capability-route-row");
      const score = clampPercent(route.score);
      const scoreTrack = el("div", "capability-route-score");
      const fill = el("i");
      fill.style.width = `${Math.max(4, score)}%`;
      scoreTrack.append(fill);
      row.append(
        el("strong", "", text(route.name || route.id, "route")),
        el("span", "", `${text(route.id, "capability")} · ${text(route.kind, "kind")} · risk ${text(route.risk, "unknown")} · ${text(route.privacy, "privacy")} · ${route.requires_network ? "web required" : "local"} · ${number(route.observation_count)} observations`),
        scoreTrack,
        el("small", "", (route.reason_codes || []).slice(0, 3).join(" · ") || "reason pending"),
        el("small", "", (route.fallback_ids || []).slice(0, 3).join(" → ") || "fallback pending"),
        chatPromptButton(
          "Ask AIOS",
          `CapabilityOS route를 검토해줘. route_id=${text(route.id, "unknown")} name=${text(route.name, "unknown")} risk=${text(route.risk, "unknown")} network=${route.requires_network ? "required" : "local"} score=${number(route.score)} observations=${number(route.observation_count)}. 이 route를 지금 작업에 써도 되는지, 필요한 증거와 fallback을 알려줘.`
        )
      );
      return row;
    });
    routeBoard.append(
      pill("Recommended routes", topRoutes.length ? "active" : "held"),
      el("strong", "", topRoutes.length ? "Capability shortlist" : "No route shortlist"),
      ...(routeRows.length ? routeRows : [el("span", "", "No top routes found in snapshot")])
    );

    const sourceCockpit = el("article", "capability-router-card source-cockpit");
    const sourceGrid = el("div", "capability-source-grid");
    sourceModes.forEach((mode) => {
      const riskCounts = mode.risk_counts || {};
      const privacyCounts = mode.privacy_counts || {};
      const state = Number(mode.network || 0) ? "attention" : Number(mode.executes_tools || 0) ? "held" : "active";
      const chip = el("div", `capability-source-chip ${String(mode.mode || "mode").toLowerCase().replace(/[^a-z0-9]+/g, "-")}`);
      chip.append(
        pill(text(mode.mode, "Source"), state),
        el("strong", "", `${number(mode.count)} route card${Number(mode.count || 0) === 1 ? "" : "s"}`),
        el("span", "", `${number(mode.network)} network · ${number(mode.executes_tools)} direct tools · low ${number(riskCounts.low)} / medium ${number(riskCounts.medium)} / high ${number(riskCounts.high)}`),
        el("small", "", `privacy ${Object.entries(privacyCounts).map(([key, value]) => `${key}:${value}`).join(" · ") || "unknown"}`),
        el("small", "", (mode.top_capabilities || []).slice(0, 3).join(" · "))
      );
      sourceGrid.append(chip);
    });
    sourceCockpit.append(
      pill("Search Cockpit", sourceModes.length ? "active" : "held"),
      el("strong", "", "Where AIOS may look next"),
      el("span", "", "CapabilityOS classifies route cards by local OS, provider/LLM, web, API, MCP, and skills so the executor sees cost, privacy, and risk before acting."),
      sourceGrid,
      chatPromptButton("Choose Source", "CapabilityOS source choice를 해줘. 이 작업이 Internal/Web/API/MCP/Connector 중 어디를 써야 하는지, 각 선택의 비용/위험/증거 요구사항을 비교해줘."),
      el("small", "", "CapabilityOS recommends routes; Hive/myworld executes only after permission and evidence gates.")
    );

    const providerCard = el("article", "capability-router-card provider-board");
    const providerRows = providerRoutes.map((route) => {
      const row = el("div", "capability-provider-row");
      const score = clampPercent(route.score);
      const track = el("div", "capability-route-score");
      const fill = el("i");
      fill.style.width = `${Math.max(4, score)}%`;
      track.append(fill);
      row.append(
        el("strong", "", text(route.agent, "provider")),
        el("span", "", `${number(route.passed)} passed · ${number(route.failed)} failed · ${number(route.observations)} observations · ${Math.round(Number(route.confidence || 0) * 100)}% confidence`),
        track,
        el("small", "", (route.reason_codes || []).join(" · ") || "reason pending")
      );
      return row;
    });
    providerCard.append(
      pill("Provider fallback", providerRoutes.length ? "active" : "held"),
      el("strong", "", "Who should take over when a provider stalls"),
      ...(providerRows.length ? providerRows : [el("span", "", "No provider route observations available")])
    );

    const webCard = el("article", "capability-router-card web-policy");
    const webSteps = (webRoute.route_steps || []).slice(0, 4).map((step) => {
      const row = el("div", "capability-policy-row");
      row.append(
        el("strong", "", `${text(step.step, "step")} · ${text(step.tool_family, "tool")}`),
        el("span", "", text(step.purpose, "purpose pending")),
        el("small", "", (step.evidence_required || []).join(" · ") || "evidence pending")
      );
      return row;
    });
    const permissionRows = (constraintRoute.permission_questions || []).slice(0, 3).map((question) => {
      const row = el("div", "capability-policy-row permission");
      row.append(
        el("strong", "", text(question.permission_id, "permission")),
        el("span", "", text(question.question, "permission question")),
        el("small", "", text(question.risk, "risk pending"))
      );
      return row;
    });
    webCard.append(
      pill("Web/API/MCP gates", webSteps.length || permissionRows.length ? "attention" : "held"),
      el("strong", "", "High-freedom routes need explicit evidence"),
      ...(webSteps.length ? webSteps : [el("span", "", "No web research route policy returned")]),
      ...(permissionRows.length ? permissionRows : []),
      el("small", "", (constraintRoute.stop_conditions || []).slice(0, 4).join(" · ") || "stop conditions pending")
    );
    const routeOpen = artifactPreviewControl(capabilityPreview.path, "capability-route-open");
    if (routeOpen) webCard.append(routeOpen);

    grid.replaceChildren(userBoard, summary, coverageCard, gapCard, routeMapCard, routeBoard, sourceCockpit, providerCard, webCard);
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
        const canRequestRereview = item.review_result === "needs_more_evidence" && Number(item.evidence_count || 0) > 0;
        const review = el("button", "memory-draft-review", alreadyQueued ? "Queued" : "Request Review");
        review.type = "button";
        review.disabled = Boolean(alreadyQueued);
        const reviewDetail = item.review_result || item.review_state || "Draft only";
        const reviewStatus = el("small", "memory-draft-review-status", reviewDetail);
        review.addEventListener("click", () => requestMemoryDraftReview(item, reviewStatus, review));
        actions.append(review, reviewStatus);
        if (canRequestRereview) {
          const rereview = el("button", "memory-draft-review rereview", "Request Re-review");
          rereview.type = "button";
          rereview.addEventListener("click", () => requestMemoryDraftReview(item, reviewStatus, rereview));
          actions.append(rereview);
        }
        const guidance = item.next_evidence
          ? el("span", "memory-draft-next-evidence", item.next_evidence)
          : null;
        const reason = item.review_reason
          ? el("small", "memory-draft-review-reason", item.review_reason)
          : null;
        card.append(
          pill(text(item.type, "memory draft"), item.status),
          el("strong", "", text(item.content_preview, "No preview available")),
          el("small", "", `${text(item.conversation_id, "conversation")} · ${text(item.origin, "origin")} · ${text(item.review_state, "review")}`),
          el("span", "memory-draft-ref", refs || text(item.genesis_ref, "provenance pending"))
        );
        if (reason) card.append(reason);
        if (guidance) card.append(guidance);
        if (item.evidence_count) {
          const evidenceSummary = el(
            "small",
            "memory-draft-evidence-summary",
            `${Number(item.evidence_count)} evidence item${Number(item.evidence_count) === 1 ? "" : "s"} · ${text(item.latest_evidence_note || item.latest_evidence_artifact, "latest evidence")}`
          );
          card.append(evidenceSummary);
          if (item.latest_evidence_ref) {
            const evidenceOpen = artifactPreviewControl(item.latest_evidence_ref, "memory-draft-evidence-open");
            if (evidenceOpen) card.append(evidenceOpen);
          }
        }
        if (item.review_result_ref) {
          const result = artifactPreviewControl(item.review_result_ref, "memory-draft-result-open");
          if (result) card.append(result);
        }
        if (source) card.append(source);
        if (item.review_result === "needs_more_evidence") {
          const evidence = el("div", "memory-draft-evidence-form");
          const note = document.createElement("textarea");
          note.placeholder = "Operator note";
          note.rows = 2;
          note.setAttribute("aria-label", "Memory review evidence note");
          const artifact = document.createElement("input");
          artifact.type = "text";
          artifact.placeholder = ".aios/... or docs/...";
          artifact.setAttribute("aria-label", "Memory review evidence artifact");
          const evidenceButton = el("button", "memory-draft-evidence-button", "Add Evidence");
          evidenceButton.type = "button";
          const evidenceStatus = el("small", "memory-draft-evidence-status", "");
          evidenceButton.addEventListener("click", () => recordMemoryReviewEvidence(item, evidenceStatus, evidenceButton, note, artifact));
          evidence.append(note, artifact, evidenceButton, evidenceStatus);
          card.append(evidence);
        }
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
    const requestedMode = new URLSearchParams(window.location.search).get("mode");
    setMode(requestedMode || localStorage.getItem("aios-control-mode") || "simple");
    restoreSectionHash();
  }

  function installVisualFocus() {
    const params = new URLSearchParams(window.location.search);
    const targetId = params.get("visual_focus");
    if (!targetId || !/^[A-Za-z0-9_-]+$/.test(targetId)) return;
    const target = qs(targetId);
    if (!target) return;
    const source = target.closest(".panel, section") || target;
    const clone = source.cloneNode(true);
    clone.querySelectorAll("[id]").forEach((node) => {
      node.id = `visual-focus-${node.id}`;
    });
    if (clone.id) clone.id = `visual-focus-${clone.id}`;
    const harness = el("section", "visual-focus-harness");
    harness.append(
      el("p", "eyebrow", "Visual Focus"),
      el("h2", "", targetId),
      clone
    );
    document.body.classList.add("visual-focus-mode");
    const shell = document.querySelector(".shell") || document.body;
    shell.prepend(harness);
  }

  function controlVisualItem(kind) {
    const items = (controlVisualWorkflow && controlVisualWorkflow.items) || {};
    return items[kind] || null;
  }

  function showControlVisualItem(kind) {
    const item = controlVisualItem(kind);
    const preview = qs("control-visual-preview");
    const image = qs("control-visual-image");
    const caption = qs("control-visual-caption");
    const receipt = qs("control-visual-receipt");
    if (!item) {
      const evidence = qs("control-visual-evidence");
      if (evidence) evidence.textContent = `visual ${kind} unavailable`;
      return;
    }
    document.querySelectorAll("[data-control-visual-open]").forEach((button) => {
      button.classList.toggle("active", button.dataset.controlVisualOpen === kind);
    });
    if (kind === "receipt") {
      if (preview) preview.hidden = true;
      if (receipt) {
        receipt.hidden = false;
        receipt.textContent = [
          `receipt: ${text(item.path, "missing")}`,
          `status: ${text(item.status, "unknown")}`,
          `screenshot: ${text(item.screenshot_path, "none")}`,
          `stops: ${(item.stop_conditions || []).join(", ") || "none"}`,
        ].join("\n");
      }
      return;
    }
    if (receipt) receipt.hidden = true;
    if (!preview || !image || !caption) return;
    image.src = item.data_url || "";
    preview.hidden = !item.data_url;
    caption.textContent = item.path || `${kind} screenshot`;
  }

  function renderVisualFixWorkItem(action) {
    const list = qs("command-receipt-list");
    if (!list || !action) return;
    const existing = qs("visual-fix-work-item");
    if (existing) existing.remove();
    const row = el("div", "command-receipt-row visual-fix-work-item");
    row.id = "visual-fix-work-item";
    const head = el("div", "command-receipt-row-head");
    head.append(el("strong", "", "Visual Fix"), pill(text(action.status, "degraded"), action.severity || action.status));
    const detail = el("span", "command-receipt-path", `${text(action.receipt, "visual receipt")} · ${(action.stop_conditions || []).join(", ") || "needs review"}`);
    const actions = el("div", "visual-fix-actions");
    const promptButton = el("button", "visual-fix-button", text(action.label, "Create Visual Fix"));
    promptButton.type = "button";
    promptButton.addEventListener("click", () => focusInlineChat(text(action.prompt, "Create a visual fix work item for the latest degraded UI verification."), "Visual fix prompt prepared"));
    const confirm = el("label", "visual-fix-confirm");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    confirm.append(checkbox, el("span", "", "reviewed"));
    const promote = el("button", "visual-fix-button", "Promote Fix");
    promote.type = "button";
    const status = el("small", "visual-fix-status", "");
    promote.addEventListener("click", async () => {
      if (!checkbox.checked) {
        status.textContent = "Review confirmation required";
        checkbox.focus();
        return;
      }
      promote.disabled = true;
      status.textContent = "Promoting visual fix";
      try {
        const response = await fetch("/api/promote_visual_fix", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ visual_receipt: action.receipt, confirm: true }),
        });
        const payload = await response.json();
        if (!response.ok || !payload.ok) {
          status.textContent = payload.reason || "Visual fix promotion blocked";
          return;
        }
        const receipt = payload.receipt || {};
        status.textContent = `Promotion ready: ${text((receipt.artifact_paths || {}).contract_seed, receipt.promotion_id)}`;
      } catch (_error) {
        status.textContent = "Visual fix promotion API unavailable";
      } finally {
        promote.disabled = false;
      }
    });
    actions.append(promptButton, confirm, promote, status);
    row.append(head, detail, actions);
    list.prepend(row);
  }

  function renderControlVisualWorkflow(payload) {
    controlVisualWorkflow = payload || null;
    const items = (controlVisualWorkflow && controlVisualWorkflow.items) || {};
    const evidence = qs("control-visual-evidence");
    const reference = items.reference || {};
    const after = items.after || {};
    const receipt = items.receipt || {};
    if (evidence) {
      const receiptStatus = receipt.status ? `verify ${receipt.status}` : "verify pending";
      evidence.textContent = reference.path && after.path ? `${receiptStatus} · ${text(after.path).split("/").pop()}` : "visual evidence missing";
    }
    document.querySelectorAll("[data-control-visual-open]").forEach((button) => {
      const kind = button.dataset.controlVisualOpen || "";
      button.disabled = !items[kind];
    });
    if (after.data_url) showControlVisualItem("after");
    else if (reference.data_url) showControlVisualItem("reference");
    renderVisualFixWorkItem(controlVisualWorkflow.action);
  }

  async function loadControlVisualWorkflow() {
    if (!qs("control-visual-workflow")) return;
    try {
      const response = await fetch("/api/visual_workflow", { headers: { Accept: "application/json" } });
      const payload = await response.json();
      if (!response.ok || !payload.ok) {
        const evidence = qs("control-visual-evidence");
        if (evidence) evidence.textContent = payload.reason || "visual workflow unavailable";
        return;
      }
      renderControlVisualWorkflow(payload);
    } catch (_error) {
      const evidence = qs("control-visual-evidence");
      if (evidence) evidence.textContent = "visual workflow API unavailable";
    }
  }

  function installControlVisualWorkflow() {
    document.querySelectorAll("[data-control-visual-open]").forEach((button) => {
      button.addEventListener("click", () => showControlVisualItem(button.dataset.controlVisualOpen || "after"));
    });
    loadControlVisualWorkflow();
  }

  function restoreSectionHash() {
    const hash = window.location.hash.replace(/^#/, "");
    if (!hash || hash.includes("=")) return;
    const target = qs(hash);
    if (!target) return;
    target.scrollIntoView({ block: "start" });
    window.setTimeout(() => target.scrollIntoView({ block: "start" }), 120);
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

  function roleProgress(status) {
    const normalized = String(status || "").toLowerCase();
    if (["passed", "ready", "complete", "completed", "collected"].includes(normalized)) return 100;
    if (["running", "active", "released", "sent"].includes(normalized)) return 72;
    if (["degraded", "waiting", "planned", "draft"].includes(normalized)) return 46;
    if (["failed", "blocked", "held", "missing"].includes(normalized)) return 18;
    return 34;
  }

  function progressBar(value, label) {
    const percent = clampPercent(value);
    const wrap = el("div", "agent-progress");
    const head = el("div", "agent-progress-head");
    head.append(el("span", "", label), el("strong", "", `${Math.round(percent)}%`));
    const track = el("div", "agent-progress-track");
    const fill = el("i");
    fill.style.width = `${Math.max(4, percent)}%`;
    track.append(fill);
    wrap.append(head, track);
    return wrap;
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
      const status = roleStatuses[role] || "waiting";
      card.append(
        pill(roleLabel(role), status),
        el("strong", "", text(status, "waiting")),
        progressBar(roleProgress(status), "Progress"),
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
      progressBar(roleProgress(invocation.overall_status), "Execution"),
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
    function worldlineMap(preview) {
      const nodes = (preview.nodes || []).slice(0, 24);
      const edges = (preview.edges || []).slice(0, 40);
      const map = el("article", "genesis-worldline-card");
      const head = el("div", "genesis-worldline-head");
      head.append(el("strong", "", "Worldline Map"), el("span", "", "discomfort -> branch -> seed -> evidence"));
      const surface = el("div", "genesis-worldline-surface");
      const nodeIds = new Set(nodes.map((node) => node.id));
      edges.filter((edge) => nodeIds.has(edge.from) && nodeIds.has(edge.to)).forEach((edge) => {
        const fromNode = nodes.find((node) => node.id === edge.from);
        const toNode = nodes.find((node) => node.id === edge.to);
        if (!fromNode || !toNode) return;
        const x1 = Number(fromNode.x || 0);
        const y1 = Number(fromNode.y || 0);
        const x2 = Number(toNode.x || 0);
        const y2 = Number(toNode.y || 0);
        const line = el("i", `genesis-worldline-edge ${text(edge.kind, "link")}`);
        const dx = x2 - x1;
        const dy = y2 - y1;
        const length = Math.max(8, Math.hypot(dx, dy));
        line.style.left = `${x1}%`;
        line.style.top = `${y1}%`;
        line.style.width = `${length}%`;
        line.style.transform = `rotate(${Math.atan2(dy, dx)}rad)`;
        surface.append(line);
      });
      nodes.forEach((node) => {
        const button = el("button", `genesis-worldline-node ${text(node.type, "node")} ${text(node.state, "")}`);
        button.type = "button";
        button.style.left = `${Number(node.x || 0)}%`;
        button.style.top = `${Number(node.y || 0)}%`;
        button.title = text(node.detail || node.label);
        button.append(el("strong", "", text(node.label, node.type)), el("span", "", text(node.type)));
        if (node.type === "seed" || node.type === "branch" || node.type === "discomfort") {
          button.addEventListener("click", () => focusInlineChat(
            `GenesisOS worldline node를 실행 가능한 AIOS 작업으로 바꿔줘. type=${text(node.type)} label=${text(node.label)} detail=${text(node.detail)} source=${text(lens.source_artifact, "")}`,
            "Genesis worldline node prepared"
          ));
        }
        surface.append(button);
      });
      if (!nodes.length) {
        surface.append(el("div", "genesis-worldline-empty", "No worldline evidence found."));
      }
      map.append(head, surface);
      return map;
    }
    const branches = (lens.branches || []).slice(0, 5);
    const cycle = qs("genesis-cycle-grid");
    if (cycle) {
      const discomforts = branches.map((branch) => branch.what_it_breaks).filter(Boolean);
      const needs = branches.map((branch) => branch.why_it_might_matter).filter(Boolean);
      const inventions = branches.map((branch) => branch.contract_seed).filter(Boolean);
      const productBoard = el("article", "genesis-cycle-card user-board");
      const productMetrics = el("div", "os-product-metrics");
      productMetrics.append(
        metric("worldlines", branches.length, ""),
        metric("discomforts", discomforts.length, ""),
        metric("needs", needs.length, ""),
        metric("seeds", inventions.length, "")
      );
      const productActions = el("div", "os-product-actions");
      productActions.append(
        askActionButton("Feel Friction", `GenesisOS가 지금 AIOS UI/UX에서 느껴야 할 불편함을 찾아줘. source=${text(lens.source_artifact, "none")} branches=${number(branches.length)}. 단순 개선이 아니라 새로운 필요성과 발명 seed로 바꿔줘.`),
        askActionButton("Make Worlds", "GenesisOS가 같은 문제를 3개의 다른 세계선으로 다시 설계해줘. 하나는 보수적, 하나는 제품급, 하나는 이상하지만 강한 아이디어로.")
      );
      productBoard.append(
        pill("GenesisOS", text(lens.authority, "speculative_only")),
        el("strong", "", "How AIOS escapes the obvious answer"),
        el("span", "", `${number(branches.length)} speculative worldlines turn discomfort into need and then into contract seeds before Hive executes.`),
        productMetrics,
        el("small", "", text(lens.source_invocation, "source invocation pending")),
        productActions
      );
      const cycleCards = [
        ["Discomfort", discomforts[0] || "No discomfort signal found", `${number(discomforts.length)} break signal${discomforts.length === 1 ? "" : "s"}`, "attention"],
        ["Need", needs[0] || "No need hypothesis found", `${number(needs.length)} need hypothesis${needs.length === 1 ? "" : "es"}`, "active"],
        ["Invention seed", inventions[0] || text(lens.source_artifact, "No contract seed found"), `${number(inventions.length)} speculative seed${inventions.length === 1 ? "" : "s"}`, "held"],
      ].map(([title, body, detail, state]) => {
        const card = el("article", `genesis-cycle-card ${state}`);
        card.append(pill(title, state), el("strong", "", body), el("span", "", detail));
        if (title === "Invention seed") {
          card.append(chatPromptButton("Develop Seed", `GenesisOS invention seed를 실행 가능한 AIOS goal/contract 후보로 발전시켜줘: ${body}`));
        }
        return card;
      });
      cycle.replaceChildren(productBoard, ...cycleCards);
    }
    const map = qs("genesis-worldline-map");
    if (map) {
      map.replaceChildren(worldlineMap(lens.worldline_preview || {}));
    }
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
          el("small", "", text(branch.risk, "Speculative only")),
          chatPromptButton(
            "Use Branch",
            `GenesisOS branch를 검토해줘. branch_id=${text(branch.branch_id, "unknown")} type=${text(branch.type, "branch")} premise=${text(branch.premise, "")} discomfort=${text(branch.what_it_breaks, "")} need=${text(branch.why_it_might_matter, "")} seed=${text(branch.contract_seed, "")}. 이걸 지금 AIOS 개발에 쓸 수 있는 goal/contract/검증 gate로 바꿔줘.`
          )
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
        const contracts = (item.contracts || []).slice(0, 3);
        if (contracts.length) {
          const list = el("div", "friction-contract-list");
          contracts.forEach((contract) => {
            const row = el("div", "friction-contract-row");
            const escapeVectors = (contract.escape_vectors || []).slice(0, 2);
            row.append(
              el("strong", "", text(contract.contract_id, "contract")),
              el("span", "", text(contract.path, "no path")),
              el("small", "", escapeVectors.join(" · ") || "No escape vector")
            );
            const actions = el("div", "friction-action-row");
            const open = artifactPreviewControl(contract.path, "friction-open-contract");
            if (open) actions.append(open);
            actions.append(chatPromptButton(
              "Break Frame",
              `GenesisOS prompt-prison advisory를 action으로 바꿔줘. contract=${text(contract.contract_id)} path=${text(contract.path)} escape_vectors=${escapeVectors.join(" | ")}. 대안 세계선 3개, 필요한 검증 gate, 실행 가능한 AIOS contract seed를 만들어줘.`,
              "friction-break-frame"
            ));
            const propose = el("button", "friction-propose-contract", "Propose Contract");
            propose.type = "button";
            const proposeStatus = el("small", "friction-propose-status", "");
            propose.addEventListener("click", async () => {
              propose.disabled = true;
              proposeStatus.textContent = "Creating proposed contract";
              try {
                const response = await fetch("/api/genesis_break_frame_seed", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({
                    confirm: true,
                    materialize: true,
                    contract_id: contract.contract_id,
                    contract_path: contract.path,
                    reason: item.reason,
                    escape_vectors: contract.escape_vectors || [],
                    signatures: contract.signatures || [],
                  }),
                });
                const payload = await response.json();
                if (!response.ok || !payload.ok) {
                  proposeStatus.textContent = payload.reason || (payload.materialization_error || {}).reason || "Contract proposal blocked";
                  return;
                }
                const materialization = payload.materialization || {};
                proposeStatus.textContent = `Proposed ${text(materialization.contract_id, "contract")}`;
                const result = el("div", "friction-materialization-result");
                result.append(
                  el("span", "", text(materialization.contract_path || payload.source_seed, "proposal created"))
                );
                const materialized = artifactPreviewControl(materialization.contract_path, "friction-open-contract");
                if (materialized) result.append(materialized);
                row.append(result);
              } catch (_error) {
                proposeStatus.textContent = "Proposal API unavailable";
              } finally {
                propose.disabled = false;
              }
            });
            actions.append(propose, proposeStatus);
            row.append(actions);
            list.append(row);
          });
          card.append(list);
        }
        const weakPersonas = (item.weak_personas || []).slice(0, 3);
        if (weakPersonas.length) {
          const personas = el("div", "friction-persona-list");
          weakPersonas.forEach((weak) => {
            personas.append(el("span", "", `${text(weak.score_key, "persona")} ${text(weak.score, "0")}`));
          });
          card.append(personas, chatPromptButton(
            "Route Persona Gap",
            `AIOS persona gap을 다음 작업으로 라우팅해줘: ${weakPersonas.map((weak) => `${text(weak.score_key)}=${text(weak.score)} ${text(weak.recommendation, "")}`).join(" / ")}`,
            "friction-break-frame"
          ));
        }
        return card;
      })
    );
  }

  function metric(label, value, unit) {
    const row = el("div", "os-metric");
    row.append(el("strong", "", number(value)), el("span", "", unit ? `${label} ${unit}` : label));
    return row;
  }

  function clampPercent(value) {
    const numeric = Number(value || 0);
    if (!Number.isFinite(numeric)) return 0;
    return Math.max(0, Math.min(100, numeric));
  }

  function osSignal(card) {
    if (card.id === "memory") {
      const total = Number(card.source.retrieval_traces || 0);
      const selected = Number(card.source.retrieval_traces_with_selected || 0);
      return {
        label: "retrieval selectivity",
        value: total ? (selected / total) * 100 : 0,
        detail: `${number(selected)} selected traces / ${number(total)} total`,
      };
    }
    if (card.id === "capability") {
      const cards = Number(card.source.capability_cards || 0);
      const observed = Number(card.source.observed_capabilities || 0);
      const gaps = Number(card.source.gaps || 0);
      const base = cards ? (observed / cards) * 100 : 0;
      const penalty = cards ? Math.min(35, (gaps / Math.max(cards, 1)) * 20) : 0;
      return {
        label: "route coverage",
        value: base - penalty,
        detail: `${number(observed)} observed / ${number(cards)} cards · ${number(gaps)} gaps`,
      };
    }
    if (card.id === "genesis") {
      const branches = Number(card.source.branches || 0);
      return {
        label: "divergence width",
        value: (branches / 5) * 100,
        detail: `${number(branches)} worldlines available before convergence`,
      };
    }
    if (card.id === "hive") {
      const board = card.source.hive_board || {};
      const done = Number(board.pipeline_done || 0);
      const total = Number(board.pipeline_total || 0);
      return {
        label: "execution proof",
        value: total ? (done / total) * 100 : 0,
        detail: total ? `${number(done)} / ${number(total)} pipeline artifacts done` : text(card.source.next_action, "waiting for run evidence"),
      };
    }
    const healthy = ["clear", "passed", "healthy", "running"].includes(String(card.status || "").toLowerCase());
    return {
      label: "control readiness",
      value: healthy ? 100 : 45,
      detail: healthy ? "monitor clear" : text(card.headline, "operator attention required"),
    };
  }

  function renderOsSignal(card) {
    const signal = osSignal(card);
    const percent = clampPercent(signal.value);
    const wrap = el("div", "os-signal");
    const head = el("div", "os-signal-head");
    head.append(el("span", "", signal.label), el("strong", "", `${Math.round(percent)}%`));
    const track = el("div", "os-signal-track");
    const fill = el("i");
    fill.style.width = `${Math.max(4, percent)}%`;
    track.append(fill);
    wrap.append(head, track, el("small", "", signal.detail));
    return wrap;
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
        source: memory,
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
        source: capability,
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
        source: genesis,
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
        source: hive,
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
        source: myworld,
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
        item.append(
          head,
          el("strong", "os-lane-headline", text(card.headline, "waiting")),
          renderOsSignal(card),
          metrics,
          el("p", "os-lane-detail", text(card.detail, "No detail"))
        );
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

  function chatMetaCount(value) {
    const number = Number(value || 0);
    return Number.isFinite(number) ? number : 0;
  }

  function chatMetaItems(result) {
    if (!result || typeof result !== "object") return [];
    const items = [];
    const chair = result.gate_chair_status || {};
    if (chair.attempted) {
      const mode = chair.mode || "chair";
      const model = chair.model ? ` ${chair.model}` : "";
      items.push({ label: "Chair", value: `${mode}${model}`, state: chair.status || "unknown" });
    } else {
      items.push({ label: "Chair", value: "internal route", state: "not_attempted" });
    }
    const memory = result.memory_context || {};
    if (memory.status || memory.context_items !== undefined) {
      const trace = memory.trace_id ? ` ${memory.trace_id}` : "";
      items.push({ label: "Memory", value: `${chatMetaCount(memory.context_items)} selected${trace}`, state: memory.status || "available" });
    }
    const artifacts = result.artifact_paths || {};
    if (artifacts.capability_route) {
      items.push({ label: "Capability", value: artifacts.capability_route, state: "routed" });
    }
    const genesis = result.genesis_friction || {};
    if (genesis.branch_count !== undefined || Array.isArray(genesis.frictions)) {
      const count = genesis.branch_count !== undefined ? chatMetaCount(genesis.branch_count) : (genesis.frictions || []).length;
      items.push({ label: "Genesis", value: `${count} branches`, state: genesis.authority || "speculative" });
    }
    const route = [result.chosen_substrate, result.route_reason].filter(Boolean).join(" / ");
    if (route) {
      items.push({ label: "Route", value: route, state: result.status || "routed" });
    }
    return items;
  }

  function chatMeta(result) {
    return chatMetaItems(result)
      .map((item) => `${item.label}: ${item.value}`)
      .join(" · ");
  }

  function chatEvidenceItems(result) {
    if (!result || typeof result !== "object") return [];
    const items = [];
    const receipt = result.operating_receipt || {};
    const route = [result.chosen_substrate, result.route_reason].filter(Boolean).join(" · ");
    if (route) items.push({ key: "route", value: route });
    if (receipt.route_summary) items.push({ key: "AIOS Gate", value: receipt.route_summary });
    const memory = result.memory_context || {};
    if (memory.context_items !== undefined) {
      const trace = memory.trace_id ? ` · ${memory.trace_id}` : "";
      items.push({ key: "memoryos", value: `${Number(memory.context_items || 0)} selected${trace}` });
    }
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
      const mode = chair.mode || "unknown";
      const model = chair.model ? ` · ${chair.model}` : "";
      items.push({ key: "chair", value: `${mode}${model} · ${chair.status || "unknown"} · executed=${Boolean(chair.executed)}` });
    }
    if ((result.artifact_paths || {}).friction_contract_seed) {
      items.push({ key: "friction_contract_seed", value: result.artifact_paths.friction_contract_seed });
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
        if (item.key === "friction_contract_seed") {
          const confirmLabel = el("label", "promotion-confirm");
          const checkbox = document.createElement("input");
          checkbox.type = "checkbox";
          confirmLabel.append(checkbox, el("span", "", "reviewed seed"));
          const promote = el("button", "inline-chat-open", "Promote Seed");
          promote.type = "button";
          const status = el("small", "promotion-status");
          const resultBox = el("div", "promotion-result");
          promote.addEventListener("click", async () => {
            if (!checkbox.checked) {
              status.textContent = "Review confirmation required";
              checkbox.focus();
              return;
            }
            promote.disabled = true;
            status.textContent = "Promoting";
            try {
              const response = await fetch("/api/promote_friction_seed", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ source_seed: path, confirm: true }),
              });
              const payload = await response.json();
              if (!response.ok || !payload.ok) {
                status.textContent = payload.reason || "Promotion blocked";
                return;
              }
              status.textContent = "Promotion ready";
              renderPromotionRows(resultBox, payload.receipt || {});
            } catch (_error) {
              status.textContent = "Promotion API unavailable";
            } finally {
              promote.disabled = false;
            }
          });
          entry.append(confirmLabel, promote, status, resultBox);
        }
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
    if (role === "assistant") {
      const metaItems = chatMetaItems(result);
      if (metaItems.length) {
        const strip = el("div", "chat-runtime-strip inline-chat-runtime-strip");
        strip.setAttribute("aria-label", "AIOS runtime evidence");
        metaItems.slice(0, 5).forEach((item) => {
          const chip = el("span", `chat-runtime-chip ${String(item.state || "").toLowerCase().replace(/[^a-z0-9_-]+/g, "-")}`);
          chip.append(el("strong", "", item.label), el("span", "", item.value));
          strip.append(chip);
        });
        row.append(strip);
      }
    }
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
    function resizeInput() {
      input.style.height = "auto";
      input.style.height = `${Math.min(input.scrollHeight, 180)}px`;
    }
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
          status.textContent = "대화 가능";
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
      resizeInput();
      button.disabled = true;
      status.textContent = "생각 중";
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ message, conversation_id: conversationId }));
        return;
      }
      try {
        const result = await sendViaHttp(message, conversationId);
        addInlineChatMessage("assistant", result.response || "AIOS returned no text.", chatMeta(result), result);
        status.textContent = "대화 가능";
      } catch (error) {
        status.textContent = "Chat failed";
      } finally {
        button.disabled = false;
      }
    });
    document.querySelectorAll("[data-chat-prompt]").forEach((promptButton) => {
      promptButton.addEventListener("click", () => {
        input.value = promptButton.dataset.chatPrompt || "";
        resizeInput();
        input.focus();
      });
    });
    input.addEventListener("input", resizeInput);
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        form.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
      }
    });
    if (qs("inline-chat-thread").children.length === 0) {
      addInlineChatMessage(
        "assistant",
        "안녕. 바로 물어봐. 필요한 기억, 도구 경로, 실행 판단은 AIOS가 뒤에서 붙일게.",
        "",
        {}
      );
    }
    resizeInput();
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

  async function submitAskGoal(goal, sourceButton) {
    const askInput = qs("ask-input");
    const askDraft = qs("ask-draft-contract");
    const askStatus = qs("ask-status");
    const inlineStatus = qs("inline-chat-status");
    const result = qs("ask-result");
    if (askInput) askInput.value = goal;
    if (askDraft) askDraft.checked = true;
    if (result) result.replaceChildren();
    if (askStatus) askStatus.textContent = "Creating governed ask";
    if (inlineStatus) inlineStatus.textContent = "Creating governed ask";
    if (sourceButton) sourceButton.disabled = true;
    try {
      const response = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ goal, draft_contract: true }),
      });
      const payload = await response.json();
      if (!response.ok || !payload.ok) {
        const reason = payload.reason || "Ask failed";
        if (askStatus) askStatus.textContent = reason;
        if (inlineStatus) inlineStatus.textContent = reason;
        return;
      }
      if (askStatus) askStatus.textContent = "Governed ask created";
      if (inlineStatus) inlineStatus.textContent = "Governed ask created";
      renderAskResult(payload.receipt || {});
    } catch (_error) {
      if (askStatus) askStatus.textContent = "Local ask API is not running";
      if (inlineStatus) inlineStatus.textContent = "Local ask API is not running";
    } finally {
      if (sourceButton) sourceButton.disabled = false;
    }
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
    renderCommandEvidence(data);
    renderAnticipatorySurface(data);
    renderIntentLens(data);
    renderCompletion(data);
    renderInstallation(data);
    renderWorkbench(data);
    renderLoopMap(data);
    renderExecutionLens(data);
    renderContracts(data);
    renderDispatches(data);
    renderRepos(data);
    renderRoster(data);
    renderContractBoard(data);
    renderRoutes(data);
    renderStops(data);
    renderSimple(data);
    renderHiveTui(data);
    renderLatestInvocation(data);
    renderWorkTimeline(data);
    renderPromotionQueue(data);
    renderCapabilityRouter(data);
    renderMemoryLibrary(data);
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
  installVisualFocus();
  installControlVisualWorkflow();
  installSessionForm();
  installInlineChat();
  installAskForm();
  restoreArtifactHash();
  window.addEventListener("hashchange", restoreArtifactHash);
  window.addEventListener("hashchange", restoreSectionHash);
})();

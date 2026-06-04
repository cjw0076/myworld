(function () {
  const controlSnapshot = window.AIOS_CONTROL_SNAPSHOT || {};

  function qs(id) {
    return document.getElementById(id);
  }

  function wsUrl() {
    const params = new URLSearchParams(window.location.search);
    if (params.get("ws")) return params.get("ws");
    const port = params.get("wsPort") || "8766";
    return `ws://${window.location.hostname || "127.0.0.1"}:${port}/chat`;
  }

  function metaCount(value) {
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
      items.push({ label: "Memory", value: `${metaCount(memory.context_items)} selected${trace}`, state: memory.status || "available" });
    }
    const artifacts = result.artifact_paths || {};
    if (artifacts.capability_route) {
      items.push({ label: "Capability", value: artifacts.capability_route, state: "routed" });
    }
    const genesis = result.genesis_friction || {};
    if (genesis.branch_count !== undefined || Array.isArray(genesis.frictions)) {
      const count = genesis.branch_count !== undefined ? metaCount(genesis.branch_count) : (genesis.frictions || []).length;
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

  function compact(value, fallback = "waiting") {
    const next = String(value === undefined || value === null || value === "" ? fallback : value);
    return next.length > 64 ? `${next.slice(0, 61)}...` : next;
  }

  function renderChatDecisionMap(result) {
    const flow = qs("chat-decision-flow");
    const shell = qs("chat-decision-map");
    if (!flow || !shell) return;
    const head = shell.querySelector(".chat-decision-head span");
    const chair = (result && result.gate_chair_status) || {};
    const memory = (result && result.memory_context) || {};
    const artifacts = (result && result.artifact_paths) || {};
    const genesis = (result && result.genesis_friction) || {};
    const receipt = (result && result.operating_receipt) || {};
    const route = [result && result.chosen_substrate, result && result.route_reason].filter(Boolean).join(" / ");
    function firstArtifact(keys) {
      for (const key of keys) {
        const value = artifacts[key] || result[key] || receipt[key] || memory[key] || genesis[key];
        if (artifactPath(value)) return artifactPath(value);
      }
      return "";
    }
    const nodes = [
      {
        label: "Chair",
        state: chair.attempted ? compact(chair.status, "attempted") : "internal",
        detail: chair.attempted ? compact([chair.mode, chair.model].filter(Boolean).join(" "), "provider") : "low-cost route",
        path: firstArtifact(["gate_chair_turns", "gate_chair_turn"]),
      },
      {
        label: "Memory",
        state: memory.status || (memory.context_items !== undefined ? "selected" : "waiting"),
        detail: memory.trace_id || `${metaCount(memory.context_items)} selected`,
        path: firstArtifact(["memory_context_pack", "memory_context", "context_pack"]),
      },
      {
        label: "Capability",
        state: artifacts.capability_route ? "routed" : "waiting",
        detail: artifacts.capability_route || "no route artifact yet",
        path: firstArtifact(["capability_route"]),
      },
      {
        label: "Genesis",
        state: genesis.authority || (genesis.branch_count !== undefined ? "speculative" : "waiting"),
        detail: genesis.branch_count !== undefined ? `${metaCount(genesis.branch_count)} branches` : "no branch yet",
        path: firstArtifact(["genesis_branches", "genesis", "friction_contract_seed"]),
      },
      {
        label: "Route",
        state: (result && result.status) || "ready",
        detail: route || "ask AIOS",
        path: firstArtifact(["receipt", "invocation_receipt", "route_receipt", "cost"]),
      },
    ];
    flow.replaceChildren(
      ...nodes.map((node, index) => {
        const item = document.createElement("button");
        item.type = "button";
        item.className = `chat-decision-node ${String(node.state || "").toLowerCase().replace(/[^a-z0-9_-]+/g, "-")}${node.path ? " has-artifact" : ""}`;
        item.disabled = !node.path;
        if (node.path) {
          item.title = `Open ${node.path}`;
          item.addEventListener("click", () => {
            const panel = artifactHashPanel();
            const pathLabel = panel.querySelector(".artifact-hash-path");
            const preview = panel.querySelector(".artifact-hash-preview");
            if (pathLabel) pathLabel.textContent = node.path;
            if (preview) openArtifact(node.path, preview);
            panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
          });
        }
        const indexNode = document.createElement("i");
        indexNode.textContent = String(index + 1);
        const label = document.createElement("strong");
        label.textContent = node.label;
        const state = document.createElement("span");
        state.textContent = compact(node.state);
        const detail = document.createElement("small");
        detail.textContent = compact(node.detail);
        item.append(indexNode, label, state, detail);
        return item;
      })
    );
    if (head) head.textContent = result && Object.keys(result).length ? "latest AIOS route" : "waiting for first route";
  }

  async function requestOfflineMemoryReview(packet, status, button) {
    if (!packet.memory_draft_source || !packet.memory_draft_id) {
      status.textContent = "No MemoryOS draft linked";
      return;
    }
    button.disabled = true;
    status.textContent = "Sending to MemoryOS";
    try {
      const response = await fetch("/api/memory_draft_review", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source_artifact: packet.memory_draft_source,
          draft_id: packet.memory_draft_id,
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
      status.textContent = `Queued ${receipt.request_id || "request"}`;
      button.textContent = "Review Queued";
      setStatus("Offline user memory review queued");
    } catch (_error) {
      status.textContent = "Review API unavailable";
      button.disabled = false;
    }
  }

  async function recordOfflineMemoryEvidence(packet, status, button, noteInput, artifactInput) {
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
          source_artifact: packet.memory_draft_source,
          draft_id: packet.memory_draft_id,
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
      status.textContent = `Evidence recorded ${receipt.evidence_id || ""}`;
      noteInput.value = "";
      artifactInput.value = "";
      setStatus("Offline user evidence recorded");
    } catch (_error) {
      status.textContent = "Evidence API unavailable";
    } finally {
      button.disabled = false;
    }
  }

  function renderOfflineUserPanel(snapshot) {
    const panel = qs("offline-user-panel");
    const status = qs("offline-user-status");
    const body = qs("offline-user-body");
    if (!panel || !status || !body) return;
    const packet = ((((snapshot || {}).offline_user || {}).latest || [])[0]) || {};
    if (!packet.path) {
      status.textContent = "no frontier packet";
      body.replaceChildren();
      body.appendChild(document.createElement("small")).textContent = "AIOS will show bounded field-observation requests here.";
      return;
    }
    status.textContent = packet.packet_type || "frontier";
    const title = document.createElement("strong");
    title.textContent = packet.title || packet.path;
    const meta = document.createElement("small");
    meta.textContent = [packet.contract_id, packet.next_action].filter(Boolean).join(" · ");
    const boundary = document.createElement("span");
    boundary.className = "offline-user-boundary";
    boundary.textContent = packet.privacy_boundary || packet.stop_condition || packet.next_question || "draft-first MemoryOS review";
    const actions = document.createElement("div");
    actions.className = "offline-user-actions";
    const open = document.createElement("button");
    open.type = "button";
    open.textContent = "Open Packet";
    open.addEventListener("click", () => {
      const desk = artifactHashPanel();
      const pathLabel = desk.querySelector(".artifact-hash-path");
      const preview = desk.querySelector(".artifact-hash-preview");
      if (pathLabel) pathLabel.textContent = packet.path;
      if (preview) openArtifact(packet.path, preview);
      desk.scrollIntoView({ behavior: "smooth", block: "nearest" });
    });
    actions.append(open);
    if (packet.memory_draft_source && packet.memory_draft_id) {
      const queued = packet.memory_review_state && packet.memory_review_state !== "operator_review_required";
      const canRereview = packet.memory_review_result === "needs_more_evidence" && Number(packet.evidence_count || 0) > 0;
      const review = document.createElement("button");
      review.type = "button";
      review.textContent = canRereview ? "Request Re-review" : (queued ? "Review Queued" : "Request Review");
      review.disabled = Boolean(queued && !canRereview);
      const reviewStatus = document.createElement("small");
      reviewStatus.className = "offline-user-review-status";
      reviewStatus.textContent = packet.memory_review_result || packet.memory_review_state || "MemoryOS draft";
      review.addEventListener("click", () => requestOfflineMemoryReview(packet, reviewStatus, review));
      actions.append(review, reviewStatus);
    }
    const prepare = document.createElement("button");
    prepare.type = "button";
    prepare.textContent = "Prepare Reply";
    prepare.addEventListener("click", () => {
      const input = qs("chat-input");
      input.value = [
        "이 offline-user-agent packet을 보고, user@offline이 답할 수 있는 관찰 형식으로 정리해줘.",
        `packet=${packet.path}`,
        `type=${packet.packet_type || "unknown"}`,
        `privacy_boundary=${packet.privacy_boundary || "private/raw data stays offline"}`,
      ].join("\n");
      input.focus();
      setStatus("Offline user prompt prepared");
    });
    actions.append(prepare);
    const children = [title, meta, boundary, actions];
    if (packet.memory_draft_source && packet.memory_draft_id && packet.memory_review_result === "needs_more_evidence") {
      const evidence = document.createElement("div");
      evidence.className = "memory-draft-evidence-form offline-user-evidence-form";
      if (packet.evidence_count) {
        const summary = document.createElement("small");
        summary.className = "memory-draft-evidence-summary";
        summary.textContent = `${Number(packet.evidence_count)} evidence item${Number(packet.evidence_count) === 1 ? "" : "s"} · ${packet.latest_evidence_note || packet.latest_evidence_artifact || "latest evidence"}`;
        evidence.append(summary);
      }
      const note = document.createElement("textarea");
      note.placeholder = "Operator evidence note";
      note.rows = 2;
      note.setAttribute("aria-label", "Offline user memory evidence note");
      const artifact = document.createElement("input");
      artifact.type = "text";
      artifact.placeholder = ".aios/... or docs/...";
      artifact.setAttribute("aria-label", "Offline user memory evidence artifact");
      const evidenceButton = document.createElement("button");
      evidenceButton.type = "button";
      evidenceButton.textContent = "Add Evidence";
      const evidenceStatus = document.createElement("small");
      evidenceStatus.className = "memory-draft-evidence-status";
      evidenceButton.addEventListener("click", () => recordOfflineMemoryEvidence(packet, evidenceStatus, evidenceButton, note, artifact));
      evidence.append(note, artifact, evidenceButton, evidenceStatus);
      children.push(evidence);
    }
    body.replaceChildren(...children);
  }

  function historyChairLabel(item) {
    const chair = (item && item.chair) || {};
    if (!chair.attempted) return "Chair internal route";
    const mode = chair.mode || "chair";
    const model = chair.model ? ` ${chair.model}` : "";
    return `Chair ${mode}${model} ${chair.status || ""}`.trim();
  }

  function appendRuntimeStrip(row, result) {
    const items = chatMetaItems(result);
    if (!items.length) return;
    const strip = document.createElement("div");
    strip.className = "chat-runtime-strip";
    strip.setAttribute("aria-label", "AIOS runtime evidence");
    items.slice(0, 5).forEach((item) => {
      const chip = document.createElement("span");
      chip.className = `chat-runtime-chip ${String(item.state || "").toLowerCase().replace(/[^a-z0-9_-]+/g, "-")}`;
      const label = document.createElement("strong");
      label.textContent = item.label;
      const value = document.createElement("span");
      value.textContent = item.value;
      chip.append(label, value);
      strip.appendChild(chip);
    });
    row.appendChild(strip);
  }

  function evidenceItems(result) {
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
    (memory.selected_memories || []).slice(0, 5).forEach((item) => {
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
    if ((result.artifact_paths || {}).invocation_receipt) {
      items.push({ key: "route_promotion", value: result.artifact_paths.invocation_receipt });
    }
    Object.entries(result.artifact_paths || {})
      .filter((entry) => entry[1])
      .slice(0, 5)
      .forEach(([key, value]) => items.push({ key, value }));
    return items;
  }

  function artifactPath(value) {
    const text = String(value || "").trim();
    if (!text || text.includes("\n")) return "";
    return text.startsWith(".aios/") || text.startsWith("docs/") || text.startsWith("apps/control/") ? text : "";
  }

  function artifactAuthority(value) {
    const path = artifactPath(value);
    if (path.startsWith(".aios/invocations/")) return { call: "ingest", authority: "AIOS invocation record" };
    if (path.startsWith(".aios/chat/")) return { call: "close", authority: "AIOS chat record" };
    if (path.startsWith(".aios/outbox/")) return { call: "close", authority: "dispatch result" };
    if (path.startsWith(".aios/visual_verification/")) return { call: "verify", authority: "visual verification" };
    if (path.startsWith(".aios/promotions/")) return { call: "promote", authority: "MyWorld promotion" };
    if (path.startsWith("docs/contracts/")) return { call: "promote", authority: "MyWorld contract" };
    if (path.startsWith("docs/discoveries/")) return { call: "observe", authority: "MyWorld discovery" };
    if (path.startsWith("apps/control/")) return { call: "observe", authority: "Control UI schema" };
    return { call: "observe", authority: "AIOS artifact" };
  }

  function authorityBadge(value) {
    const info = artifactAuthority(value);
    const badge = document.createElement("span");
    badge.className = "authority-badge";
    badge.textContent = `${info.call} · ${info.authority}`;
    return badge;
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

  function artifactKind(path, payload) {
    const data = payload && payload.json;
    const schema = data && typeof data === "object" ? String(data.schema_version || data.schema || "") : "";
    if (schema.includes("visual_verification")) return "Visual verification";
    if (schema.includes("invocation_receipt")) return "Invocation receipt";
    if (schema.includes("session_envelope")) return "Session envelope";
    if (path.includes("/capability/") || path.includes("capability_route") || path.includes("route.json")) return "Capability route";
    if (path.includes("/memory/") || path.includes("context_pack")) return "Memory context";
    if (path.includes("gate_chair")) return "Gate Chair evidence";
    if (path.startsWith("docs/contracts/")) return "Smart contract";
    if (path.includes("screenshot") || path.endsWith(".png")) return "Visual artifact";
    return "AIOS artifact";
  }

  function artifactStatus(path, payload) {
    const data = payload && payload.json;
    if (data && typeof data === "object") {
      return data.status || data.overall_status || data.verdict || data.next_action || "recorded";
    }
    if (path.startsWith("docs/contracts/")) return "reviewable";
    return "preview";
  }

  function artifactNextAction(kind, payload) {
    const data = payload && payload.json;
    if (data && typeof data === "object") {
      if (data.next_action) return data.next_action;
      if (Array.isArray(data.stop_conditions) && data.stop_conditions.length) return `review ${data.stop_conditions[0]}`;
      if (data.status === "degraded") return "inspect degraded receipt";
      if (data.status === "passed") return "use as verification evidence";
    }
    if (kind === "Memory context") return "check selected memory provenance";
    if (kind === "Capability route") return "review chosen route and fallback";
    if (kind === "Smart contract") return "review status and acceptance gate";
    return "inspect artifact";
  }

  function artifactFacts(path, payload) {
    const data = payload && payload.json;
    const facts = [];
    if (data && typeof data === "object") {
      if (data.schema_version || data.schema) facts.push(["schema", data.schema_version || data.schema]);
      if (data.verification_id) facts.push(["verification", data.verification_id]);
      if (data.invocation_id) facts.push(["invocation", data.invocation_id]);
      if (data.trace_id) facts.push(["trace", data.trace_id]);
      if (data.screenshot_path) facts.push(["screenshot", data.screenshot_path]);
      if (Array.isArray(data.stop_conditions) && data.stop_conditions.length) facts.push(["stops", data.stop_conditions.slice(0, 3).join(" · ")]);
      if (data.cost_usd !== undefined) facts.push(["cost", `$${data.cost_usd}`]);
    }
    if (!facts.length) facts.push(["path", path]);
    return facts.slice(0, 5);
  }

  function renderArtifactSummary(path, payload, target) {
    const panel = target.closest(".artifact-evidence-desk, .artifact-hash-panel");
    if (!panel) return;
    let summary = panel.querySelector(".artifact-summary");
    if (!summary) {
      summary = document.createElement("div");
      summary.className = "artifact-summary";
      target.before(summary);
    }
    const kind = artifactKind(path, payload);
    const status = artifactStatus(path, payload);
    const next = artifactNextAction(kind, payload);
    const facts = artifactFacts(path, payload);
    const head = document.createElement("div");
    head.className = "artifact-summary-head";
    head.append(authorityBadge(path), document.createElement("strong"));
    head.querySelector("strong").textContent = kind;
    const state = document.createElement("span");
    state.className = `artifact-summary-state ${String(status).toLowerCase().replace(/[^a-z0-9_-]+/g, "-")}`;
    state.textContent = status;
    const factGrid = document.createElement("div");
    factGrid.className = "artifact-summary-facts";
    facts.forEach(([label, value]) => {
      const fact = document.createElement("span");
      fact.append(document.createElement("strong"), document.createTextNode(String(value || "")));
      fact.querySelector("strong").textContent = `${label}: `;
      factGrid.append(fact);
    });
    const action = document.createElement("small");
    action.className = "artifact-summary-action";
    action.textContent = `Next: ${next}`;
    summary.replaceChildren(head, state, factGrid, action);
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
      activeArtifactPath = payload.path || path;
      renderArtifactSummary(payload.path || path, payload, target);
      if (options.updateHash !== false) setArtifactHash(payload.path || path);
    } catch (_error) {
      target.textContent = "Artifact API unavailable";
    }
  }

  async function copyText(value, status) {
    try {
      await navigator.clipboard.writeText(String(value || ""));
      if (status) status.textContent = "Copied";
    } catch (_error) {
      if (status) status.textContent = "Copy unavailable";
    }
  }

  let historyItems = [];
  let activeHistoryFilter = "all";
  let visualWorkflow = null;
  let activeArtifactPath = "";

  function historyMatchesFilter(item) {
    if (activeHistoryFilter === "all") return true;
    return ((item && item.flags) || []).includes(activeHistoryFilter);
  }

  function historyFilterCounts(items) {
    return {
      all: items.length,
      provider_chair: items.filter((item) => (item.flags || []).includes("provider_chair")).length,
      internal: items.filter((item) => (item.flags || []).includes("internal")).length,
      memory_review_needed: items.filter((item) => (item.flags || []).includes("memory_review_needed")).length,
      failed_provider: items.filter((item) => (item.flags || []).includes("failed_provider")).length,
    };
  }

  function updateHistoryFilterLabels(counts) {
    document.querySelectorAll("[data-history-filter]").forEach((button) => {
      const filter = button.dataset.historyFilter || "all";
      const label = {
        all: "All",
        provider_chair: "Provider Chair",
        internal: "Internal",
        memory_review_needed: "Memory Review",
        failed_provider: "Failed Provider",
      }[filter] || filter;
      button.textContent = `${label} ${Number((counts || {})[filter] || 0)}`;
      button.setAttribute("aria-pressed", filter === activeHistoryFilter ? "true" : "false");
    });
  }

  async function runChatHistoryAction(item, action) {
    const conversationId = item && item.conversation_id;
    if (!conversationId) return;
    const label = action === "memory_rereview" ? "Memory review packet" : (action === "capability_fallback_preview" ? "Capability route preview" : "Capability fallback packet");
    setStatus(`${label} creating`);
    try {
      const response = await fetch("/api/chat_history_action", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ conversation_id: conversationId, action, confirm: action !== "capability_fallback_preview" }),
      });
      const payload = await response.json();
      if (!response.ok || !payload.ok) {
        setStatus(payload.reason || `${label} failed`);
        return;
      }
      if (action === "capability_fallback_preview") {
        const routePlan = payload.route_plan || {};
        const fallback = Array.isArray(routePlan.fallback_agents) ? routePlan.fallback_agents.join(" -> ") : "";
        const panel = artifactHashPanel();
        const pathLabel = panel.querySelector(".artifact-hash-path");
        const preview = panel.querySelector(".artifact-hash-preview");
        if (pathLabel) pathLabel.textContent = `CapabilityOS route preview: ${conversationId}`;
        if (preview) preview.textContent = JSON.stringify(routePlan, null, 2);
        setStatus(fallback ? `${label}: ${fallback}` : `${label} ready`);
        return;
      }
      const receipt = payload.receipt || {};
      const packet = (receipt.artifact_paths || {}).packet || "";
      setStatus(packet ? `${label} sent: ${packet}` : `${label} sent`);
      loadChatHistory();
    } catch (_error) {
      setStatus(`${label} API unavailable`);
    }
  }

  function renderChatHistory(items) {
    const list = qs("chat-history-list");
    if (!list) return;
    const visible = (items || []).filter(historyMatchesFilter);
    if (!visible.length) {
      list.replaceChildren();
      const empty = document.createElement("span");
      empty.className = "chat-history-empty";
      empty.textContent = activeHistoryFilter === "all" ? "No conversation history yet" : "No conversations match this filter";
      list.appendChild(empty);
      return;
    }
    list.replaceChildren();
    visible.slice(0, 12).forEach((item) => {
      const card = document.createElement("article");
      card.className = "chat-history-card";
      const title = document.createElement("button");
      title.type = "button";
      title.className = "chat-history-title";
      title.textContent = item.conversation_id || "conversation";
      title.addEventListener("click", () => {
        qs("chat-conversation").value = item.conversation_id || "web";
        setStatus(`Conversation ${item.conversation_id || "web"} selected`);
        qs("chat-input").focus();
      });
      const prompt = document.createElement("p");
      prompt.textContent = item.last_user_preview || "No user prompt";
      const chips = document.createElement("div");
      chips.className = "chat-history-chips";
      [
        historyChairLabel(item),
        [item.substrate, item.route_reason].filter(Boolean).join(" / "),
        `${Number(item.message_count || 0)} messages`,
        ...((item.flags || []).filter((flag) => flag !== "provider_chair").slice(0, 2)),
      ]
        .filter(Boolean)
        .forEach((value) => {
          const chip = document.createElement("span");
          chip.textContent = value;
          chips.appendChild(chip);
        });
      const artifacts = document.createElement("div");
      artifacts.className = "chat-history-artifacts";
      Object.entries(item.artifact_paths || {})
        .slice(0, 3)
        .forEach(([key, value]) => {
          const path = artifactPath(value);
          if (!path) return;
          const button = document.createElement("button");
          button.type = "button";
          button.textContent = key;
          button.addEventListener("click", () => {
            const panel = artifactHashPanel();
            const pathLabel = panel.querySelector(".artifact-hash-path");
            const preview = panel.querySelector(".artifact-hash-preview");
            if (pathLabel) pathLabel.textContent = path;
            if (preview) openArtifact(path, preview);
          });
          artifacts.appendChild(button);
        });
      if ((item.flags || []).includes("failed_provider")) {
        const preview = document.createElement("button");
        preview.type = "button";
        preview.textContent = "Preview";
        preview.addEventListener("click", () => runChatHistoryAction(item, "capability_fallback_preview"));
        artifacts.appendChild(preview);
        const fallback = document.createElement("button");
        fallback.type = "button";
        fallback.textContent = "Fallback";
        fallback.addEventListener("click", () => runChatHistoryAction(item, "capability_fallback_review"));
        artifacts.appendChild(fallback);
      }
      if ((item.flags || []).includes("memory_review_needed")) {
        const review = document.createElement("button");
        review.type = "button";
        review.textContent = "Review";
        review.addEventListener("click", () => runChatHistoryAction(item, "memory_rereview"));
        artifacts.appendChild(review);
      }
      card.append(title, prompt, chips, artifacts);
      list.appendChild(card);
    });
  }

  async function loadChatHistory() {
    const list = qs("chat-history-list");
    if (!list) return;
    list.replaceChildren();
    const loading = document.createElement("span");
    loading.className = "chat-history-empty";
    loading.textContent = "Loading history";
    list.appendChild(loading);
    try {
      const response = await fetch("/api/chat_history", { headers: { Accept: "application/json" } });
      const payload = await response.json();
      if (!response.ok || !payload.ok) {
        loading.textContent = payload.reason || "History unavailable";
        return;
      }
      historyItems = payload.items || [];
      updateHistoryFilterLabels(payload.counts || historyFilterCounts(historyItems));
      renderChatHistory(historyItems);
    } catch (_error) {
      loading.textContent = "History API unavailable";
    }
  }

  function visualWorkflowItem(kind) {
    const items = (visualWorkflow && visualWorkflow.items) || {};
    return items[kind] || null;
  }

  function showVisualWorkflowItem(kind) {
    const item = visualWorkflowItem(kind);
    if (!item) {
      setStatus(`Visual ${kind} unavailable`);
      return;
    }
    if (kind === "receipt") {
      const panel = artifactHashPanel();
      const pathLabel = panel.querySelector(".artifact-hash-path");
      const preview = panel.querySelector(".artifact-hash-preview");
      if (pathLabel) pathLabel.textContent = item.path || "visual receipt";
      if (preview && item.path) openArtifact(item.path, preview);
      return;
    }
    const preview = qs("visual-workflow-preview");
    const image = qs("visual-workflow-image");
    const caption = qs("visual-workflow-caption");
    if (!preview || !image || !caption) return;
    image.src = item.data_url || "";
    preview.hidden = !item.data_url;
    caption.textContent = item.path || `${kind} screenshot`;
    setStatus(`${kind} visual loaded`);
  }

  function renderVisualWorkflow(payload) {
    visualWorkflow = payload || null;
    const items = (visualWorkflow && visualWorkflow.items) || {};
    const evidence = qs("visual-workflow-evidence");
    const reference = items.reference || {};
    const after = items.after || {};
    const receipt = items.receipt || {};
    if (evidence) {
      const status = receipt.status ? `verify ${receipt.status}` : "verify pending";
      evidence.textContent = reference.path && after.path ? `${status} · ${after.path.split("/").pop()}` : "visual evidence missing";
    }
    document.querySelectorAll("[data-visual-open]").forEach((button) => {
      const kind = button.dataset.visualOpen || "";
      const available = Boolean(items[kind]);
      button.disabled = !available;
      button.classList.toggle("active", kind === "reference" && available);
    });
    if (reference.data_url) showVisualWorkflowItem("reference");
  }

  async function loadVisualWorkflow() {
    try {
      const response = await fetch("/api/visual_workflow", { headers: { Accept: "application/json" } });
      const payload = await response.json();
      if (!response.ok || !payload.ok) {
        const evidence = qs("visual-workflow-evidence");
        if (evidence) evidence.textContent = payload.reason || "visual workflow unavailable";
        return;
      }
      renderVisualWorkflow(payload);
    } catch (_error) {
      const evidence = qs("visual-workflow-evidence");
      if (evidence) evidence.textContent = "visual workflow API unavailable";
    }
  }

  function artifactHashPanel() {
    let panel = qs("artifact-evidence-desk") || qs("artifact-hash-panel");
    if (panel) {
      panel.classList.add("active");
      return panel;
    }
    panel = qs("artifact-hash-panel");
    if (panel) return panel;
    panel = document.createElement("aside");
    panel.id = "artifact-hash-panel";
    panel.className = "artifact-hash-panel";
    const head = document.createElement("div");
    head.className = "artifact-hash-head";
    const title = document.createElement("strong");
    title.textContent = "Artifact preview";
    const close = document.createElement("button");
    close.className = "artifact-hash-close";
    close.type = "button";
    close.textContent = "Close";
    close.addEventListener("click", () => {
      clearArtifactHash();
      panel.remove();
    });
    head.append(title, close);
    const pathLabel = document.createElement("small");
    pathLabel.className = "artifact-hash-path";
    const summary = document.createElement("div");
    summary.className = "artifact-summary";
    summary.textContent = "No artifact metadata yet.";
    const preview = document.createElement("pre");
    preview.className = "artifact-hash-preview";
    panel.append(head, pathLabel, summary, preview);
    document.body.append(panel);
    return panel;
  }

  function restoreArtifactHash() {
    const path = artifactFromHash();
    if (!path) {
      const existing = qs("artifact-hash-panel");
      if (existing) existing.remove();
      const desk = qs("artifact-evidence-desk");
      if (desk) {
        desk.classList.remove("active");
        const pathLabel = desk.querySelector(".artifact-hash-path");
        const summary = desk.querySelector(".artifact-summary");
        const preview = desk.querySelector(".artifact-hash-preview");
        const actionStatus = qs("evidence-desk-action-status");
        activeArtifactPath = "";
        if (pathLabel) pathLabel.textContent = "No artifact selected";
        if (summary) summary.textContent = "No artifact metadata yet.";
        if (actionStatus) actionStatus.textContent = "";
        if (preview) preview.textContent = "Open a route, receipt, memory pack, or screenshot verification artifact.";
      }
      return;
    }
    const panel = artifactHashPanel();
    const pathLabel = panel.querySelector(".artifact-hash-path");
    const preview = panel.querySelector(".artifact-hash-preview");
    if (pathLabel) pathLabel.textContent = path;
    if (preview) openArtifact(path, preview, { updateHash: false });
  }

  function appendEvidence(row, result) {
    const items = evidenceItems(result);
    if (!items.length) return;
    const details = document.createElement("details");
    details.className = "chat-evidence";
    const summary = document.createElement("summary");
    summary.textContent = `Trace ${items.length}`;
    details.appendChild(summary);
    const list = document.createElement("div");
    list.className = "chat-evidence-list";
    items.forEach((item) => {
      const entry = document.createElement("div");
      entry.className = "chat-evidence-item";
      const label = document.createElement("small");
      label.textContent = `${item.key}: ${item.value}`;
      entry.appendChild(label);
      const path = artifactPath(item.value);
      if (path) {
        const actions = document.createElement("div");
        actions.className = "chat-artifact-actions";
        const button = document.createElement("button");
        button.className = "chat-evidence-open";
        button.type = "button";
        button.textContent = "Open";
        const copyPath = document.createElement("button");
        copyPath.className = "chat-evidence-open";
        copyPath.type = "button";
        copyPath.textContent = "Copy path";
        const copyBody = document.createElement("button");
        copyBody.className = "chat-evidence-open";
        copyBody.type = "button";
        copyBody.textContent = "Copy preview";
        const status = document.createElement("small");
        status.className = "chat-copy-status";
        const preview = document.createElement("pre");
        preview.className = "chat-artifact-preview";
        button.addEventListener("click", () => openArtifact(path, preview));
        copyPath.addEventListener("click", () => copyText(path, status));
        copyBody.addEventListener("click", () => copyText(preview.textContent, status));
        actions.append(button, copyPath, copyBody, status);
        entry.append(authorityBadge(path), actions, preview);
        if (item.key === "friction_contract_seed") {
          const confirmLabel = document.createElement("label");
          confirmLabel.className = "promotion-confirm";
          const checkbox = document.createElement("input");
          checkbox.type = "checkbox";
          const confirmText = document.createElement("span");
          confirmText.textContent = "reviewed seed";
          confirmLabel.append(checkbox, confirmText);
          const promote = document.createElement("button");
          promote.className = "chat-evidence-open";
          promote.type = "button";
          promote.textContent = "Promote Seed";
          const promoteStatus = document.createElement("small");
          promoteStatus.className = "chat-copy-status";
          promote.addEventListener("click", async () => {
            if (!checkbox.checked) {
              promoteStatus.textContent = "Review confirmation required";
              checkbox.focus();
              return;
            }
            promote.disabled = true;
            promoteStatus.textContent = "Promoting";
            try {
              const response = await fetch("/api/promote_friction_seed", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ source_seed: path, confirm: true }),
              });
              const payload = await response.json();
              if (!response.ok || !payload.ok) {
                promoteStatus.textContent = payload.reason || "Promotion blocked";
                return;
              }
              const receipt = payload.receipt || {};
              const warnings = receipt.quality_warnings || [];
              promoteStatus.textContent = warnings.length
                ? `Promotion needs revision: ${warnings.slice(0, 2).join(", ")}`
                : `Promotion ready: ${receipt.promotion_id || "created"}`;
              const receiptPath = ((receipt.artifact_paths || {}).receipt) || "";
              if (receiptPath) {
                const materialize = document.createElement("div");
                materialize.className = "chat-materialize-contract";
                const input = document.createElement("input");
                input.type = "text";
                input.placeholder = "ASC-0200";
                input.setAttribute("aria-label", "ASC id for promoted route");
                const create = document.createElement("button");
                create.className = "chat-evidence-open";
                create.type = "button";
                create.textContent = "Create Contract";
                const createStatus = document.createElement("small");
                createStatus.className = "chat-copy-status";
                create.addEventListener("click", async () => {
                  const ascId = input.value.trim().toUpperCase();
                  if (!/^ASC-\d{4}$/.test(ascId)) {
                    createStatus.textContent = "Use ASC-0000 format";
                    input.focus();
                    return;
                  }
                  create.disabled = true;
                  createStatus.textContent = "Creating proposed contract";
                  try {
                    const response = await fetch("/api/materialize_promotion_contract", {
                      method: "POST",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({ promotion_receipt: receiptPath, asc_id: ascId, confirm: true }),
                    });
                    const materialized = await response.json();
                    if (!response.ok || !materialized.ok) {
                      createStatus.textContent = materialized.reason || "Contract creation blocked";
                      return;
                    }
                    const contract = (materialized.materialization || {}).contract_path || ascId;
                    createStatus.textContent = `Proposed ${contract}`;
                  } catch (_error) {
                    createStatus.textContent = "Materialization API unavailable";
                  } finally {
                    create.disabled = false;
                  }
                });
                materialize.append(input, create, createStatus);
                entry.append(materialize);
              }
            } catch (_error) {
              promoteStatus.textContent = "Promotion API unavailable";
            } finally {
              promote.disabled = false;
            }
          });
          entry.append(confirmLabel, promote, promoteStatus);
        }
        if (item.key === "route_promotion") {
          const confirmLabel = document.createElement("label");
          confirmLabel.className = "promotion-confirm";
          const checkbox = document.createElement("input");
          checkbox.type = "checkbox";
          const confirmText = document.createElement("span");
          confirmText.textContent = "reviewed route";
          confirmLabel.append(checkbox, confirmText);
          const promote = document.createElement("button");
          promote.className = "chat-evidence-open route-promote";
          promote.type = "button";
          promote.textContent = "Promote Route";
          const promoteStatus = document.createElement("small");
          promoteStatus.className = "chat-copy-status";
          promote.addEventListener("click", async () => {
            if (!checkbox.checked) {
              promoteStatus.textContent = "Review confirmation required";
              checkbox.focus();
              return;
            }
            promote.disabled = true;
            promoteStatus.textContent = "Promoting route";
            try {
              const response = await fetch("/api/promote_chat_route", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ invocation_receipt: path, confirm: true }),
              });
              const payload = await response.json();
              if (!response.ok || !payload.ok) {
                promoteStatus.textContent = payload.reason || "Route promotion blocked";
                return;
              }
              const receipt = payload.receipt || {};
              promoteStatus.textContent = `Promotion ready: ${receipt.promotion_id || "created"}`;
            } catch (_error) {
              promoteStatus.textContent = "Promotion API unavailable";
            } finally {
              promote.disabled = false;
            }
          });
          entry.append(confirmLabel, promote, promoteStatus);
        }
      }
      list.appendChild(entry);
    });
    details.appendChild(list);
    row.appendChild(details);
  }

  function cleanMarkdownText(value) {
    return String(value || "").replace(/\*\*/g, "").trim();
  }

  function appendParagraph(container, lines) {
    const text = cleanMarkdownText((lines || []).join(" "));
    if (!text) return;
    const paragraph = document.createElement("p");
    paragraph.textContent = text;
    container.appendChild(paragraph);
  }

  function renderMessageBody(text) {
    const body = document.createElement("div");
    body.className = "chat-message-body";
    const paragraphLines = [];
    let list = null;

    function flushParagraph() {
      appendParagraph(body, paragraphLines.splice(0));
    }

    function flushList() {
      list = null;
    }

    String(text || "")
      .split(/\r?\n/)
      .forEach((line) => {
        const trimmed = line.trim();
        if (!trimmed) {
          flushParagraph();
          flushList();
          return;
        }
        const heading = trimmed.match(/^#{1,3}\s+(.+)$/);
        if (heading) {
          flushParagraph();
          flushList();
          const title = document.createElement("h3");
          title.textContent = cleanMarkdownText(heading[1]);
          body.appendChild(title);
          return;
        }
        const bullet = trimmed.match(/^[-*]\s+(.+)$/);
        if (bullet) {
          flushParagraph();
          if (!list) {
            list = document.createElement("ul");
            body.appendChild(list);
          }
          const item = document.createElement("li");
          item.textContent = cleanMarkdownText(bullet[1]);
          list.appendChild(item);
          return;
        }
        flushList();
        paragraphLines.push(trimmed);
      });
    flushParagraph();
    return body;
  }

  function addMessage(role, text, meta, result) {
    const row = document.createElement("article");
    row.className = `chat-message ${role}`;

    const label = document.createElement("span");
    label.className = "chat-meta-label";
    label.textContent = role === "user" ? "You" : "AIOS";
    row.appendChild(label);

    row.appendChild(renderMessageBody(text));

    appendRuntimeStrip(row, result);

    if (meta && typeof meta === "string" && meta.trim()) {
      const detail = document.createElement("small");
      detail.className = "chat-meta-detail";
      detail.textContent = meta;
      row.appendChild(detail);
    }

    appendEvidence(row, result);
    if (role === "assistant") renderChatDecisionMap(result || {});

    qs("chat-thread").appendChild(row);
    qs("chat-thread").scrollTop = qs("chat-thread").scrollHeight;
  }

  function setStatus(next) {
    qs("chat-status").textContent = next;
  }

  let socket = null;
  let pending = false;
  let threadReady = false;

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

  function showGreetingBanner() {
    const thread = qs("chat-thread");
    while (thread.children.length) thread.firstChild.remove();
    const banner = document.createElement("article");
    banner.className = "chat-empty";
    banner.textContent = "준비되었어. 바로 물어봐.";
    thread.appendChild(banner);
  }

  function connect() {
    if (!("WebSocket" in window)) {
      setStatus("HTTP fallback");
      return;
    }
    socket = new WebSocket(wsUrl());
    socket.addEventListener("open", () => {
      setStatus("연결됨");
      if (!threadReady) {
        threadReady = true;
      }
    });
    socket.addEventListener("message", (event) => {
      let frame;
      try {
        frame = JSON.parse(event.data);
      } catch (_error) {
        setStatus("응답 형식이 올바르지 않음");
        return;
      }
      if (frame.type === "chat_ready") {
        setStatus("대화 가능");
        if (!threadReady) {
          showGreetingBanner();
        }
        return;
      }
      if (frame.type === "chat_error") {
        setStatus(frame.reason || "대화 에러");
        pending = false;
        return;
      }
      if (frame.type === "chat_response") {
        const result = frame.result || {};
        addMessage("assistant", result.response || "AIOS returned no text.", chatMeta(result), result);
        setStatus("대화 가능");
        pending = false;
      }
    });
    socket.addEventListener("close", () => {
      setStatus("HTTP fallback");
      pending = false;
      window.setTimeout(connect, 2000);
    });
    socket.addEventListener("error", () => {
      setStatus("HTTP fallback");
      pending = false;
    });
  }

  qs("chat-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const input = qs("chat-input");
    const message = input.value.trim();
    if (!message || pending) return;
    const thread = qs("chat-thread");
    if (thread.children.length === 1 && thread.firstElementChild && thread.firstElementChild.className === "chat-empty") {
      thread.firstElementChild.remove();
    }
    addMessage("user", message, "");
    const conversationId = qs("chat-conversation").value || "web";
    input.value = "";
    pending = true;
    setStatus("응답 생성 중");
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ message, conversation_id: conversationId }));
      return;
    }
    sendViaHttp(message, conversationId)
      .then((result) => {
        addMessage("assistant", result.response || "AIOS returned no text.", chatMeta(result), result);
        setStatus("대화 가능");
      })
      .catch(() => {
        setStatus("대화 실패");
      })
      .finally(() => {
        pending = false;
      });
  });

  document.querySelectorAll("[data-chat-prompt]").forEach((button) => {
    button.addEventListener("click", () => {
      const prompt = button.dataset.chatPrompt || "";
      if (!prompt) return;
      const input = qs("chat-input");
      input.value = prompt;
      input.focus();
    });
  });

  const historyRefresh = qs("chat-history-refresh");
  if (historyRefresh) historyRefresh.addEventListener("click", loadChatHistory);
  const evidenceClear = qs("evidence-desk-clear");
  if (evidenceClear) {
    evidenceClear.addEventListener("click", () => {
      clearArtifactHash();
      restoreArtifactHash();
    });
  }
  const evidenceAsk = qs("evidence-desk-ask");
  if (evidenceAsk) {
    evidenceAsk.addEventListener("click", () => {
      const path = activeArtifactPath || artifactFromHash();
      const status = qs("evidence-desk-action-status");
      if (!path) {
        if (status) status.textContent = "Open an artifact first";
        return;
      }
      const input = qs("chat-input");
      input.value = `이 artifact를 읽고 상태, 문제, 다음 행동을 요약해줘: ${path}`;
      input.focus();
      if (status) status.textContent = "Prompt prepared";
    });
  }
  const evidenceCopy = qs("evidence-desk-copy");
  if (evidenceCopy) {
    evidenceCopy.addEventListener("click", () => {
      const path = activeArtifactPath || artifactFromHash();
      const status = qs("evidence-desk-action-status");
      if (!path) {
        if (status) status.textContent = "Open an artifact first";
        return;
      }
      copyText(path, status);
    });
  }
  document.querySelectorAll("[data-visual-open]").forEach((button) => {
    button.addEventListener("click", () => showVisualWorkflowItem(button.dataset.visualOpen || "reference"));
  });
  document.querySelectorAll("[data-history-filter]").forEach((button) => {
    button.addEventListener("click", () => {
      activeHistoryFilter = button.dataset.historyFilter || "all";
      updateHistoryFilterLabels(historyFilterCounts(historyItems));
      renderChatHistory(historyItems);
    });
  });

  qs("chat-input").addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      qs("chat-form").dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
    }
  });

  renderChatDecisionMap({});
  renderOfflineUserPanel(controlSnapshot);
  connect();
  loadChatHistory();
  loadVisualWorkflow();
  restoreArtifactHash();
  window.addEventListener("hashchange", restoreArtifactHash);
})();

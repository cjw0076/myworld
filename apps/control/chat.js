(function () {
  function qs(id) {
    return document.getElementById(id);
  }

  function wsUrl() {
    const params = new URLSearchParams(window.location.search);
    if (params.get("ws")) return params.get("ws");
    const port = params.get("wsPort") || "8766";
    return `ws://${window.location.hostname || "127.0.0.1"}:${port}/chat`;
  }

  function chatMeta(result) {
    if (!result || typeof result !== "object") return "";
    const chair = result.gate_chair_status || {};
    const memory = result.memory_context || {};
    const memoryCount = Number(memory.context_items || 0);
    const substrate = result.chosen_substrate || "";
    return [
      "AIOS Gate",
      substrate === "aios_gate" ? "direct" : "",
      chair.attempted ? `Chair ${chair.mode || chair.status || "active"}` : "",
      memoryCount ? `MemoryOS ${memoryCount}` : "",
    ]
      .filter(Boolean)
      .join(" · ");
  }

  function evidenceItems(result) {
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
      items.push({ key: "gate_chair_status", value: `${chair.status || "unknown"} · executed=${Boolean(chair.executed)}` });
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

  function artifactHashPanel() {
    let panel = qs("artifact-hash-panel");
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
    const preview = document.createElement("pre");
    preview.className = "artifact-hash-preview";
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
      }
      list.appendChild(entry);
    });
    details.appendChild(list);
    row.appendChild(details);
  }

  function addMessage(role, text, meta, result) {
    const row = document.createElement("article");
    row.className = `chat-message ${role}`;

    const label = document.createElement("span");
    label.className = "chat-meta-label";
    label.textContent = role === "user" ? "You" : "AIOS";
    row.appendChild(label);

    const body = document.createElement("p");
    body.textContent = text;
    row.appendChild(body);

    if (meta && typeof meta === "string" && meta.trim()) {
      const detail = document.createElement("small");
      detail.className = "chat-meta-detail";
      detail.textContent = meta;
      row.appendChild(detail);
    }

    appendEvidence(row, result);

    qs("chat-thread").appendChild(row);
    qs("chat-thread").scrollTop = qs("chat-thread").scrollHeight;
  }

  function setStatus(next) {
    qs("chat-status").textContent = next;
  }

  let socket = null;
  let pending = false;
  let threadReady = false;

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
      setStatus("WebSocket unavailable");
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
      setStatus("연결 끊김, 재시도 중");
      pending = false;
      window.setTimeout(connect, 2000);
    });
    socket.addEventListener("error", () => {
      setStatus("연결 오류");
      pending = false;
    });
  }

  qs("chat-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const input = qs("chat-input");
    const message = input.value.trim();
    if (!message || !socket || socket.readyState !== WebSocket.OPEN || pending) return;
    const thread = qs("chat-thread");
    if (thread.children.length === 1 && thread.firstElementChild && thread.firstElementChild.className === "chat-empty") {
      thread.firstElementChild.remove();
    }
    addMessage("user", message, "");
    socket.send(JSON.stringify({ message, conversation_id: qs("chat-conversation").value || "web" }));
    input.value = "";
    pending = true;
    setStatus("응답 생성 중");
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

  qs("chat-input").addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      qs("chat-form").dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
    }
  });

  connect();
  restoreArtifactHash();
  window.addEventListener("hashchange", restoreArtifactHash);
})();

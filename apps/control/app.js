(function () {
  const snapshot = window.AIOS_CONTROL_SNAPSHOT;

  function qs(id) {
    return document.getElementById(id);
  }

  function text(value, fallback = "unknown") {
    return value === undefined || value === null || value === "" ? fallback : String(value);
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
      pill(text(evolution.readiness, "readiness unknown"), "pass"),
      pill(`Contracts ${text((data.contracts || {}).total, 0)}`, "active"),
      pill(`Dispatches ${text((data.dispatches || {}).total, 0)}`, "released"),
      pill(`Round ${text(round.status || round.latest_status, "observing")}`, "clear")
    );
  }

  function renderGoal(data) {
    const active = (data.goals || {}).active || {};
    const evolution = (data.goals || {}).evolution || {};
    qs("goal-title").textContent = active.slug
      ? `${active.slug}: ${text(evolution.recommendation, "no recommendation")}`
      : "AIOS control plane";
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

  function render(data) {
    if (!data) {
      qs("goal-title").textContent = "Snapshot missing";
      qs("status-strip").replaceChildren(pill("Run scripts/aios_control_snapshot.py", "held"));
      return;
    }
    renderGoal(data);
    renderStatus(data);
    renderLoopMap(data);
    renderContracts(data);
    renderDispatches(data);
    renderRepos(data);
    renderRoutes(data);
    renderStops(data);
  }

  render(snapshot);
})();

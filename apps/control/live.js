(function () {
  function qs(id) {
    return document.getElementById(id);
  }

  function wsUrl() {
    const params = new URLSearchParams(window.location.search);
    if (params.get("ws")) return params.get("ws");
    const port = params.get("wsPort") || "8766";
    return `ws://${window.location.hostname || "127.0.0.1"}:${port}/events`;
  }

  function connect() {
    if (!("WebSocket" in window)) {
      qs("live-status").textContent = "Live stream unavailable";
      return;
    }
    const socket = new WebSocket(wsUrl());
    socket.addEventListener("open", () => {
      qs("live-status").textContent = "Live stream connected";
    });
    socket.addEventListener("message", (event) => {
      try {
        window.AIOSControl.applyLiveFrame(JSON.parse(event.data));
      } catch (_error) {
        qs("live-status").textContent = "Live stream sent unreadable data";
      }
    });
    socket.addEventListener("close", () => {
      qs("live-status").textContent = "Live stream reconnecting";
      window.setTimeout(connect, 2000);
    });
    socket.addEventListener("error", () => {
      qs("live-status").textContent = "Live stream error";
    });
  }

  connect();
})();

(function () {
  function qs(id) {
    return document.getElementById(id);
  }

  function row(label, value) {
    const node = document.createElement("div");
    node.className = "goal-bar-row";
    const key = document.createElement("strong");
    key.textContent = label;
    const body = document.createElement("span");
    body.textContent = value || "";
    node.append(key, body);
    return node;
  }

  function renderResult(payload) {
    const result = qs("goal-bar-result");
    if (!result) return;
    result.replaceChildren();
    if (!payload) return;
    result.append(
      row("intent", payload.intent),
      row("command", payload.classified_command),
      row("reason", payload.reason)
    );
    if (payload.execution) {
      result.append(
        row("returncode", String(payload.execution.returncode)),
        row("stdout", payload.execution.stdout_tail || ""),
        row("stderr", payload.execution.stderr_tail || "")
      );
    }
  }

  async function postGoal(goal, execute) {
    const response = await fetch("/api/goal_bar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ goal, execute, confirm: execute }),
    });
    const payload = await response.json();
    if (!response.ok || !payload.ok) {
      throw new Error(payload.reason || "goal_bar_failed");
    }
    return payload.result;
  }

  function installGoalBar() {
    const form = qs("goal-bar-form");
    if (!form) return;
    const input = qs("goal-bar-input");
    const status = qs("goal-bar-status");
    const run = qs("goal-bar-run");
    let latestGoal = "";

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      latestGoal = input.value.trim();
      run.disabled = true;
      if (!latestGoal) {
        status.textContent = "Goal required";
        input.focus();
        return;
      }
      status.textContent = "Classifying";
      try {
        const result = await postGoal(latestGoal, false);
        renderResult(result);
        run.disabled = !result.will_execute;
        status.textContent = result.will_execute ? "Review command before running" : result.reason;
      } catch (error) {
        status.textContent = error.message;
      }
    });

    run.addEventListener("click", async () => {
      if (!latestGoal) return;
      run.disabled = true;
      status.textContent = "Running locally";
      try {
        const result = await postGoal(latestGoal, true);
        renderResult(result);
        status.textContent = result.execution && result.execution.ok ? "Completed" : "Command returned a problem";
      } catch (error) {
        status.textContent = error.message;
      } finally {
        run.disabled = false;
      }
    });
  }

  installGoalBar();
})();

const api = window.BOB_API_BASE || window.location.origin;
const healthEl = document.querySelector("#health");
const workspaceEl = document.querySelector("#workspace");
const chatEl = document.querySelector("#chat");
const pendingEl = document.querySelector("#pending");
const formEl = document.querySelector("#composer");
const messageEl = document.querySelector("#message");
const newChatEl = document.querySelector("#newChat");

function append(role, text) {
  if (!text) return;
  const node = document.createElement("div");
  node.className = `message ${role}`;
  node.textContent = text;
  chatEl.appendChild(node);
  chatEl.scrollTop = chatEl.scrollHeight;
}

async function json(path, options = {}) {
  const response = await fetch(api + path, {
    headers: {"Content-Type": "application/json"},
    ...options,
  });
  const payload = await response.json();
  if (!response.ok || payload.success === false) {
    throw new Error(payload.error || `HTTP ${response.status}`);
  }
  return payload;
}

function renderPending(items = []) {
  pendingEl.innerHTML = "";
  pendingEl.classList.toggle("hidden", items.length === 0);
  for (const item of items) {
    const card = document.createElement("div");
    card.className = "approval";
    const pre = document.createElement("pre");
    if (item.preview?.kind === "diff") {
      pre.textContent = item.preview.diff || "(empty diff)";
    } else {
      pre.textContent = JSON.stringify({
        tool: item.tool,
        effect_class: item.effect_class,
        args: item.args,
        preview: item.preview,
      }, null, 2);
    }
    const button = document.createElement("button");
    button.textContent = "Approve";
    button.onclick = async () => {
      button.disabled = true;
      try {
        const result = await json("/bob/approve", {
          method: "POST",
          body: JSON.stringify({pending_id: item.pending_id}),
        });
        renderResult(result);
      } catch (error) {
        append("system", error.message);
        button.disabled = false;
      }
    };
    card.append(pre, button);
    pendingEl.appendChild(card);
  }
}

function renderResult(result) {
  for (const text of result.visible_messages || []) append("assistant", text);
  renderPending(result.pending || []);
  if (result.status === "ASK_USER" && result.terminal?.args?.question) {
    append("assistant", result.terminal.args.question);
  }
}

async function boot() {
  try {
    const health = await json("/bob/health");
    healthEl.textContent = "online";
    healthEl.classList.add("ok");
    const workspaces = await json("/bob/workspaces");
    workspaceEl.innerHTML = "";
    for (const ws of workspaces.workspaces) {
      const option = document.createElement("option");
      option.value = ws.code;
      option.textContent = `${ws.name} (${ws.code})`;
      workspaceEl.appendChild(option);
    }
    if (!workspaces.workspaces.length) {
      append("system", "No configured workspaces. Add a JSON file under workspaces/.");
    }
  } catch (error) {
    healthEl.textContent = "offline";
    append("system", error.message);
  }
}

formEl.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = messageEl.value.trim();
  if (!message || !workspaceEl.value) return;
  append("human", message);
  messageEl.value = "";
  try {
    const result = await json("/bob/turn", {
      method: "POST",
      body: JSON.stringify({workspace: workspaceEl.value, message}),
    });
    renderResult(result);
  } catch (error) {
    append("system", error.message);
  }
});

newChatEl.addEventListener("click", async () => {
  if (!workspaceEl.value) return;
  try {
    await json("/bob/new-chat", {
      method: "POST",
      body: JSON.stringify({workspace: workspaceEl.value}),
    });
    chatEl.innerHTML = "";
    renderPending([]);
    append("system", "New ChatGPT conversation started.");
  } catch (error) {
    append("system", error.message);
  }
});

boot();

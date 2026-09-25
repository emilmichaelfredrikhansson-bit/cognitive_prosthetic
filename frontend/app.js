const api = window.BOB_API_BASE || window.location.origin;

const appEl = document.querySelector("#app");
const sidebarOpenEl = document.querySelector("#sidebarOpen");
const sidebarCloseEl = document.querySelector("#sidebarClose");
const sidebarFilterEl = document.querySelector("#sidebarFilter");
const projectListEl = document.querySelector("#projectList");
const newChatEl = document.querySelector("#newChat");
const healthDotEl = document.querySelector("#healthDot");
const healthLabelEl = document.querySelector("#healthLabel");
const healthDetailEl = document.querySelector("#healthDetail");
const projectNameEl = document.querySelector("#projectName");
const projectMetaEl = document.querySelector("#projectMeta");
const verifyWorkspaceEl = document.querySelector("#verifyWorkspace");
const qualificationBannerEl = document.querySelector("#qualificationBanner");
const inspectorToggleEl = document.querySelector("#inspectorToggle");
const inspectorCloseEl = document.querySelector("#inspectorClose");
const inspectorTitleEl = document.querySelector("#inspectorTitle");
const realityBadgeEl = document.querySelector("#realityBadge");
const realityChecksEl = document.querySelector("#realityChecks");
const authorityListEl = document.querySelector("#authorityList");
const providerListEl = document.querySelector("#providerList");
const contextDocsEl = document.querySelector("#contextDocs");
const settingsListEl = document.querySelector("#settingsList");
const projectSearchEl = document.querySelector("#projectSearch");
const projectSearchDialogEl = document.querySelector("#projectSearchDialog");
const projectSearchCloseEl = document.querySelector("#projectSearchClose");
const projectSearchFormEl = document.querySelector("#projectSearchForm");
const projectSearchInputEl = document.querySelector("#projectSearchInput");
const projectSearchTitleEl = document.querySelector("#projectSearchTitle");
const projectSearchMetaEl = document.querySelector("#projectSearchMeta");
const projectSearchResultsEl = document.querySelector("#projectSearchResults");
const approvalInboxEl = document.querySelector("#approvalInbox");
const approvalCountEl = document.querySelector("#approvalCount");
const chatEl = document.querySelector("#chat");
const emptyStateEl = document.querySelector("#emptyState");
const pendingEl = document.querySelector("#pending");
const formEl = document.querySelector("#composer");
const messageEl = document.querySelector("#message");
const sendButtonEl = document.querySelector("#sendButton");
const scrimEl = document.querySelector("#scrim");
const recentLabelEl = document.querySelector(".recent-item .truncate");
const themeToggleEl = document.querySelector("#themeToggle");
const themeLabelEl = document.querySelector("#themeLabel");
const documentViewerEl = document.querySelector("#documentViewer");
const documentTitleEl = document.querySelector("#documentTitle");
const documentPathEl = document.querySelector("#documentPath");
const documentContentEl = document.querySelector("#documentContent");
const documentCloseEl = document.querySelector("#documentClose");

const state = {
  health: null,
  workspaces: [],
  selectedCode: null,
  qualifications: new Map(),
  pending: [],
  messages: [],
  busy: false,
};

const authorityLabels = {
  write_branch: ["Branch writes", "Create or change files on an approved branch"],
  open_pr: ["Pull requests", "Open a pull request after approval"],
  mutate_production_state: ["Production mutation", "Change production database/application state"],
  material_spend: ["Material spend", "Start paid compute or another spend-bearing effect"],
  deploy: ["Deploy", "Change a live deployment"],
};

const providerLabels = {
  github: "GitHub",
  supabase: "Supabase",
  hugging_face: "Hugging Face",
  cloudflare: "Cloudflare",
};

function createElement(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = text;
  return node;
}

async function json(path, options = {}) {
  const response = await fetch(api + path, {
    headers: {"Content-Type": "application/json"},
    ...options,
  });
  let payload;
  try {
    payload = await response.json();
  } catch (_error) {
    throw new Error(`HTTP ${response.status}`);
  }
  if (!response.ok || payload.success === false) {
    throw new Error(payload.error || `HTTP ${response.status}`);
  }
  return payload;
}

function setBusy(value) {
  state.busy = value;
  sendButtonEl.disabled = value;
  messageEl.disabled = value;
}

function updateEmptyState() {
  emptyStateEl.classList.toggle("hidden", state.messages.length > 0);
}

function appendMessage(role, text) {
  if (!text) return;
  state.messages.push({role, text});
  updateEmptyState();

  const row = createElement("article", `message-row ${role}`);
  const avatar = createElement("div", "message-avatar", role === "assistant" ? "B" : role === "human" ? "You" : "i");
  const body = createElement("div", "message-body");

  if (role !== "system") {
    body.appendChild(createElement("span", "message-role", role === "assistant" ? "Bob" : "You"));
  }
  body.appendChild(document.createTextNode(text));
  row.append(avatar, body);
  chatEl.appendChild(row);
  chatEl.scrollTop = chatEl.scrollHeight;

  if (role === "human" && state.messages.filter((item) => item.role === "human").length === 1) {
    recentLabelEl.textContent = text.length > 34 ? `${text.slice(0, 34)}…` : text;
  }
}

function clearConversation() {
  state.messages = [];
  state.pending = [];
  for (const child of [...chatEl.children]) {
    if (child !== emptyStateEl) child.remove();
  }
  recentLabelEl.textContent = "Current conversation";
  renderPending([]);
  updateEmptyState();
}

function workspaceByCode(code) {
  return state.workspaces.find((workspace) => workspace.code === code) || null;
}

function renderProjects(filter = "") {
  const query = filter.trim().toLowerCase();
  projectListEl.innerHTML = "";
  const workspaces = state.workspaces.filter((workspace) => {
    if (!query) return true;
    return [workspace.name, workspace.code, workspace.github?.repository]
      .filter(Boolean)
      .some((value) => String(value).toLowerCase().includes(query));
  });

  for (const workspace of workspaces) {
    const button = createElement("button", `project-button${workspace.code === state.selectedCode ? " active" : ""}`);
    button.type = "button";
    button.dataset.workspace = workspace.code;
    const icon = createElement("span", "project-icon", workspace.code.slice(0, 2).toUpperCase());
    const copy = createElement("span", "project-copy");
    copy.append(
      createElement("strong", "truncate", workspace.name),
      createElement("span", "truncate", workspace.github?.repository || workspace.code),
    );
    button.append(icon, copy);
    button.addEventListener("click", () => selectWorkspace(workspace.code));
    projectListEl.appendChild(button);
  }

  if (!workspaces.length) {
    projectListEl.appendChild(createElement("p", "sidebar-note", "No matching projects."));
  }
}

function providerSummary(key, config) {
  if (key === "github") return config?.repository || "Repository binding";
  if (key === "supabase") return config?.project_id ? `Project ${config.project_id}` : "Project binding";
  if (key === "hugging_face") return config?.namespace ? `Namespace ${config.namespace}` : "Account binding";
  if (key === "cloudflare") {
    if (config?.identity_anchor_r2_bucket) return `R2 · ${config.identity_anchor_r2_bucket}`;
    if (config?.worker_script) return `Worker · ${config.worker_script}`;
    if (config?.project_name || config?.resource) return `Pages · ${config.project_name || config.resource}`;
  }
  return "Configured binding";
}

function renderWorkspaceInspector(workspace) {
  if (!workspace) return;
  inspectorTitleEl.textContent = workspace.name;
  projectNameEl.textContent = workspace.name;
  projectMetaEl.textContent = workspace.github?.repository || workspace.code;
  projectSearchTitleEl.textContent = `Search ${workspace.name}`;

  settingsListEl.innerHTML = "";
  const settings = [
    ["Project code", workspace.code],
    ["Repository", workspace.github?.repository || "Not configured"],
    ["Repository ID", workspace.github?.repository_id ? String(workspace.github.repository_id) : "Not configured"],
    ["Default branch", workspace.github?.default_branch || "main"],
  ];
  for (const [label, value] of settings) {
    const row = createElement("div", "settings-item");
    const copy = createElement("span", "item-copy");
    copy.append(createElement("strong", null, label), createElement("span", null, value));
    row.appendChild(copy);
    settingsListEl.appendChild(row);
  }
  const instructionsPath = (workspace.entry_documents || []).find((path) => /CHATGPT.*PROJECT.*INSTRUCTIONS/i.test(path));
  if (instructionsPath) {
    const row = createElement("button", "settings-item settings-button");
    row.type = "button";
    const copy = createElement("span", "item-copy");
    copy.append(createElement("strong", null, "ChatGPT Project instructions"), createElement("span", null, instructionsPath));
    row.append(copy, createElement("span", "context-open", "Open"));
    row.addEventListener("click", () => openDocument(instructionsPath));
    settingsListEl.appendChild(row);
  }

  authorityListEl.innerHTML = "";
  const effects = workspace.effects || {};
  for (const key of Object.keys(authorityLabels)) {
    const allowed = Boolean(effects[key]);
    const [label, description] = authorityLabels[key];
    const row = createElement("div", "authority-item");
    const copy = createElement("span", "item-copy");
    copy.append(createElement("strong", null, label), createElement("span", null, description));
    row.append(copy, createElement("span", `state ${allowed ? "allowed" : "blocked"}`, allowed ? "Allowed" : "Blocked"));
    authorityListEl.appendChild(row);
  }

  providerListEl.innerHTML = "";
  const providerEntries = [["github", workspace.github || {}], ...Object.entries(workspace.providers || {})];
  for (const [key, config] of providerEntries) {
    const row = createElement("div", "provider-item");
    const copy = createElement("span", "item-copy");
    copy.append(
      createElement("strong", null, providerLabels[key] || key),
      createElement("span", null, providerSummary(key, config)),
    );
    const qualification = state.qualifications.get(workspace.code);
    const checkKey = key === "hugging_face" ? "hf" : key;
    const status = qualification?.checks?.[checkKey]?.status;
    row.append(copy, createElement("span", `state ${status ? status.toLowerCase() : "unavailable"}`, status || "Unchecked"));
    providerListEl.appendChild(row);
  }

  contextDocsEl.innerHTML = "";
  const docs = workspace.entry_documents || [];
  if (!docs.length) {
    contextDocsEl.appendChild(createElement("p", "muted", "No entry documents configured."));
  } else {
    for (const path of docs) {
      const row = createElement("button", "context-item context-button");
      row.type = "button";
      const copy = createElement("span", "item-copy");
      copy.append(createElement("strong", null, path.split("/").pop()), createElement("span", null, path));
      row.append(copy, createElement("span", "context-open", "Open"));
      row.addEventListener("click", () => openDocument(path));
      contextDocsEl.appendChild(row);
    }
  }

  renderQualification(state.qualifications.get(workspace.code) || null, false);
}

function selectWorkspace(code) {
  const workspace = workspaceByCode(code);
  if (!workspace) return;
  const changed = state.selectedCode && state.selectedCode !== code;
  state.selectedCode = code;
  localStorage.setItem("bob.workspace", code);
  renderProjects(sidebarFilterEl.value);
  renderWorkspaceInspector(workspace);

  if (changed && state.messages.length) {
    appendMessage("system", `Project changed to ${workspace.name}. Bob will attach this workspace's authority and reality packet on the next turn.`);
  }
  closeSidebar();
}

function checkDescription(name, item) {
  const data = item?.data || {};
  if (name === "github" && data.repository) return data.repository;
  if (name === "supabase" && data.project_id) return data.project_id;
  if (name === "hf" && (data.name || data.namespace)) return data.name || data.namespace;
  if (name === "cloudflare" && data.identity_anchor) {
    return data.identity_anchor.bucket || data.identity_anchor.worker_script || data.identity_anchor.project_name || "Identity anchor";
  }
  return item?.error || "Identity check";
}

function renderQualification(result, showBanner = true) {
  realityChecksEl.innerHTML = "";
  realityBadgeEl.className = "mini-badge neutral";
  realityBadgeEl.textContent = "Not checked";

  if (!result) {
    realityChecksEl.appendChild(createElement("p", "muted", "Verify this workspace to read external identities."));
    if (showBanner) qualificationBannerEl.classList.add("hidden");
    return;
  }

  realityBadgeEl.className = `mini-badge ${result.qualified ? "pass" : "fail"}`;
  realityBadgeEl.textContent = result.qualified ? "Verified" : "Not qualified";

  for (const [name, item] of Object.entries(result.checks || {})) {
    const row = createElement("div", "status-item");
    const copy = createElement("span", "item-copy");
    copy.append(
      createElement("strong", null, providerLabels[name === "hf" ? "hugging_face" : name] || name),
      createElement("span", null, checkDescription(name, item)),
    );
    row.append(copy, createElement("span", `state ${(item.status || "unavailable").toLowerCase()}`, item.status || "Unknown"));
    realityChecksEl.appendChild(row);
  }

  if (showBanner) {
    qualificationBannerEl.className = `qualification-banner ${result.qualified ? "pass" : "fail"}`;
    qualificationBannerEl.textContent = result.qualified
      ? "Project reality verified against every configured provider."
      : "Project is not fully qualified. Open Project to see which identity check failed or is unavailable.";
  }
}

function approvalPreview(item) {
  if (item.preview?.kind === "diff") return item.preview.diff || "(empty diff)";
  return JSON.stringify({
    tool: item.tool,
    effect_class: item.effect_class,
    args: item.args,
    preview: item.preview,
    candidate_hash: item.candidate_hash,
  }, null, 2);
}

function renderPending(items = []) {
  state.pending = items;
  pendingEl.innerHTML = "";
  pendingEl.classList.toggle("hidden", items.length === 0);
  approvalCountEl.textContent = String(items.length);
  approvalInboxEl.classList.toggle("hidden", items.length === 0);

  for (const item of items) {
    const card = createElement("article", "approval");
    const head = createElement("div", "approval-head");
    const title = createElement("div", "approval-title");
    title.append(
      createElement("strong", null, "Bob needs your approval"),
      createElement("span", null, `${item.effect_class || "effect"} · ${item.tool || "unknown tool"}`),
    );
    head.append(title, createElement("span", "mini-badge neutral", "Pending"));

    const pre = createElement("pre", null, approvalPreview(item));
    const actions = createElement("div", "approval-actions");
    const reject = createElement("button", "approval-button", "Reject");
    const approve = createElement("button", "approval-button primary", "Approve");
    reject.type = approve.type = "button";

    reject.addEventListener("click", async () => {
      reject.disabled = approve.disabled = true;
      try {
        await json("/bob/reject", {
          method: "POST",
          body: JSON.stringify({pending_id: item.pending_id}),
        });
        appendMessage("system", `Rejected ${item.tool}. No external effect was executed.`);
        renderPending(state.pending.filter((pending) => pending.pending_id !== item.pending_id));
      } catch (error) {
        appendMessage("system", error.message);
        reject.disabled = approve.disabled = false;
      }
    });

    approve.addEventListener("click", async () => {
      reject.disabled = approve.disabled = true;
      try {
        const result = await json("/bob/approve", {
          method: "POST",
          body: JSON.stringify({pending_id: item.pending_id}),
        });
        renderResult(result);
      } catch (error) {
        appendMessage("system", error.message);
        reject.disabled = approve.disabled = false;
      }
    });

    actions.append(reject, approve);
    card.append(head, pre, actions);
    pendingEl.appendChild(card);
  }
}

function renderActivity(rounds = []) {
  const reads = rounds.flatMap((round) => round.reads || []);
  if (!reads.length) return;
  const details = createElement("details", "activity-row");
  const summary = createElement("summary", null, `Checked project reality · ${reads.length} read${reads.length === 1 ? "" : "s"}`);
  const list = createElement("div", "activity-list");
  for (const read of reads) {
    const row = createElement("div", "activity-item");
    row.append(
      createElement("span", null, read.tool || "read"),
      createElement("span", `state ${(read.status || "fail").toLowerCase()}`, read.status || "Unknown"),
    );
    list.appendChild(row);
  }
  details.append(summary, list);
  chatEl.appendChild(details);
  chatEl.scrollTop = chatEl.scrollHeight;
}

function renderResult(result) {
  for (const text of result.visible_messages || []) appendMessage("assistant", text);
  renderActivity(result.tool_rounds || []);
  renderPending(result.pending || []);
  if (result.status === "ASK_USER" && result.terminal?.args?.question) {
    appendMessage("assistant", result.terminal.args.question);
  }
}

function autoResize() {
  messageEl.style.height = "auto";
  messageEl.style.height = `${Math.min(messageEl.scrollHeight, 180)}px`;
}

async function sendMessage(rawMessage) {
  const message = String(rawMessage || "").trim();
  if (!message || !state.selectedCode || state.busy) return;
  appendMessage("human", message);
  messageEl.value = "";
  autoResize();
  setBusy(true);
  try {
    const result = await json("/bob/turn", {
      method: "POST",
      body: JSON.stringify({workspace: state.selectedCode, message}),
    });
    renderResult(result);
  } catch (error) {
    appendMessage("system", error.message);
  } finally {
    setBusy(false);
    messageEl.focus();
  }
}

function openInspector() {
  appEl.classList.add("inspector-open");
  inspectorToggleEl.setAttribute("aria-expanded", "true");
  syncScrim();
}
function closeInspector() {
  appEl.classList.remove("inspector-open");
  inspectorToggleEl.setAttribute("aria-expanded", "false");
  syncScrim();
}
function openSidebar() {
  appEl.classList.add("sidebar-open");
  syncScrim();
}
function closeSidebar() {
  appEl.classList.remove("sidebar-open");
  syncScrim();
}
function syncScrim() {
  const sidebarNeedsScrim = window.matchMedia("(max-width: 760px)").matches && appEl.classList.contains("sidebar-open");
  const inspectorNeedsScrim = window.matchMedia("(max-width: 1060px)").matches && appEl.classList.contains("inspector-open");
  scrimEl.classList.toggle("hidden", !(sidebarNeedsScrim || inspectorNeedsScrim));
}

async function verifyWorkspace() {
  if (!state.selectedCode) return;
  verifyWorkspaceEl.disabled = true;
  const oldLabel = verifyWorkspaceEl.textContent;
  verifyWorkspaceEl.textContent = "Verifying…";
  qualificationBannerEl.className = "qualification-banner pending";
  qualificationBannerEl.textContent = "Reading bound external identities…";
  try {
    const result = await json("/bob/qualify", {
      method: "POST",
      body: JSON.stringify({workspace: state.selectedCode}),
    });
    state.qualifications.set(state.selectedCode, result);
    renderQualification(result, true);
    renderWorkspaceInspector(workspaceByCode(state.selectedCode));
  } catch (error) {
    qualificationBannerEl.className = "qualification-banner fail";
    qualificationBannerEl.textContent = error.message;
  } finally {
    verifyWorkspaceEl.disabled = false;
    verifyWorkspaceEl.textContent = oldLabel;
  }
}

function openProjectSearch() {
  if (!state.selectedCode) return;
  closeSidebar();
  projectSearchResultsEl.innerHTML = "";
  projectSearchMetaEl.textContent = "Searches only configured entry documents through bounded Bob reads.";
  projectSearchDialogEl.showModal();
  window.setTimeout(() => projectSearchInputEl.focus(), 0);
}

function renderProjectSearchResults(payload) {
  projectSearchResultsEl.innerHTML = "";
  const reads = payload.reads || [];
  const passed = reads.filter((item) => item.status === "PASS").length;
  const failed = reads.filter((item) => item.status === "FAIL").length;
  const suffix = payload.truncated ? " · limited results" : "";
  projectSearchMetaEl.textContent = `${payload.total_matches || 0} match${payload.total_matches === 1 ? "" : "es"} · ${passed} READ PASS${failed ? ` · ${failed} READ FAIL` : ""}${suffix}`;

  if (!(payload.results || []).length) {
    projectSearchResultsEl.appendChild(createElement("p", "search-empty", "No matches in configured project context."));
  } else {
    for (const result of payload.results) {
      const button = createElement("button", "search-result");
      button.type = "button";
      const head = createElement("span", "search-result-head");
      head.append(
        createElement("strong", null, result.path),
        createElement("span", null, `Line ${result.line}`),
      );
      button.append(head, createElement("span", "search-snippet", result.snippet || ""));
      button.addEventListener("click", () => {
        projectSearchDialogEl.close();
        openDocument(result.path);
      });
      projectSearchResultsEl.appendChild(button);
    }
  }

  for (const read of reads.filter((item) => item.status === "FAIL")) {
    const failure = createElement("div", "search-read-failure");
    failure.append(
      createElement("strong", null, `READ FAIL · ${read.path}`),
      createElement("span", null, read.error || "Project context read failed"),
    );
    projectSearchResultsEl.appendChild(failure);
  }
}

async function searchProjectContext(query) {
  const value = String(query || "").trim();
  if (!state.selectedCode || value.length < 2) {
    projectSearchMetaEl.textContent = "Type at least 2 characters. Search is limited to configured entry documents.";
    return;
  }
  const submit = projectSearchFormEl.querySelector("button[type=submit]");
  submit.disabled = true;
  projectSearchInputEl.disabled = true;
  projectSearchMetaEl.textContent = "Reading configured project context…";
  projectSearchResultsEl.innerHTML = "";
  try {
    const payload = await json("/bob/project-search", {
      method: "POST",
      body: JSON.stringify({workspace: state.selectedCode, query: value, limit: 20}),
    });
    renderProjectSearchResults(payload);
  } catch (error) {
    projectSearchMetaEl.textContent = error.message;
  } finally {
    submit.disabled = false;
    projectSearchInputEl.disabled = false;
    projectSearchInputEl.focus();
  }
}

async function openDocument(path) {
  if (!state.selectedCode || !path) return;
  documentTitleEl.textContent = path.split("/").pop();
  documentPathEl.textContent = path;
  documentContentEl.textContent = "Reading project file…";
  documentViewerEl.showModal();
  try {
    const payload = await json("/bob/read", {
      method: "POST",
      body: JSON.stringify({workspace: state.selectedCode, tool: "github.read_file", args: {path}}),
    });
    documentContentEl.textContent = payload.result?.content || "(empty file)";
  } catch (error) {
    documentContentEl.textContent = `Could not read ${path}.\n\n${error.message}`;
  }
}

function setTheme(theme) {
  const resolved = theme === "dark" || theme === "light" ? theme : "system";
  if (resolved === "system") {
    document.body.dataset.theme = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  } else {
    document.body.dataset.theme = resolved;
  }
  localStorage.setItem("bob.theme", resolved);
  themeLabelEl.textContent = resolved[0].toUpperCase() + resolved.slice(1);
}

function cycleTheme() {
  const current = localStorage.getItem("bob.theme") || "system";
  const next = current === "system" ? "light" : current === "light" ? "dark" : "system";
  setTheme(next);
}

async function newChat() {
  if (!state.selectedCode) return;
  newChatEl.disabled = true;
  try {
    await json("/bob/new-chat", {
      method: "POST",
      body: JSON.stringify({workspace: state.selectedCode}),
    });
    clearConversation();
  } catch (error) {
    appendMessage("system", error.message);
  } finally {
    newChatEl.disabled = false;
  }
}

async function boot() {
  setTheme(localStorage.getItem("bob.theme") || "system");
  try {
    const health = await json("/bob/health");
    state.health = health;
    healthDotEl.classList.add("ok");
    healthLabelEl.textContent = "Online";
    const adapterCount = Object.keys(health.capabilities || {}).length;
    healthDetailEl.textContent = `${adapterCount} adapter${adapterCount === 1 ? "" : "s"} available`;

    const workspaces = await json("/bob/workspaces");
    state.workspaces = workspaces.workspaces || [];
    const remembered = localStorage.getItem("bob.workspace");
    const defaultWorkspace = state.workspaces.find((workspace) => workspace.code === remembered)
      || state.workspaces.find((workspace) => workspace.code === "BOB")
      || state.workspaces[0];

    renderProjects();
    if (defaultWorkspace) {
      selectWorkspace(defaultWorkspace.code);
    } else {
      projectNameEl.textContent = "No projects";
      projectMetaEl.textContent = "Add a workspace JSON file to continue";
      appendMessage("system", "No configured workspaces. Add a JSON file under workspaces/.");
      messageEl.disabled = sendButtonEl.disabled = true;
    }
  } catch (error) {
    healthDotEl.classList.add("fail");
    healthLabelEl.textContent = "Offline";
    healthDetailEl.textContent = "Bob runtime unavailable";
    appendMessage("system", error.message);
  }
}

formEl.addEventListener("submit", (event) => {
  event.preventDefault();
  sendMessage(messageEl.value);
});
messageEl.addEventListener("input", autoResize);
messageEl.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    formEl.requestSubmit();
  }
});
for (const starter of document.querySelectorAll(".starter")) {
  starter.addEventListener("click", () => sendMessage(starter.dataset.prompt));
}

verifyWorkspaceEl.addEventListener("click", verifyWorkspace);
projectSearchEl.addEventListener("click", openProjectSearch);
projectSearchFormEl.addEventListener("submit", (event) => {
  event.preventDefault();
  searchProjectContext(projectSearchInputEl.value);
});
projectSearchCloseEl.addEventListener("click", () => projectSearchDialogEl.close());
projectSearchDialogEl.addEventListener("click", (event) => {
  if (event.target === projectSearchDialogEl) projectSearchDialogEl.close();
});
approvalInboxEl.addEventListener("click", () => {
  pendingEl.scrollIntoView({behavior: "smooth", block: "center"});
  pendingEl.querySelector("button")?.focus({preventScroll: true});
});
newChatEl.addEventListener("click", newChat);
sidebarFilterEl.addEventListener("input", () => renderProjects(sidebarFilterEl.value));
inspectorToggleEl.addEventListener("click", () => {
  if (appEl.classList.contains("inspector-open")) closeInspector(); else openInspector();
});
inspectorCloseEl.addEventListener("click", closeInspector);
sidebarOpenEl.addEventListener("click", openSidebar);
sidebarCloseEl.addEventListener("click", closeSidebar);
scrimEl.addEventListener("click", () => {
  closeSidebar();
  closeInspector();
});
themeToggleEl.addEventListener("click", cycleTheme);
documentCloseEl.addEventListener("click", () => documentViewerEl.close());
documentViewerEl.addEventListener("click", (event) => {
  if (event.target === documentViewerEl) documentViewerEl.close();
});
window.addEventListener("resize", syncScrim);

document.addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
    event.preventDefault();
    if (!projectSearchDialogEl.open) openProjectSearch();
  }
  if (event.key === "Escape") {
    closeSidebar();
    closeInspector();
  }
});

boot();

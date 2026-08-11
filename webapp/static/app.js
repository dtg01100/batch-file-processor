"use strict";

/* Batch File Sender webapp — dashboard logic (vanilla JS). */

const $ = (id) => document.getElementById(id);

const state = {
  config: null,
  pollHandle: null,
  lastRunId: null,
  editingFolderId: null,
};

async function api(path, options) {
  const resp = await fetch(path, options);
  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const body = await resp.json();
      detail = body.detail || detail;
    } catch (_e) { /* non-JSON error body */ }
    const err = new Error(detail);
    err.status = resp.status;
    throw err;
  }
  return resp.json();
}

const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));

/* ---------------- health + config ---------------- */

async function refreshConfig() {
  try {
    const [health, config, sched] = await Promise.all([
      api("/api/health"),
      api("/api/config"),
      api("/api/schedule").catch(() => null),
    ]);
    state.config = config;
    $("health-dot").className = "dot " + (health.status === "ok" ? "ok" : "err");
    $("base-dir-pill").textContent = "base: " + config.base_dir;
    if (config.imported_base_dir && !$("import-base-dir").value) {
      $("import-base-dir").value = config.imported_base_dir;
    }
    $("run-btn").disabled = !config.database_exists || config.active_count === 0;
    if (sched) _renderSchedule(sched);
    return config;
  } catch (err) {
    $("health-dot").className = "dot err";
    $("base-dir-pill").textContent = "server unreachable";
    console.error(err);
    return null;
  }
}

function _renderSchedule(s) {
  $("schedule-status").textContent = s.enabled ? "enabled" : "disabled";
  $("schedule-status").className = s.enabled ? "state-on" : "state-off";
  if (!$("schedule-interval").value || document.activeElement !== $("schedule-interval")) {
    $("schedule-interval").value = s.interval_seconds;
  }
  $("schedule-last-run").textContent = s.last_run_at
    ? s.last_run_at.replace("T", " ").slice(0, 19)
    : "never";
  $("schedule-next-run").textContent = s.next_run_at
    ? s.next_run_at.replace("T", " ").slice(0, 19)
    : s.enabled ? "—" : "—";
}

async function _postSchedule(enabled) {
  const interval = Number($("schedule-interval").value) || 60;
  try {
    const s = await api("/api/schedule", {
      method: "POST",
      params: { enabled, interval_seconds: interval },
    });
    _renderSchedule(s);
  } catch (err) {
    alert(`Failed: ${err.message || err}`);
  }
}

async function loadBackups() {
  try {
    const { backups } = await api("/api/backups");
    const empty = $("backups-empty");
    const wrap = $("backups-wrap");
    empty.hidden = backups.length !== 0;
    wrap.hidden = backups.length === 0;
    $("backups-body").innerHTML = backups.map((b) => `
      <tr data-backup-path="${esc(b.path)}">
        <td><code>${esc(b.modified_at.replace("T", " ").slice(0, 19))}</code></td>
        <td>${(b.size_bytes / 1024).toFixed(1)} KB</td>
        <td>
          <button class="btn btn--ghost backup-download">Download</button>
          <button class="btn btn--ghost backup-restore">Restore</button>
        </td>
      </tr>`).join("");
    $("backups-body").querySelectorAll(".backup-download").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const tr = e.target.closest("tr");
        const path = tr.dataset.backupPath;
        const url = `/api/backup/download?path=${encodeURIComponent(path)}`;
        window.open(url, "_blank");
      });
    });
    $("backups-body").querySelectorAll(".backup-restore").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        const tr = e.target.closest("tr");
        const path = tr.dataset.backupPath;
        if (!window.confirm(`Restore ${tr.querySelector("code").textContent} as the active database? The current database will be backed up first.`)) return;
        try {
          await api("/api/backup/restore", { method: "POST", params: { path } });
          await loadBackups();
          await refreshConfig();
          await loadFolders();
        } catch (err) {
          alert(`Restore failed: ${err.message || err}`);
        }
      });
    });
  } catch (_e) { return; }
}

$("backup-create").addEventListener("click", async () => {
  try {
    await api("/api/backup/create", { method: "POST" });
    await loadBackups();
  } catch (err) {
    alert(`Failed: ${err.message || err}`);
  }
});

$("schedule-form").addEventListener("submit", (e) => {
  e.preventDefault();
  _postSchedule(true);
});
$("schedule-disable").addEventListener("click", () => {
  _postSchedule(false);
});

/* ---------------- import ---------------- */

$("import-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const file = $("import-file").files[0];
  if (!file) return;
  const btn = $("import-btn");
  const resultBox = $("import-result");
  btn.disabled = true;
  btn.textContent = "Importing…";
  resultBox.hidden = true;

  const form = new FormData();
  form.append("file", file);
  if ($("import-platform").value) form.append("platform", $("import-platform").value);
  if ($("import-base-dir").value.trim()) form.append("base_dir", $("import-base-dir").value.trim());

  try {
    const result = await api("/api/import", { method: "POST", body: form });
    resultBox.className = "notice ok";
    resultBox.hidden = false;
    resultBox.innerHTML =
      `Imported <b>${result.folders_imported}</b> folder(s) ` +
      `(<b>${result.active_folders}</b> active), rebased <b>${result.rebased_paths}</b> ` +
      `path field(s) to <code>${esc(result.base_directory)}</code>.`;
    await refreshConfig();
    await loadFolders();
    await loadProcessed();
  } catch (err) {
    resultBox.className = "notice err";
    resultBox.hidden = false;
    resultBox.textContent = "Import failed: " + err.message;
  } finally {
    btn.disabled = false;
    btn.textContent = "Import";
  }
});

/* ---------------- folders ---------------- */

async function loadFolders() {
  let folders;
  try {
    folders = await api("/api/folders");
  } catch (err) {
    console.error(err);
    return;
  }
  state.folders = folders; // keep the list for the edit panel
  const empty = $("folders-empty");
  const wrap = $("folders-wrap");
  empty.hidden = folders.length !== 0;
  wrap.hidden = folders.length === 0;

  const body = $("folders-body");
  body.innerHTML = folders.map((f) => {
    const tags = f.backends.map((b) => `<span class="tag tag--${b}">${b}</span>`).join("");
    const pathCell = f.path_exists
      ? `<span class="exists">OK</span> <code>${esc(f.resolved_path)}</code>`
      : `<span class="missing">MISS</span> <code>${esc(f.resolved_path)}</code>`;
    return `<tr data-folder-id="${f.id}" class="folder-row" tabindex="0" role="button" aria-label="Edit ${esc(f.alias || f.folder_name)}">
      <td><b>${esc(f.alias || f.folder_name)}</b></td>
      <td><code>${esc(f.folder_name)}</code></td>
      <td>${pathCell}</td>
      <td>${tags || '<span class="state-off">—</span>'}</td>
      <td>${f.is_active ? '<span class="state-on">● active</span>' : '<span class="state-off">○ inactive</span>'}</td>
    </tr>`;
  }).join("");

  // Each row is a button: clicking opens the side panel.
  body.querySelectorAll(".folder-row").forEach((row) => {
    row.addEventListener("click", () => openFolderPanel(Number(row.dataset.folderId)));
    row.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        openFolderPanel(Number(row.dataset.folderId));
      }
    });
  });
}

$("refresh-folders").addEventListener("click", () => { loadFolders(); loadProcessed(); });

/* ---------------- folder edit panel ---------------- */

function setByPath(obj, path, value) {
  // path = "a.b.c" -> obj.a.b.c = value
  const parts = path.split(".");
  let cursor = obj;
  for (let i = 0; i < parts.length - 1; i++) {
    const k = parts[i];
    if (cursor[k] === undefined || cursor[k] === null) cursor[k] = {};
    cursor = cursor[k];
  }
  cursor[parts[parts.length - 1]] = value;
}

function getByPath(obj, path) {
  const parts = path.split(".");
  let cursor = obj;
  for (const k of parts) {
    if (cursor === null || cursor === undefined) return undefined;
    cursor = cursor[k];
  }
  return cursor;
}

function panelValue(name) {
  const el = $("folder-panel-form").elements.namedItem(name);
  if (!el) return undefined;
  if (el.type === "checkbox") return el.checked;
  if (el.tagName === "SELECT" || el.type === "text" || el.type === "password" ||
      el.type === "number" || el.tagName === "TEXTAREA") {
    return el.value === "" ? "" : (el.type === "number" ? Number(el.value) : el.value);
  }
  return el.value;
}

function setPanelValue(name, value) {
  const el = $("folder-panel-form").elements.namedItem(name);
  if (!el) return;
  if (el.type === "checkbox") {
    el.checked = Boolean(value);
  } else if (value === null || value === undefined) {
    el.value = "";
  } else {
    el.value = String(value);
  }
}

function populateFolderPanel(schema) {
  const form = $("folder-panel-form");
  // Identity + backend toggles live at the top level
  for (const k of ["alias", "folder_name", "process_backend_copy", "process_backend_ftp",
                   "process_backend_email", "process_backend_http"]) {
    setPanelValue(k, schema[k]);
  }
  // Backends (FTP/Email/Copy/HTTP) get a dedicated hidden <fieldset> that
  // we show only when that backend is configured. The other groups
  // (EDI/UPC/A-record/etc.) are always visible because they apply to
  // every folder regardless of which backend is selected.
  const backendGroups = [
    ["ftp", "ftp"],
    ["email", "email"],
    ["copy_backend", "copy"],
    ["http", "http"],
  ];
  for (const [grp, domId] of backendGroups) {
    const obj = schema[grp];
    $(`grp-${domId}`).hidden = !obj;
    if (obj) {
      for (const [k, v] of Object.entries(obj)) {
        setPanelValue(`${grp}.${k}`, v);
      }
    } else {
      const fields = form.querySelectorAll(`[name^="${grp}."]`);
      fields.forEach((f) => {
        if (f.type === "checkbox") f.checked = false;
        else f.value = "";
      });
    }
  }
  // Other groups: just populate, don't toggle visibility.
  for (const grp of [
    "edi", "upc_override", "a_record_padding", "invoice_date",
    "backend_specific", "csv",
  ]) {
    const obj = schema[grp];
    if (obj) {
      for (const [k, v] of Object.entries(obj)) {
        setPanelValue(`${grp}.${k}`, v);
      }
    }
  }
  $("folder-panel-error").hidden = true;
  $("folder-panel-error").textContent = "";
  $("folder-panel-title").textContent =
    `Edit: ${schema.alias || schema.folder_name || `folder ${schema.id}`}`;
}

function readFolderPanel() {
  const schema = {
    id: state.editingFolderId,
    alert_on_failure: true, // not exposed in the UI yet; default
    plugin_configurations: {},
  };
  for (const el of $("folder-panel-form").elements) {
    if (!el.name) continue;
    if (el.name.includes(".")) continue; // handled below by group
    setByPath(schema, el.name, panelValue(el.name));
  }
  for (const grp of ["ftp", "email", "copy_backend", "http", "edi", "upc_override",
                     "a_record_padding", "invoice_date", "backend_specific", "csv"]) {
    const fields = $("folder-panel-form").querySelectorAll(`[name^="${grp}."]`);
    if (fields.length === 0) continue;
    // Include the group iff at least one field is filled or checked.
    let anySet = false;
    const obj = {};
    fields.forEach((f) => {
      const v = panelValue(f.name);
      if (v !== undefined && v !== "" && v !== false) anySet = true;
      const lastDot = f.name.lastIndexOf(".");
      setByPath(obj, f.name.slice(lastDot + 1), v);
    });
    if (anySet) schema[grp] = obj;
  }
  return schema;
}

async function openFolderPanel(folderId) {
  state.editingFolderId = folderId;
  const errBox = $("folder-panel-error");
  errBox.hidden = true;
  errBox.textContent = "";
  try {
    const schema = await api(`/api/folders/${folderId}`);
    populateFolderPanel(schema);
    const panel = $("folder-panel");
    panel.hidden = false;
    panel.setAttribute("aria-hidden", "false");
  } catch (err) {
    // Show errors in the panel itself, not in the (far away) Run card —
    // an operator opening a folder expects feedback in the same place
    // they clicked.
    errBox.hidden = false;
    errBox.textContent = `Failed to load folder: ${err.message || String(err)}`;
  }
}

function closeFolderPanel() {
  const panel = $("folder-panel");
  panel.hidden = true;
  panel.setAttribute("aria-hidden", "true");
  state.editingFolderId = null;
}

$("folder-panel-close").addEventListener("click", closeFolderPanel);
$("folder-panel-cancel").addEventListener("click", closeFolderPanel);
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !$("folder-panel").hidden) closeFolderPanel();
});

$("folder-panel-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const schema = readFolderPanel();
  const errBox = $("folder-panel-error");
  const saveBtn = $("folder-panel-save");
  saveBtn.disabled = true;
  saveBtn.textContent = "Saving…";
  try {
    const updated = await api(`/api/folders/${schema.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(schema),
    });
    populateFolderPanel(updated);
    errBox.hidden = true;
    await loadFolders();
    await refreshConfig();
  } catch (err) {
    errBox.hidden = false;
    errBox.textContent = err.message || String(err);
  } finally {
    saveBtn.disabled = false;
    saveBtn.textContent = "Save";
  }
});

/* ---------------- folder-level maintenance ---------------- */

function _showMaintenance(message, kind) {
  const box = $("folder-panel-maintenance-result");
  box.hidden = false;
  box.className = "notice " + (kind === "err" ? "err" : "ok");
  box.innerHTML = message;
}

async function runFolderMaintenance(action) {
  const folderId = state.editingFolderId;
  if (folderId == null) return;
  if (action === "clear-processed") {
    if (
      !window.confirm(
        `Clear every processed-files row for folder ${folderId}? The next run will re-process every EDI in this folder.`,
      )
    ) {
      return;
    }
  }
  const folderAlias = $("folder-panel-form").elements.namedItem("alias").value || "";
  const result = $("folder-panel-maintenance-result");
  result.hidden = true;
  try {
    if (action === "clear-processed") {
      const r = await api(
        `/api/maintenance/clear-processed?folder_id=${folderId}`,
        { method: "POST" },
      );
      _showMaintenance(
        `Cleared <b>${r.deleted}</b> processed-files row(s) for ${esc(folderAlias)}.`,
        "ok",
      );
      await loadProcessed();
    } else if (action === "mark-processed") {
      const filePath = window.prompt(
        "Absolute path of the file to mark as processed:",
        "",
      );
      if (!filePath) return;
      const invoiceNumbers = window.prompt(
        "Invoice numbers (comma-separated, optional):",
        "",
      ) || "";
      const r = await api("/api/maintenance/mark-processed", {
        method: "POST",
        params: { folder_id: folderId, folder_alias: folderAlias,
                  file_path: filePath, invoice_numbers: invoiceNumbers },
      });
      _showMaintenance(
        `Recorded processed-files row id <b>${r.id}</b>.`,
        "ok",
      );
      await loadProcessed();
    } else if (action === "export-processed") {
      const r = await api("/api/maintenance/export-processed", {
        method: "POST",
        params: { folder_id: folderId },
      });
      const url = `/api/maintenance/download?path=${encodeURIComponent(r.path)}`;
      _showMaintenance(
        `Report written to <code>${esc(r.path)}</code> — ` +
        `<a href="${url}" download>download</a>.`,
        "ok",
      );
    }
  } catch (err) {
    _showMaintenance(`Failed: ${esc(err.message || String(err))}`, "err");
  }
}

async function _runFolderFromPanel() {
  const folderId = state.editingFolderId;
  if (folderId == null) return;
  const btn = $("folder-panel-run");
  btn.disabled = true;
  btn.textContent = "Running…";
  try {
    const { run_id } = await api(`/api/folders/${folderId}/run`, { method: "POST" });
    // Poll the run to completion and render the result in the Run card.
    const report = await _pollFolderRun(run_id);
    renderRun(report);
    await loadProcessed();
  } catch (err) {
    const errBox = $("folder-panel-error");
    errBox.hidden = false;
    errBox.textContent = `Run failed: ${err.message || String(err)}`;
  } finally {
    btn.disabled = false;
    btn.textContent = "Run this folder";
  }
}

async function _pollFolderRun(runId) {
  for (let i = 0; i < 60; i++) {
    const report = await api(`/api/runs/${runId}`);
    if (report.status !== "running") return report;
    await new Promise((r) => setTimeout(r, 1000));
  }
  return await api(`/api/runs/${runId}`);
}

$("folder-panel-run").addEventListener("click", () => _runFolderFromPanel());

document.querySelectorAll("[data-maint]").forEach((btn) => {
  btn.addEventListener("click", () => runFolderMaintenance(btn.dataset.maint));
});

/* ---------------- EDI preview ---------------- */

$("edi-preview-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const file = $("edi-preview-file").files[0];
  if (!file) return;
  const result = $("edi-preview-result");
  result.hidden = false;
  result.textContent = "Parsing…";
  try {
    const data = await api("/api/preview/edi", {
      method: "POST",
      body: (() => {
        const fd = new FormData();
        fd.append("file", file);
        return fd;
      })(),
    });
    const s = data.summary;
    result.innerHTML = `
      <div class="summary">
        <span><b>${s.total}</b> total</span>
        <span><b>${s.a}</b> A records</span>
        <span><b>${s.b}</b> B records</span>
        <span><b>${s.c}</b> C records</span>
        <span><b>${s.trailer}</b> trailer</span>
        ${s.unknown ? `<span style="color: var(--bad)"><b>${s.unknown}</b> unknown</span>` : ""}
      </div>
      <table>
        ${data.lines.map((l) => `
          <tr class="${l.type}"><td>${l.num}</td><td>${l.type.toUpperCase()}</td><td>${esc(l.raw)}</td></tr>
        `).join("")}
      </table>`;
  } catch (err) {
    result.textContent = `Failed: ${err.message || err}`;
  }
});

/* ---------------- run ---------------- */

$("run-btn").addEventListener("click", async () => {
  try {
    const { run_id } = await api("/api/run", { method: "POST" });
    state.lastRunId = run_id;
    $("run-progress").hidden = false;
    $("run-btn").disabled = true;
    const started = Date.now();
    window.clearInterval(state.pollHandle);
    state.pollHandle = window.setInterval(() => {
      $("run-elapsed").textContent = ((Date.now() - started) / 1000).toFixed(1) + "s";
    }, 200);
    streamRunLog(run_id);  // fire-and-forget; the polling loop below still drives status
    await pollRun(run_id);
  } catch (err) {
    flashRunError(err.message);
  } finally {
    // The button stays disabled while a run is in flight; once the poll
    // loop finishes, refreshConfig() re-enables it (see pollRun).
  }
});

async function _pollRun(runId) {
  const report = await api(`/api/runs/${runId}`);
  if (report.status === "running") {
    setTimeout(() => _pollRun(runId), 1200);
    return;
  }
  window.clearInterval(state.pollHandle);
  $("run-progress").hidden = true;
  $("run-btn").disabled = false;
  renderRun(report);
  await loadProcessed();
}

async function streamRunLog(runId) {
  const logEl = $("run-log-body");
  logEl.textContent = "";
  $("run-log").hidden = false;
  logEl.hidden = false;
  $("log-toggle").textContent = "hide";
  try {
    const resp = await fetch(`/api/runs/${runId}/log`);
    const reader = resp.body.getReader();
    const dec = new TextDecoder();
    let buf = "";
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      // Parse SSE frames (event:/data:/blank line).
      const events = buf.split("\n\n");
      buf = events.pop();
      for (const frame of events) {
        const lines = frame.split("\n");
        const ev = (lines.find((l) => l.startsWith("event:")) || "").slice(6).trim();
        const data = (lines.find((l) => l.startsWith("data:")) || "").slice(5).trim();
        if (ev === "log" && data) {
          logEl.textContent += data.replace(/\\n/g, "\n") + "\n";
          logEl.scrollTop = logEl.scrollHeight;
        } else if (ev === "done") {
          return;
        }
      }
    }
  } catch (_e) { /* ignore */ }
}

function renderRun(report) {
  const box = $("run-results");
  if (report.status === "failed") {
    box.innerHTML = `<div class="folder-result"><div class="folder-result__head">
      <h3>Run failed</h3></div><div class="folder-result__errors">${esc(report.error)}</div></div>`;
    return;
  }
  box.innerHTML = report.folders.map((f) => `
    <div class="folder-result">
      <div class="folder-result__head">
        <h3>${esc(f.alias)}</h3>
        <span class="folder-result__meta">${esc(f.relative_path)}</span>
      </div>
      <div class="folder-result__stats">
        <span class="stat stat--good">processed <b>${f.files_processed}</b></span>
        <span class="stat ${f.files_failed ? "stat--bad" : "stat--good"}">failed <b>${f.files_failed}</b></span>
        <span class="stat">${f.success ? '<span class="state-on">✓ ok</span>' : '<span class="state-off">⚠</span>'}</span>
      </div>
      ${f.errors.length ? `<div class="folder-result__errors">${f.errors.map(esc).join("<br>")}</div>` : ""}
    </div>`).join("");

  const log = $("run-log");
  const logBody = $("run-log-body");
  logBody.textContent = report.run_log || "(no log output)";
  log.hidden = false;
  logBody.hidden = true;
  $("log-toggle").textContent = "show";
}

$("log-toggle").addEventListener("click", () => {
  const body = $("run-log-body");
  body.hidden = !body.hidden;
  $("log-toggle").textContent = body.hidden ? "show" : "hide";
});

function flashRunError(message) {
  const box = $("run-results");
  box.innerHTML = `<div class="folder-result"><div class="folder-result__errors">${esc(message)}</div></div>`;
}

/* ---------------- runs list ---------------- */

async function loadRuns() {
  let runs;
  try {
    runs = await api("/api/runs");
  } catch (_e) { return; }
  $("runs-empty").hidden = runs.length !== 0;
  const list = $("runs-list");
  list.innerHTML = runs.slice().reverse().map((r) => `
    <li data-run="${r.run_id}">
      <span class="run-status">
        <span class="dot ${r.status === "running" ? "ok" : r.status === "completed" ? "ok" : "err"}"></span>
        <b>${esc(r.run_id)}</b>
        <span class="state-off">${esc(r.started_at.replace("T", " ").slice(0, 19))}</span>
      </span>
      <span class="state-off">${r.total_processed} ok · ${r.total_failed} fail</span>
    </li>`).join("");

  list.querySelectorAll("li").forEach((li) => {
    li.addEventListener("click", async () => {
      const detail = await api("/api/runs/" + li.dataset.run);
      renderRun(detail);
      const log = $("run-log");
      log.hidden = false;
      $("run-log-body").textContent = detail.run_log || "(no log output)";
    });
  });
}

/* ---------------- processed files ---------------- */

async function loadProcessed() {
  let data;
  try {
    data = await api("/api/processed-files/flagged");
  } catch (_e) { return; }
  $("processed-empty").hidden = data.count !== 0;
  $("processed-wrap").hidden = data.count === 0;
  state.processedFiles = data.files;
  $("processed-body").innerHTML = data.files.map((f) => `
    <tr data-row-id="${f.id}" class="${f.resend_flag ? "resend-row-flagged" : ""}">
      <td class="resend-cell"><input type="checkbox" data-flag-id="${f.id}" ${f.resend_flag ? "checked" : ""} /></td>
      <td><code>${esc(f.file_name)}</code></td>
      <td>${esc(f.folder_alias || "")}</td>
      <td>${esc(f.status || "")}</td>
      <td>${esc(f.sent_to || "")}</td>
      <td>${esc((f.processed_at || "").replace("T", " ").slice(0, 19))}</td>
    </tr>`).join("");
  // Attach per-row checkbox handler.
  $("processed-body").querySelectorAll("input[data-flag-id]").forEach((cb) => {
    cb.addEventListener("change", async () => {
      const id = Number(cb.dataset.flagId);
      const resend = cb.checked;
      try {
        await api(`/api/processed-files/${id}/resend`, {
          method: "POST",
          params: { resend },
        });
        cb.closest("tr").classList.toggle("resend-row-flagged", resend);
        _updateResendButton();
      } catch (err) {
        // Revert on failure.
        cb.checked = !resend;
        alert(`Failed to update flag: ${err.message || err}`);
      }
    });
  });
  _updateResendButton();
}

function _updateResendButton() {
  const count = (state.processedFiles || []).filter((f) => f.resend_flag).length;
  $("resend-btn").disabled = count === 0;
  $("resend-btn").textContent = count > 0
    ? `Resend flagged (${count})`
    : "Resend flagged";
}

$("resend-btn").addEventListener("click", async () => {
  const flagged = (state.processedFiles || []).filter((f) => f.resend_flag);
  if (flagged.length === 0) return;
  if (!window.confirm(
    `Re-send ${flagged.length} flagged file(s) through their original backends?`,
  )) return;
  try {
    const { run_id } = await api("/api/resend", { method: "POST" });
    $("resend-btn").disabled = true;
    $("resend-btn").textContent = "Resending…";
    await _pollResend(run_id);
  } catch (err) {
    alert(`Resend failed: ${err.message || err}`);
    _updateResendButton();
  }
});

async function _pollResend(runId) {
  const report = await api(`/api/runs/${runId}`);
  if (report.status === "running") {
    setTimeout(() => _pollResend(runId), 1200);
    return;
  }
  await loadProcessed();
  await loadRuns();
}

$("clear-flags-btn").addEventListener("click", async () => {
  const count = (state.processedFiles || []).filter((f) => f.resend_flag).length;
  if (count === 0) return;
  if (!window.confirm(`Clear ${count} resend flag(s)?`)) return;
  try {
    await api("/api/processed-files/clear-flags", { method: "POST" });
    await loadProcessed();
  } catch (err) {
    alert(`Failed: ${err.message || err}`);
  }
});

/* ---------------- boot ---------------- */

(async function init() {
  await refreshConfig();
  await loadFolders();
  await loadRuns();
  await loadProcessed();
  await loadBackups();
  window.setInterval(async () => {
    await refreshConfig();
    await loadRuns();
  }, 8000);
})();

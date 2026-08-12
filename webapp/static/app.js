"use strict";

/* Batch File Sender webapp — dashboard logic (vanilla JS). */

// ``api`` itself lives in api.js (loaded before this file); see there
// for the fetch wrapper that serializes ``params`` into the URL.

const $ = (id) => document.getElementById(id);

const state = {
  config: null,
  pollHandle: null,
  lastRunId: null,
  editingFolderId: null,
  errorsFilterId: null, // folder id the Errors card is narrowed to, or null
};

// ``esc`` and ``folderIdForPath`` live in helpers.js (loaded before this
// file); see there for the HTML-escaper and the folder-path matcher.

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
    : "—";
  $("schedule-runs").textContent = s.runs_triggered ?? 0;
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
    $("backups-body").innerHTML = backupRows(backups);
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
          await loadWatched();
          await loadErrors();
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
    resultBox.innerHTML = importResultNotice(result);
    await refreshConfig();
    await loadFolders();
    await loadWatched();
    await loadProcessed();
    await loadErrors();
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
  body.innerHTML = folderRows(folders);

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

/* ---------------- watching overview ---------------- */

// ``fmtInterval`` lives in helpers.js; the row builders in templates.js.

async function loadWatched() {
  let data;
  try {
    data = await api("/api/watched");
  } catch (_e) { return; }
  const folders = data.folders || [];
  const empty = $("watching-empty");
  const wrap = $("watching-wrap");
  const count = $("watching-count");
  empty.hidden = folders.length !== 0;
  wrap.hidden = folders.length === 0;
  count.hidden = folders.length === 0;
  count.textContent = folders.length === 1 ? "1 folder" : `${folders.length} folders`;

  const body = $("watching-body");
  body.innerHTML = watchingRows(folders);

  // Clicking a watched row opens the folder editor (same as the
  // folders table) so the interval / toggle can be adjusted in place.
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

/* ---------------- errors overview ---------------- */

// The row-template builders (``folderRows`` / ``errorRows`` /
// ``processedRows``) live in templates.js (loaded before this file);
// ``fmtErrorStamp`` lives in helpers.js.

function setErrorsFilter(folderId) {
  const id = folderId == null || folderId === "" ? null : Number(folderId);
  if (id === state.errorsFilterId) return;
  state.errorsFilterId = id;
  _renderErrorsFilterUI();
  loadErrors();
}

function _renderErrorsFilterOptions() {
  const folders = state.folders || [];
  const select = $("errors-filter");
  $("errors-filter-wrap").hidden = folders.length === 0;
  // Rebuild only when the folder set changed, so the 8s poll doesn't
  // disturb a dropdown the operator has open.
  const key = folders.map((f) => f.id).join(",");
  if (select.dataset.foldersKey !== key) {
    select.dataset.foldersKey = key;
    select.innerHTML =
      '<option value="">All folders</option>' +
      folders.map((f) =>
        `<option value="${f.id}" title="${esc(f.folder_name || "")}">` +
        `${esc(f.alias || f.folder_name || `folder ${f.id}`)}</option>`
      ).join("");
  }
  // Drop a filter whose folder no longer exists (e.g. after a restore).
  if (state.errorsFilterId != null && !folders.some((f) => f.id === state.errorsFilterId)) {
    state.errorsFilterId = null;
  }
  _renderErrorsFilterUI();
}

function _renderErrorsFilterUI() {
  const folder = state.errorsFilterId != null
    ? (state.folders || []).find((f) => f.id === state.errorsFilterId)
    : null;
  $("errors-filter").value = folder ? String(folder.id) : "";
  $("errors-filter-state").hidden = !folder;
  $("errors-filter-name").textContent = folder
    ? (folder.alias || folder.folder_name || `folder ${folder.id}`)
    : "";
  $("errors-clear").textContent = folder ? "Clear folder" : "Clear all";
}

$("errors-filter").addEventListener("change", () => {
  setErrorsFilter($("errors-filter").value);
});
$("errors-filter-clear").addEventListener("click", () => setErrorsFilter(null));

async function loadErrors() {
  _renderErrorsFilterOptions();
  const filterId = state.errorsFilterId;
  let data;
  try {
    data = await api(
      "/api/errors" + (filterId != null ? `?folder_id=${filterId}&limit=50` : "?limit=50")
    );
  } catch (_e) { return; }
  const errors = data.errors || [];
  const empty = $("errors-empty");
  const wrap = $("errors-wrap");
  const count = $("errors-count");
  empty.hidden = errors.length !== 0;
  wrap.hidden = errors.length === 0;
  count.hidden = errors.length === 0;
  count.textContent = errors.length === 1 ? "1 error" : `${errors.length} errors`;
  $("errors-clear").disabled = errors.length === 0;

  const folder = filterId != null
    ? (state.folders || []).find((f) => f.id === filterId)
    : null;
  empty.textContent = folder
    ? `No errors recorded for ${folder.alias || folder.folder_name || `folder ${filterId}`}.`
    : "No errors recorded.";

  $("errors-body").innerHTML = errorRows(errors, state.folders);

  $("errors-body").querySelectorAll(".error-row").forEach((row) => {
    row.addEventListener("click", () => setErrorsFilter(Number(row.dataset.folderId)));
    row.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        setErrorsFilter(Number(row.dataset.folderId));
      }
    });
  });
}

$("errors-clear").addEventListener("click", async () => {
  const filterId = state.errorsFilterId;
  const folder = filterId != null
    ? (state.folders || []).find((f) => f.id === filterId)
    : null;
  // With a filter active, clear only that folder so the operator can't
  // accidentally wipe every folder's errors while investigating one.
  const what = folder
    ? `all errors for ${folder.alias || folder.folder_name || `folder ${filterId}`}`
    : "the entire error ledger";
  if (!window.confirm(`Clear ${what}? This cannot be undone.`)) return;
  try {
    await api(
      "/api/errors/clear" + (filterId != null ? `?folder_id=${filterId}` : ""),
      { method: "POST" },
    );
    await loadErrors();
  } catch (err) {
    alert(`Failed: ${err.message || err}`);
  }
});

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
  // Identity + backend toggles + watcher live at the top level
  for (const k of [
    "alias", "folder_name",
    "process_backend_copy", "process_backend_ftp",
    "process_backend_email", "process_backend_http",
    "watch_enabled", "watch_interval_seconds",
  ]) {
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
    // If watch_enabled changed, kick the supervisor so the change
    // takes effect immediately rather than waiting up to 30s.
    if ("watch_enabled" in schema) {
      await api("/api/watcher/refresh", { method: "POST" }).catch(() => {});
    }
    await loadWatched();
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
      _showMaintenance(maintenanceClearedNotice(r.deleted, folderAlias), "ok");
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
      _showMaintenance(maintenanceRecordedNotice(r.id), "ok");
      await loadProcessed();
    } else if (action === "export-processed") {
      const r = await api("/api/maintenance/export-processed", {
        method: "POST",
        params: { folder_id: folderId },
      });
      const url = `/api/maintenance/download?path=${encodeURIComponent(r.path)}`;
      _showMaintenance(maintenanceExportNotice(r.path, url), "ok");
    }
  } catch (err) {
    _showMaintenance(maintenanceErrorNotice(err.message || String(err)), "err");
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
    await loadErrors();
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
    result.innerHTML = ediPreviewResult(data);
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
    await _pollRun(run_id);
  } catch (err) {
    flashRunError(err.message);
  } finally {
    // The button stays disabled while a run is in flight; once the poll
    // loop finishes, refreshConfig() re-enables it (see _pollRun).
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
  await loadErrors();
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
  box.innerHTML = runResults(report);
  if (report.status === "failed") return;

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
  $("run-results").innerHTML = runErrorBox(message);
}

/* ---------------- runs list ---------------- */

async function loadRuns() {
  let runs;
  try {
    runs = await api("/api/runs");
  } catch (_e) { return; }
  $("runs-empty").hidden = runs.length !== 0;
  const list = $("runs-list");
  list.innerHTML = runRows(runs.slice().reverse());

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
  $("processed-body").innerHTML = processedRows(data.files);
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
  await loadErrors();
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
  await loadWatched();
  await loadErrors();
  await loadRuns();
  await loadProcessed();
  await loadBackups();
  window.setInterval(async () => {
    await refreshConfig();
    await loadWatched();
    await loadErrors();
    await loadRuns();
  }, 8000);
})();

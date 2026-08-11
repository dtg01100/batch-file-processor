"use strict";

/* Batch File Sender webapp — dashboard logic (vanilla JS). */

const $ = (id) => document.getElementById(id);

const state = {
  config: null,
  pollHandle: null,
  lastRunId: null,
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
    const [health, config] = await Promise.all([
      api("/api/health"),
      api("/api/config"),
    ]);
    state.config = config;
    $("health-dot").className = "dot " + (health.status === "ok" ? "ok" : "err");
    $("base-dir-pill").textContent = "base: " + config.base_dir;
    if (config.imported_base_dir && !$("import-base-dir").value) {
      $("import-base-dir").value = config.imported_base_dir;
    }
    $("run-btn").disabled = !config.database_exists || config.active_count === 0;
    return config;
  } catch (err) {
    $("health-dot").className = "dot err";
    $("base-dir-pill").textContent = "server unreachable";
    console.error(err);
    return null;
  }
}

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
    return `<tr>
      <td><b>${esc(f.alias || f.folder_name)}</b></td>
      <td><code>${esc(f.folder_name)}</code></td>
      <td>${pathCell}</td>
      <td>${tags || '<span class="state-off">—</span>'}</td>
      <td>${f.is_active ? '<span class="state-on">● active</span>' : '<span class="state-off">○ inactive</span>'}</td>
    </tr>`;
  }).join("");
}

$("refresh-folders").addEventListener("click", () => { loadFolders(); loadProcessed(); });

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
    await pollRun(run_id);
  } catch (err) {
    flashRunError(err.message);
  } finally {
    // The button stays disabled while a run is in flight; once the poll
    // loop finishes, refreshConfig() re-enables it (see pollRun).
  }
});

async function pollRun(runId) {
  const report = await api("/api/runs/" + runId);
  if (report.status === "running") {
    setTimeout(() => pollRun(runId), 1200);
    return;
  }
  window.clearInterval(state.pollHandle);
  $("run-progress").hidden = true;
  $("run-btn").disabled = false;
  renderRun(report);
  await loadProcessed();
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
    data = await api("/api/processed-files");
  } catch (_e) { return; }
  $("processed-empty").hidden = data.count !== 0;
  $("processed-wrap").hidden = data.count === 0;
  $("processed-body").innerHTML = data.files.map((f) => `
    <tr>
      <td><code>${esc(f.file_name)}</code></td>
      <td>${esc(f.folder_alias || "")}</td>
      <td>${esc(f.status || "")}</td>
      <td>${esc(f.sent_to || "")}</td>
      <td>${esc((f.processed_at || "").replace("T", " ").slice(0, 19))}</td>
    </tr>`).join("");
}

/* ---------------- boot ---------------- */

(async function init() {
  await refreshConfig();
  await loadFolders();
  await loadRuns();
  await loadProcessed();
  window.setInterval(async () => {
    await refreshConfig();
    await loadRuns();
  }, 8000);
})();

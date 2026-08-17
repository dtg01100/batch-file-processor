"use strict";

/*
 * templates.js — pure row-template builders for the dashboard tables.
 *
 * Each builder takes plain data (the API payloads) and returns the
 * innerHTML for the table's <tbody>. No DOM access, no side effects —
 * app.js assigns the result and attaches the click/checkbox handlers.
 *
 * Loaded as a classic script before app.js (defines the globals
 * ``folderRows``, ``errorRows`` and ``processedRows``) and exported via
 * ``module.exports`` so the snapshot tests in
 * tests/webapp/templates.test.js can require() it under Node.
 *
 * Depends on helpers.js for ``esc`` / ``folderIdForPath`` /
 * ``fmtErrorStamp`` (browser: globals; Node: required below).
 */

// helpers.js must load first (browser: it defines the globals; Node:
// require it explicitly). A plain object avoids declaring top-level
// ``let esc`` etc., which would collide with helpers.js's global
// function declarations in the browser.
const H =
  typeof module !== "undefined" && module.exports
    ? require("./helpers.js")
    : globalThis;

// Folders table (Configured folders card). Each row opens the edit panel.
function folderRows(folders) {
  return (folders || []).map((f) => {
    const tags = f.backends.map((b) => `<span class="tag tag--${b}">${b}</span>`).join("");
    const pathCell = f.path_exists
      ? `<span class="exists">OK</span> <code>${H.esc(f.resolved_path)}</code>`
      : `<span class="missing">MISS</span> <code>${H.esc(f.resolved_path)}</code>`;
    return `<tr data-folder-id="${f.id}" class="folder-row" tabindex="0" role="button" aria-label="Edit ${H.esc(f.alias || f.folder_name)}">
      <td><b>${H.esc(f.alias || f.folder_name)}</b></td>
      <td><code>${H.esc(f.folder_name)}</code></td>
      <td>${pathCell}</td>
      <td>${tags || '<span class="state-off">—</span>'}</td>
      <td>${f.is_active ? '<span class="state-on">● active</span>' : '<span class="state-off">○ inactive</span>'}</td>
    </tr>`;
  }).join("");
}

// Errors table. Rows whose folder still exists in the config become
// clickable filters (error-row + data-folder-id); orphaned rows render
// as plain text.
function errorRows(errors, folders) {
  return (errors || []).map((e) => {
    const folderId = H.folderIdForPath(e.folder, folders);
    const attrs = folderId != null
      ? ` class="error-row" tabindex="0" role="button" data-folder-id="${folderId}" ` +
        `title="Click to filter errors by this folder"`
      : "";
    const folderCell = folderId != null
      ? `<span class="error-row__filterable">${H.esc(e.folder || "—")}</span>`
      : H.esc(e.folder || "—");
    // Open question #2: rows the runner linked to a raw error-text file
    // get a download link. The href must survive HTML escaping, so the
    // path goes through encodeURIComponent and the click handler in
    // app.js stops propagation (the row itself filters by folder).
    const rawCell = e.error_file
      ? `<a class="error-row__raw" href="/api/errors/file?path=${encodeURIComponent(e.error_file)}" ` +
        `title="Download raw error text" download>raw</a>`
      : "";
    // Phase 5.5: EDI validation problems carry a major/minor severity
    // (the original validator's distinction). Pipeline exceptions have
    // no severity, so the badge is omitted for them.
    const sev = e.severity === "major" || e.severity === "minor"
      ? `<span class="tag tag--${e.severity}">${e.severity}</span> `
      : "";
    return `<tr${attrs}>
      <td><code>${H.esc(H.fmtErrorStamp(e.timestamp))}</code></td>
      <td>${folderCell}</td>
      <td><code>${H.esc(e.filename || "—")}</code></td>
      <td>
        <span class="tag tag--err">${H.esc(e.error_type || "Error")}</span>
        ${sev}<span>${H.esc(e.error_message || "")}</span>
      </td>
      <td>${rawCell}</td>
    </tr>`;
  }).join("");
}

// Recently processed files table. The resend checkbox + row class are
// driven by resend_flag; app.js wires the checkbox change handler.
function processedRows(files) {
  return (files || []).map((f) => `
    <tr data-row-id="${f.id}" class="${f.resend_flag ? "resend-row-flagged" : ""}">
      <td class="resend-cell"><input type="checkbox" data-flag-id="${f.id}" ${f.resend_flag ? "checked" : ""} /></td>
      <td><code>${H.esc(f.file_name)}</code></td>
      <td>${H.esc(f.folder_alias || "")}</td>
      <td>${H.esc(f.status || "")}</td>
      <td>${H.esc(f.sent_to || "")}</td>
      <td>${H.esc((f.processed_at || "").replace("T", " ").slice(0, 19))}</td>
    </tr>`).join("");
}

// Watching overview table. Rows open the folder editor like the folders
// table (same folder-row class); app.js wires the click handlers.
//
// The State cell reflects phase-5.2 watcher health: a non-empty
// last_error means the last scan failed, an empty last_tick_at means
// the watcher hasn't ticked yet (idle), otherwise it is ticking.
// last_run_id is the most recent run this watcher triggered.
function watchingRows(folders) {
  return (folders || []).map((f) => {
    const err = String(f.last_error || "");
    const tick = f.last_tick_at ? String(f.last_tick_at).replace("T", " ").slice(0, 19) : "";
    const state = err
      ? { cls: "err", label: "error", title: err }
      : tick
        ? { cls: "ok", label: "ticking", title: "" }
        : { cls: "", label: "idle", title: "Waiting for the first scan" };
    const dotTitle = state.title ? ` title="${H.esc(state.title)}"` : "";
    const run = f.last_run_id
      ? ` <span class="state-off">· run ${H.esc(String(f.last_run_id).slice(0, 8))}</span>`
      : "";
    const errorDetail = err
      ? ` <span class="state-off watcher-error" title="${H.esc(err)}">${H.esc(err.length > 60 ? err.slice(0, 60) + "…" : err)}</span>`
      : "";
    return `
    <tr data-folder-id="${f.id}" class="folder-row" tabindex="0" role="button" aria-label="Edit ${H.esc(f.alias || `folder ${f.id}`)}">
      <td><b>${H.esc(f.alias || `folder ${f.id}`)}</b></td>
      <td>${f.watch_path ? `<code>${H.esc(f.watch_path)}</code>` : '<span class="state-off">—</span>'}</td>
      <td>${H.fmtInterval(Number(f.watch_interval_seconds) || 0)}</td>
      <td><span class="dot${state.cls ? " " + state.cls : ""}"${dotTitle}></span> ${state.label}${run}${errorDetail}</td>
      <td>${tick ? `<code>${H.esc(tick)}</code>` : '<span class="state-off">—</span>'}</td>
    </tr>`;
  }).join("");
}

// Backups table. The Download/Restore buttons carry data-* markers that
// app.js queries to attach the handlers.
function backupRows(backups) {
  return (backups || []).map((b) => `
      <tr data-backup-path="${H.esc(b.path)}">
        <td><code>${H.esc(b.modified_at.replace("T", " ").slice(0, 19))}</code></td>
        <td>${(b.size_bytes / 1024).toFixed(1)} KB</td>
        <td>
          <button class="btn btn--ghost backup-download">Download</button>
          <button class="btn btn--ghost backup-restore">Restore</button>
        </td>
      </tr>`).join("");
}

// Phase 5.3: per-run duration + throughput. Running placeholders and
// payloads without the metric fields (older API responses) show nothing;
// finished runs with metrics always do (0.0 files/s is honest for a run
// that processed nothing).
function runMetricsText(r) {
  if (r.status === "running" || typeof r.duration_seconds !== "number") return "";
  const fps = typeof r.files_per_second === "number" ? r.files_per_second : 0;
  return ` · ${r.duration_seconds.toFixed(1)}s · ${fps.toFixed(1)} files/s`;
}

// Recent-runs list. Newest-first ordering is applied by the caller
// (runs.slice().reverse()); this builder renders what it is given.
function runRows(runs) {
  return (runs || []).map((r) => `
    <li data-run="${r.run_id}">
      <span class="run-status">
        <span class="dot ${r.status === "running" ? "ok" : r.status === "completed" ? "ok" : "err"}"></span>
        <b>${H.esc(r.run_id)}</b>
        <span class="state-off">${H.esc(r.started_at.replace("T", " ").slice(0, 19))}</span>
      </span>
      <span class="state-off">${r.total_processed} ok · ${r.total_failed} fail${runMetricsText(r)}</span>
    </li>`).join("");
}

// Phase 5.3: run-level duration + throughput summary line for the run card.
function runMetricsLine(report) {
  if (report.status === "running" || typeof report.duration_seconds !== "number") return "";
  const fps = typeof report.files_per_second === "number" ? report.files_per_second : 0;
  return `<div class="run-meta">${report.duration_seconds.toFixed(1)}s · ${fps.toFixed(1)} files/s</div>`;
}

// Run card body: either a failed-run notice or one folder-result block
// per folder. The run-log DOM handling stays in app.js.
function runResults(report) {
  const meta = runMetricsLine(report);
  if (report.status === "failed") {
    return `<div class="folder-result"><div class="folder-result__head">
      <h3>Run failed</h3></div>${meta}<div class="folder-result__errors">${H.esc(report.error)}</div></div>`;
  }
  return meta + (report.folders || []).map((f) => `
    <div class="folder-result">
      <div class="folder-result__head">
        <h3>${H.esc(f.alias)}</h3>
        <span class="folder-result__meta">${H.esc(f.relative_path)}</span>
      </div>
      <div class="folder-result__stats">
        <span class="stat stat--good">processed <b>${f.files_processed}</b></span>
        <span class="stat ${f.files_failed ? "stat--bad" : "stat--good"}">failed <b>${f.files_failed}</b></span>
        <span class="stat">${f.success ? '<span class="state-on">✓ ok</span>' : '<span class="state-off">⚠</span>'}</span>
      </div>
      ${f.warning ? `<div class="folder-result__warning">⚠ ${H.esc(f.warning)}</div>` : ""}
      ${f.errors.length ? `<div class="folder-result__errors">${f.errors.map(H.esc).join("<br>")}</div>` : ""}
    </div>`).join("");
}

// Transient error notice in the run card (flashRunError).
function runErrorBox(message) {
  return `<div class="folder-result"><div class="folder-result__errors">${H.esc(message)}</div></div>`;
}

// Import success notice (Import configuration card). Surfaces the
// server-measured duration when present so the operator can see how
// long a large DB import actually took (the dashboard already shows
// a live elapsed timer while the request is in flight; this is the
// final, authoritative number the server measured).
function importResultNotice(result) {
  const head = (
    `Imported <b>${result.folders_imported}</b> folder(s) ` +
    `(<b>${result.active_folders}</b> active), rebased <b>${result.rebased_paths}</b> ` +
    `path field(s) to <code>${H.esc(result.base_directory)}</code>.`
  );
  if (typeof result.duration_seconds === "number" && result.duration_seconds >= 0) {
    return `${head} <span class="state-off">(${result.duration_seconds.toFixed(2)}s)</span>`;
  }
  return head;
}

// EDI preview pane: summary pills + per-line record table. Counts and
// record types come from the parse endpoint and are trusted; raw line
// text is escaped.
function ediPreviewResult(data) {
  const s = data.summary;
  return `
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
          <tr class="${l.type}"><td>${l.num}</td><td>${l.type.toUpperCase()}</td><td>${H.esc(l.raw)}</td></tr>
        `).join("")}
      </table>`;
}

// Maintenance-panel result notices (folder editor).
function maintenanceClearedNotice(deleted, folderAlias) {
  return `Cleared <b>${deleted}</b> processed-files row(s) for ${H.esc(folderAlias)}.`;
}

function maintenanceRecordedNotice(rowId) {
  return `Recorded processed-files row id <b>${rowId}</b>.`;
}

function maintenanceExportNotice(path, downloadUrl) {
  return (
    `Report written to <code>${H.esc(path)}</code> — ` +
    `<a href="${downloadUrl}" download>download</a>.`
  );
}

function maintenanceErrorNotice(message) {
  return `Failed: ${H.esc(message)}`;
}

// Read-only audit table: one row per folder with a configured convert
// format, showing the per-format plugin settings as key=value pairs.
// Folders without a format (or with an empty config) are skipped so
// the table only surfaces what an operator would want to review.
function pluginAuditRows(folders) {
  const rows = (folders || []).filter((f) => f.convert_to_format);
  return rows
    .map((f) => {
      const config = f.plugin_configurations || {};
      const plugin = config[f.convert_to_format] || {};
      const settings = Object.entries(plugin)
        .map(([key, value]) => {
          const shown =
            typeof value === "boolean" ? (value ? "true" : "false") : String(value);
          return `<code class="plugin-audit__kv">${H.esc(key)}=${H.esc(shown)}</code>`;
        })
        .join(" ");
      return `<tr data-folder-id="${f.id}" class="folder-row" tabindex="0" role="button" aria-label="Edit ${H.esc(f.alias || f.folder_name)}">
        <td><b>${H.esc(f.alias || f.folder_name)}</b></td>
        <td><span class="tag tag--format">${H.esc(f.convert_to_format)}</span></td>
        <td>${settings || '<span class="state-off">defaults</span>'}</td>
      </tr>`;
    })
    .join("");
}

// Browser: top-level function declarations are already globals. Node:
// expose the builders for tests.
if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    folderRows,
    errorRows,
    processedRows,
    watchingRows,
    backupRows,
    runRows,
    runResults,
    runMetricsText,
    runMetricsLine,
    runErrorBox,
    importResultNotice,
    ediPreviewResult,
    maintenanceClearedNotice,
    maintenanceRecordedNotice,
    maintenanceExportNotice,
    maintenanceErrorNotice,
    pluginAuditRows,
  };
}

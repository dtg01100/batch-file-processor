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
    return `<tr${attrs}>
      <td><code>${H.esc(H.fmtErrorStamp(e.timestamp))}</code></td>
      <td>${folderCell}</td>
      <td><code>${H.esc(e.filename || "—")}</code></td>
      <td>
        <span class="tag tag--err">${H.esc(e.error_type || "Error")}</span>
        <span>${H.esc(e.error_message || "")}</span>
      </td>
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
function watchingRows(folders) {
  return (folders || []).map((f) => `
    <tr data-folder-id="${f.id}" class="folder-row" tabindex="0" role="button" aria-label="Edit ${H.esc(f.alias || `folder ${f.id}`)}">
      <td><b>${H.esc(f.alias || `folder ${f.id}`)}</b></td>
      <td>${f.watch_path ? `<code>${H.esc(f.watch_path)}</code>` : '<span class="state-off">—</span>'}</td>
      <td>${H.fmtInterval(Number(f.watch_interval_seconds) || 0)}</td>
      <td><span class="state-on">● watching</span></td>
    </tr>`).join("");
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
      <span class="state-off">${r.total_processed} ok · ${r.total_failed} fail</span>
    </li>`).join("");
}

// Run card body: either a failed-run notice or one folder-result block
// per folder. The run-log DOM handling stays in app.js.
function runResults(report) {
  if (report.status === "failed") {
    return `<div class="folder-result"><div class="folder-result__head">
      <h3>Run failed</h3></div><div class="folder-result__errors">${H.esc(report.error)}</div></div>`;
  }
  return (report.folders || []).map((f) => `
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
      ${f.errors.length ? `<div class="folder-result__errors">${f.errors.map(H.esc).join("<br>")}</div>` : ""}
    </div>`).join("");
}

// Transient error notice in the run card (flashRunError).
function runErrorBox(message) {
  return `<div class="folder-result"><div class="folder-result__errors">${H.esc(message)}</div></div>`;
}

// Import success notice (Import configuration card).
function importResultNotice(result) {
  return (
    `Imported <b>${result.folders_imported}</b> folder(s) ` +
    `(<b>${result.active_folders}</b> active), rebased <b>${result.rebased_paths}</b> ` +
    `path field(s) to <code>${H.esc(result.base_directory)}</code>.`
  );
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
    runErrorBox,
    importResultNotice,
    ediPreviewResult,
    maintenanceClearedNotice,
    maintenanceRecordedNotice,
    maintenanceExportNotice,
    maintenanceErrorNotice,
  };
}

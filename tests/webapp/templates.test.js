"use strict";

/*
 * Snapshot tests for webapp/static/templates.js — the pure row-template
 * builders behind the folders, errors, and processed-files tables.
 * Each test asserts the exact innerHTML string so a markup change shows
 * up as a diff instead of silently altering the rendered dashboard.
 *
 * Run with:  node --test tests/webapp/templates.test.js
 * (or:        make test-js)
 *
 * Uses only Node's built-in test runner (node:test) — no dependencies.
 * pytest ignores this file (it only collects test_*.py).
 */

const { test } = require("node:test");
const assert = require("node:assert/strict");
const {
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
} = require("../../webapp/static/templates.js");

/* ---------------- folderRows ---------------- */

test("folderRows renders an active folder with backends and an existing path", () => {
  const out = folderRows([
    {
      id: 1,
      alias: "ACME",
      folder_name: "inbox/acme",
      resolved_path: "/data/inbox/acme",
      path_exists: true,
      is_active: true,
      backends: ["copy", "ftp"],
    },
  ]);
  assert.equal(
    out,
    `<tr data-folder-id="1" class="folder-row" tabindex="0" role="button" aria-label="Edit ACME">
      <td><b>ACME</b></td>
      <td><code>inbox/acme</code></td>
      <td><span class="exists">OK</span> <code>/data/inbox/acme</code></td>
      <td><span class="tag tag--copy">copy</span><span class="tag tag--ftp">ftp</span></td>
      <td><span class="state-on">● active</span></td>
    </tr>`,
  );
});

test("folderRows renders an inactive folder with no backends and a missing path", () => {
  const out = folderRows([
    {
      id: 2,
      alias: "",
      folder_name: "inbox/dark",
      resolved_path: "/data/inbox/dark",
      path_exists: false,
      is_active: false,
      backends: [],
    },
  ]);
  assert.equal(
    out,
    `<tr data-folder-id="2" class="folder-row" tabindex="0" role="button" aria-label="Edit inbox/dark">
      <td><b>inbox/dark</b></td>
      <td><code>inbox/dark</code></td>
      <td><span class="missing">MISS</span> <code>/data/inbox/dark</code></td>
      <td><span class="state-off">—</span></td>
      <td><span class="state-off">○ inactive</span></td>
    </tr>`,
  );
});

test("folderRows escapes aliases and paths", () => {
  const out = folderRows([
    {
      id: 3,
      alias: 'A&B "Co"',
      folder_name: 'x <y>',
      resolved_path: "/data/x <y>",
      path_exists: true,
      is_active: true,
      backends: ["http"],
    },
  ]);
  assert.ok(out.includes('aria-label="Edit A&amp;B &quot;Co&quot;"'));
  assert.ok(out.includes("<td><b>A&amp;B &quot;Co&quot;</b></td>"));
  assert.ok(out.includes("<td><code>x &lt;y&gt;</code></td>"));
  assert.ok(out.includes("<code>/data/x &lt;y&gt;</code>"));
});

test("folderRows joins multiple rows with no separator", () => {
  const out = folderRows([
    { id: 1, alias: "A", folder_name: "a", resolved_path: "/d/a", path_exists: true, is_active: true, backends: [] },
    { id: 2, alias: "B", folder_name: "b", resolved_path: "/d/b", path_exists: true, is_active: true, backends: [] },
  ]);
  assert.equal(out.match(/<tr /g).length, 2);
  assert.ok(out.endsWith("</tr>"));
});

test("folderRows returns empty string for no folders", () => {
  assert.equal(folderRows([]), "");
  assert.equal(folderRows(undefined), "");
});

/* ---------------- errorRows ---------------- */

const folders = [
  { id: 1, folder_name: "inbox/acme", resolved_path: "/data/inbox/acme" },
  { id: 2, folder_name: "inbox/gamma", resolved_path: "/data/inbox/gamma" },
];

test("errorRows renders a filterable row for a known folder", () => {
  const out = errorRows(
    [
      {
        timestamp: "Tue Aug 12 10:00:00 2026",
        folder: "/data/inbox/acme",
        filename: "/data/inbox/acme/bad.edi",
        error_type: "ValueError",
        error_message: "boom",
      },
    ],
    folders,
  );
  assert.equal(
    out,
    `<tr class="error-row" tabindex="0" role="button" data-folder-id="1" title="Click to filter errors by this folder">
      <td><code>Tue Aug 12 10:00:00 2026</code></td>
      <td><span class="error-row__filterable">/data/inbox/acme</span></td>
      <td><code>/data/inbox/acme/bad.edi</code></td>
      <td>
        <span class="tag tag--err">ValueError</span>
        <span>boom</span>
      </td>
    </tr>`,
  );
});

test("errorRows renders a plain row for a folder that no longer exists", () => {
  const out = errorRows(
    [
      {
        timestamp: "2026-08-12T10:00:00.000000",
        folder: "/data/inbox/deleted",
        filename: "orphan.edi",
        error_type: "RuntimeError",
        error_message: "gone",
      },
    ],
    folders,
  );
  assert.equal(
    out,
    `<tr>
      <td><code>2026-08-12 10:00:00</code></td>
      <td>/data/inbox/deleted</td>
      <td><code>orphan.edi</code></td>
      <td>
        <span class="tag tag--err">RuntimeError</span>
        <span>gone</span>
      </td>
    </tr>`,
  );
});

test("errorRows falls back for missing fields and escapes markup", () => {
  const out = errorRows(
    [
      {
        timestamp: "",
        folder: '<img src=x onerror=alert(1)>',
        filename: "",
        error_type: "",
        error_message: 'x < y & z',
      },
    ],
    folders,
  );
  assert.ok(out.includes("<td><code>—</code></td>"));
  assert.ok(out.includes("<td>&lt;img src=x onerror=alert(1)&gt;</td>"));
  assert.ok(out.includes("<td><code>—</code></td>"));
  assert.ok(out.includes('<span class="tag tag--err">Error</span>'));
  assert.ok(out.includes("<span>x &lt; y &amp; z</span>"));
});

test("errorRows returns empty string for no errors", () => {
  assert.equal(errorRows([], folders), "");
  assert.equal(errorRows(undefined, folders), "");
});

/* ---------------- processedRows ---------------- */

test("processedRows renders a flagged row with a checked box", () => {
  const out = processedRows([
    {
      id: 7,
      file_name: "INV-1001.edi",
      folder_alias: "ACME",
      status: "processed",
      sent_to: "copy",
      processed_at: "2026-08-12T10:00:00.000000",
      resend_flag: true,
    },
  ]);
  assert.equal(
    out,
    `
    <tr data-row-id="7" class="resend-row-flagged">
      <td class="resend-cell"><input type="checkbox" data-flag-id="7" checked /></td>
      <td><code>INV-1001.edi</code></td>
      <td>ACME</td>
      <td>processed</td>
      <td>copy</td>
      <td>2026-08-12 10:00:00</td>
    </tr>`,
  );
});

test("processedRows renders an unflagged row without the class or checked attr", () => {
  const out = processedRows([
    {
      id: 8,
      file_name: "PO-77.edi",
      folder_alias: "GAMMA",
      status: "processed",
      sent_to: "ftp",
      processed_at: "2026-08-12T11:00:00.000000",
      resend_flag: false,
    },
  ]);
  assert.equal(
    out,
    `
    <tr data-row-id="8" class="">
      <td class="resend-cell"><input type="checkbox" data-flag-id="8"  /></td>
      <td><code>PO-77.edi</code></td>
      <td>GAMMA</td>
      <td>processed</td>
      <td>ftp</td>
      <td>2026-08-12 11:00:00</td>
    </tr>`,
  );
});

test("processedRows escapes file names and other text fields", () => {
  const out = processedRows([
    {
      id: 9,
      file_name: 'A&B <x>.edi',
      folder_alias: '<b>ACME</b>',
      status: "done & dusted",
      sent_to: "copy",
      processed_at: "",
      resend_flag: false,
    },
  ]);
  assert.ok(out.includes("<td><code>A&amp;B &lt;x&gt;.edi</code></td>"));
  assert.ok(out.includes("<td>&lt;b&gt;ACME&lt;/b&gt;</td>"));
  assert.ok(out.includes("<td>done &amp; dusted</td>"));
  assert.ok(out.includes("<td></td>")); // empty processed_at renders blank
});

test("processedRows returns empty string for no files", () => {
  assert.equal(processedRows([]), "");
  assert.equal(processedRows(undefined), "");
});

/* ---------------- watchingRows ---------------- */

test("watchingRows renders a watched folder with its interval", () => {
  const out = watchingRows([
    { id: 2, alias: "GAMMA", watch_path: "/data/inbox/gamma", watch_interval_seconds: 30 },
  ]);
  assert.equal(
    out,
    `
    <tr data-folder-id="2" class="folder-row" tabindex="0" role="button" aria-label="Edit GAMMA">
      <td><b>GAMMA</b></td>
      <td><code>/data/inbox/gamma</code></td>
      <td>30s</td>
      <td><span class="state-on">● watching</span></td>
    </tr>`,
  );
});

test("watchingRows formats minute-long intervals and falls back without a path", () => {
  const out = watchingRows([
    { id: 3, alias: "", watch_path: "", watch_interval_seconds: 120 },
  ]);
  assert.equal(
    out,
    `
    <tr data-folder-id="3" class="folder-row" tabindex="0" role="button" aria-label="Edit folder 3">
      <td><b>folder 3</b></td>
      <td><span class="state-off">—</span></td>
      <td>2m</td>
      <td><span class="state-on">● watching</span></td>
    </tr>`,
  );
});

test("watchingRows returns empty string for no folders", () => {
  assert.equal(watchingRows([]), "");
  assert.equal(watchingRows(undefined), "");
});

/* ---------------- backupRows ---------------- */

test("backupRows renders a backup row with size and actions", () => {
  const out = backupRows([
    {
      path: "/data/config/folders.db.bak-2026-08-12-10-00-00.db",
      modified_at: "2026-08-12T10:00:00.000000",
      size_bytes: 2048,
    },
  ]);
  assert.equal(
    out,
    `
      <tr data-backup-path="/data/config/folders.db.bak-2026-08-12-10-00-00.db">
        <td><code>2026-08-12 10:00:00</code></td>
        <td>2.0 KB</td>
        <td>
          <button class="btn btn--ghost backup-download">Download</button>
          <button class="btn btn--ghost backup-restore">Restore</button>
        </td>
      </tr>`,
  );
});

test("backupRows escapes the backup path in the data attribute", () => {
  const out = backupRows([
    { path: '/data/a"b&c.db', modified_at: "2026-08-12T10:00:00", size_bytes: 1024 },
  ]);
  assert.ok(out.includes('data-backup-path="/data/a&quot;b&amp;c.db"'));
  assert.ok(out.includes("<td>1.0 KB</td>"));
});

/* ---------------- runRows ---------------- */

test("runRows renders a completed run", () => {
  const out = runRows([
    {
      run_id: "run-abc",
      status: "completed",
      started_at: "2026-08-12T10:00:00.000000",
      total_processed: 3,
      total_failed: 0,
    },
  ]);
  assert.equal(
    out,
    `
    <li data-run="run-abc">
      <span class="run-status">
        <span class="dot ok"></span>
        <b>run-abc</b>
        <span class="state-off">2026-08-12 10:00:00</span>
      </span>
      <span class="state-off">3 ok · 0 fail</span>
    </li>`,
  );
});

test("runRows marks running runs ok and failed runs err", () => {
  const out = runRows([
    { run_id: "r1", status: "running", started_at: "2026-08-12T10:00:00", total_processed: 0, total_failed: 0 },
    { run_id: "r2", status: "failed", started_at: "2026-08-12T11:00:00", total_processed: 1, total_failed: 2 },
  ]);
  assert.ok(out.includes('<span class="dot ok"></span>\n        <b>r1</b>'));
  assert.ok(out.includes('<span class="dot err"></span>\n        <b>r2</b>'));
  assert.ok(out.includes("1 ok · 2 fail"));
});

/* ---------------- runResults ---------------- */

test("runResults renders a failed run notice", () => {
  const out = runResults({ status: "failed", error: "backend <ftp> unreachable" });
  assert.equal(
    out,
    `<div class="folder-result"><div class="folder-result__head">
      <h3>Run failed</h3></div><div class="folder-result__errors">backend &lt;ftp&gt; unreachable</div></div>`,
  );
});

test("runResults renders folder-result blocks with stats and errors", () => {
  const out = runResults({
    status: "completed",
    folders: [
      {
        alias: "ACME",
        relative_path: "inbox/acme",
        files_processed: 2,
        files_failed: 1,
        success: false,
        errors: ["line 12 bad", "dup"],
      },
    ],
  });
  assert.equal(
    out,
    `
    <div class="folder-result">
      <div class="folder-result__head">
        <h3>ACME</h3>
        <span class="folder-result__meta">inbox/acme</span>
      </div>
      <div class="folder-result__stats">
        <span class="stat stat--good">processed <b>2</b></span>
        <span class="stat stat--bad">failed <b>1</b></span>
        <span class="stat"><span class="state-off">⚠</span></span>
      </div>
      <div class="folder-result__errors">line 12 bad<br>dup</div>
    </div>`,
  );
});

test("runResults escapes folder aliases and error text", () => {
  const out = runResults({
    status: "completed",
    folders: [
      {
        alias: 'A&B <x>',
        relative_path: "inbox/a",
        files_processed: 0,
        files_failed: 0,
        success: true,
        errors: ['bad <&>'],
      },
    ],
  });
  assert.ok(out.includes("<h3>A&amp;B &lt;x&gt;</h3>"));
  assert.ok(out.includes('<span class="stat stat--good">failed <b>0</b></span>'));
  assert.ok(out.includes('<span class="state-on">✓ ok</span>'));
  assert.ok(out.includes('bad &lt;&amp;&gt;'));
});

/* ---------------- runErrorBox ---------------- */

test("runErrorBox escapes the message", () => {
  assert.equal(
    runErrorBox('boom <script>alert(1)</script>'),
    '<div class="folder-result"><div class="folder-result__errors">boom &lt;script&gt;alert(1)&lt;/script&gt;</div></div>',
  );
});

/* ---------------- importResultNotice ---------------- */

test("importResultNotice renders the import summary", () => {
  assert.equal(
    importResultNotice({
      folders_imported: 3,
      active_folders: 2,
      rebased_paths: 5,
      base_directory: "/data/batch",
    }),
    "Imported <b>3</b> folder(s) (<b>2</b> active), rebased <b>5</b> " +
      "path field(s) to <code>/data/batch</code>.",
  );
});

test("importResultNotice escapes the base directory", () => {
  const out = importResultNotice({
    folders_imported: 0,
    active_folders: 0,
    rebased_paths: 0,
    base_directory: '/data/a<b>&c',
  });
  assert.ok(out.endsWith("to <code>/data/a&lt;b&gt;&amp;c</code>."));
});

/* ---------------- ediPreviewResult ---------------- */

test("ediPreviewResult renders summary pills and one row", () => {
  const out = ediPreviewResult({
    summary: { total: 2, a: 1, b: 1, c: 0, trailer: 0, unknown: 0 },
    lines: [{ type: "a", num: 1, raw: "HEADER" }],
  });
  assert.equal(
    out,
    `
      <div class="summary">
        <span><b>2</b> total</span>
        <span><b>1</b> A records</span>
        <span><b>1</b> B records</span>
        <span><b>0</b> C records</span>
        <span><b>0</b> trailer</span>
        
      </div>
      <table>
        
          <tr class="a"><td>1</td><td>A</td><td>HEADER</td></tr>
        
      </table>`,
  );
});

test("ediPreviewResult shows the unknown pill only when nonzero", () => {
  const base = {
    summary: { total: 1, a: 1, b: 0, c: 0, trailer: 0, unknown: 1 },
    lines: [],
  };
  assert.ok(ediPreviewResult(base).includes('<span style="color: var(--bad)"><b>1</b> unknown</span>'));
  assert.ok(!ediPreviewResult({ ...base, summary: { ...base.summary, unknown: 0 } })
    .includes("unknown</span>"));
});

test("ediPreviewResult escapes raw record text", () => {
  const out = ediPreviewResult({
    summary: { total: 1, a: 0, b: 1, c: 0, trailer: 0, unknown: 0 },
    lines: [{ type: "b", num: 2, raw: 'DETAIL <x>&"' }],
  });
  assert.ok(out.includes('<tr class="b"><td>2</td><td>B</td><td>DETAIL &lt;x&gt;&amp;&quot;</td></tr>'));
});

/* ---------------- maintenance notices ---------------- */

test("maintenanceClearedNotice renders count and escaped alias", () => {
  assert.equal(
    maintenanceClearedNotice(12, 'ACME & "Co"'),
    "Cleared <b>12</b> processed-files row(s) for ACME &amp; &quot;Co&quot;.",
  );
});

test("maintenanceRecordedNotice renders the row id", () => {
  assert.equal(maintenanceRecordedNotice(42), "Recorded processed-files row id <b>42</b>.");
});

test("maintenanceExportNotice renders path and download link", () => {
  assert.equal(
    maintenanceExportNotice(
      "/data/config/report.csv",
      "/api/maintenance/download?path=%2Fdata%2Fconfig%2Freport.csv",
    ),
    "Report written to <code>/data/config/report.csv</code> — " +
      '<a href="/api/maintenance/download?path=%2Fdata%2Fconfig%2Freport.csv" download>download</a>.',
  );
});

test("maintenanceExportNotice escapes the path in the code element", () => {
  const out = maintenanceExportNotice("/data/a<b>.csv", "/download?a=1");
  assert.ok(out.includes("<code>/data/a&lt;b&gt;.csv</code>"));
  assert.ok(out.includes('<a href="/download?a=1" download>download</a>.'));
});

test("maintenanceErrorNotice escapes the message", () => {
  assert.equal(maintenanceErrorNotice('backend <ftp> down'), "Failed: backend &lt;ftp&gt; down");
});

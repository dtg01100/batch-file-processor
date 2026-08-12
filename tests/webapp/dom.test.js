"use strict";

/*
 * DOM-level integration test for the webapp dashboard.
 *
 * Loads the real index.html and the real static scripts (api.js,
 * helpers.js, templates.js, app.js) into jsdom, stubs fetch with the
 * API payloads the endpoints would return, lets the boot sequence
 * (init) run, and asserts the rendered page structure. Then exercises
 * two interactions end to end: opening a folder's edit panel and
 * filtering the errors ledger by folder.
 *
 * Run with:  node --test tests/webapp/dom.test.js
 * (or:        make test-js)
 *
 * Requires jsdom (devDependency; npm install). pytest ignores this file
 * (it only collects test_*.py).
 */

const { test, after } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { JSDOM } = require("jsdom");

const STATIC = path.join(__dirname, "../../webapp/static");
const SCRIPT_FILES = ["api.js", "helpers.js", "templates.js", "app.js"];

/* ---------------- fixtures (what the API endpoints return) ---------------- */

const folders = [
  {
    id: 1, alias: "ACME", folder_name: "inbox/acme",
    resolved_path: "/data/inbox/acme", path_exists: true, is_active: true,
    backends: ["copy"],
  },
  {
    id: 2, alias: "GAMMA", folder_name: "inbox/gamma",
    resolved_path: "/data/inbox/gamma", path_exists: true, is_active: true,
    backends: ["ftp", "copy"],
  },
  {
    id: 3, alias: "OMEGA", folder_name: "inbox/omega",
    resolved_path: "/data/inbox/omega", path_exists: false, is_active: false,
    backends: [],
  },
];

const watched = [
  { id: 1, alias: "ACME", watch_path: "/data/inbox/acme", watch_interval_seconds: 120 },
  { id: 2, alias: "GAMMA", watch_path: "/data/inbox/gamma", watch_interval_seconds: 30 },
];

const errors = [
  {
    id: 3, timestamp: "Wed Aug 12 13:20:51 2026",
    folder: "/data/inbox/gamma", filename: "/data/inbox/gamma/PO-77.edi",
    error_type: "EDIValidationError", error_message: "missing ST segment",
    error_source: "Validator", stack_trace: "", created_at: "",
  },
  {
    id: 2, timestamp: "Wed Aug 12 13:20:51 2026",
    folder: "/data/inbox/acme", filename: "/data/inbox/acme/INV-1002.edi",
    error_type: "EDISplitError", error_message: "missing B record",
    error_source: "Splitter", stack_trace: "", created_at: "",
  },
  {
    id: 1, timestamp: "Wed Aug 12 13:20:50 2026",
    folder: "/data/inbox/acme", filename: "/data/inbox/acme/INV-1001.edi",
    error_type: "ValueError", error_message: "bad rename pattern",
    error_source: "Tweaker", stack_trace: "", created_at: "",
  },
];

const runs = [
  {
    run_id: "run-2026-08-12-1", status: "completed",
    started_at: "2026-08-12T13:20:00.000000", finished_at: "2026-08-12T13:21:00.000000",
    total_processed: 3, total_failed: 0, error: "",
    folders: [{ alias: "ACME", relative_path: "inbox/acme", resolved_path: "/data/inbox/acme",
                files_processed: 3, files_failed: 0, success: true, errors: [] }],
  },
  {
    run_id: "run-2026-08-12-0", status: "failed",
    started_at: "2026-08-12T13:10:00.000000", finished_at: "2026-08-12T13:11:00.000000",
    total_processed: 1, total_failed: 2, error: "backend down",
    folders: [],
  },
];

const processedFiles = [
  {
    id: 2, file_name: "INV-1002.edi", folder_id: 1, folder_alias: "ACME",
    processed_at: "2026-08-12T13:21:00.000000", status: "processed",
    sent_to: "copy", invoice_numbers: "1002", resend_flag: true,
  },
  {
    id: 1, file_name: "PO-77.edi", folder_id: 2, folder_alias: "GAMMA",
    processed_at: "2026-08-12T13:21:00.000000", status: "processed",
    sent_to: "ftp", invoice_numbers: "77", resend_flag: false,
  },
];

const backups = [
  {
    path: "/data/config/folders.db.bak-2026-08-12-13-00-00.db",
    modified_at: "2026-08-12T13:00:00.000000",
    size_bytes: 2048,
  },
];

// Full edit schema for the folder panel (folder 1 only — the panel test
// clicks the ACME row; other groups stay absent and get cleared).
const folderOneSchema = {
  id: 1, alias: "ACME", folder_name: "inbox/acme",
  process_backend_copy: true, process_backend_ftp: false,
  process_backend_email: false, process_backend_http: false,
  watch_enabled: true, watch_interval_seconds: 120,
  edi: { process_edi: true, split_edi: false },
};

// The run the Run card will report. While runningPollsLeft > 0 the detail
// endpoint answers "running" (pollRun keeps polling every 1.2s); when it
// hits 0 the run is "completed" and the UI settles. The /log endpoint
// streams SSE frames exactly like the real server (escaped \n in data).
const completedRunReport = {
  run_id: "run-flow-1",
  status: "completed",
  started_at: "2026-08-12T14:00:00.000000",
  finished_at: "2026-08-12T14:01:00.000000",
  total_processed: 3,
  total_failed: 0,
  error: "",
  run_log:
    "processing INV-1001.edi\nprocessing INV-1002.edi\nprocessing PO-77.edi\n3 files processed",
  folders: [
    { alias: "ACME", relative_path: "inbox/acme", resolved_path: "/data/inbox/acme",
      files_processed: 2, files_failed: 0, success: true, errors: [] },
    { alias: "GAMMA", relative_path: "inbox/gamma", resolved_path: "/data/inbox/gamma",
      files_processed: 1, files_failed: 0, success: true, errors: [] },
  ],
};

const runLogFrames =
  "event: log\n" +
  "data: processing INV-1001.edi\\nprocessing INV-1002.edi\\nprocessing PO-77.edi\n\n" +
  "event: done\n" +
  "data: completed\n\n";

const resendReport = {
  run_id: "run-resend-1",
  status: "completed",
  started_at: "2026-08-12T14:10:00.000000",
  finished_at: "2026-08-12T14:11:00.000000",
  total_processed: 2,
  total_failed: 0,
  error: "",
  run_log: "resent 2 files",
  folders: [
    { alias: "ACME", relative_path: "inbox/acme", resolved_path: "/data/inbox/acme",
      files_processed: 1, files_failed: 0, success: true, errors: [] },
  ],
};

// A canned HTTP response with a streaming body (for the SSE log route).
function rawResponse(status, body) {
  return {
    __raw: true,
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 404 ? "Not Found" : "OK",
    json: async () => body,
    body,
  };
}

function sseStream(text) {
  return new ReadableStream({
    start(controller) {
      controller.enqueue(new TextEncoder().encode(text));
      controller.close();
    },
  });
}

// Routes are built fresh per boot so stateful endpoints (the run detail,
// the scheduler state) never leak between tests. The scheduler object is
// returned alongside routes so a test can simulate a scheduled tick.
function buildRoutes() {
  let runningPollsLeft = 2;
  const schedule = {
    enabled: false,
    interval_seconds: 60,
    last_run_at: null,
    next_run_at: null,
  };
  // Mutable copy of the processed-files rows: flag toggles and the resend
  // sweep update this, and loadProcessed re-reads it after each run.
  const processed = processedFiles.map((f) => ({ ...f }));
  let resendPollsLeft = 1;
  const resendRoute = (id) => (url, options) => {
    if (options && options.method === "POST") {
      const row = processed.find((f) => f.id === id);
      if (row) row.resend_flag = url.searchParams.get("resend") === "true";
    }
    const row = processed.find((f) => f.id === id);
    return { id, resend_flag: row ? row.resend_flag : false };
  };
  const routes = {
    "/api/health": () => ({
      status: "ok", base_dir: "/data", data_dir: "/data/config",
      database_exists: true, platform: "Linux",
    }),
    "/api/config": () => ({
      base_dir: "/data", data_dir: "/data/config", database_exists: true,
      imported_base_dir: "/data", source_platform: "Windows",
      folders_count: folders.length,
      active_count: folders.filter((f) => f.is_active).length,
    }),
    "/api/schedule": (url, options) => {
      // POST persists the toggle + interval (params arrive as query
      // string via api()'s serializer); enabling schedules a next run,
      // disabling clears it. GET returns the current state.
      if (options && options.method === "POST") {
        schedule.enabled = url.searchParams.get("enabled") === "true";
        const interval = Number(url.searchParams.get("interval_seconds"));
        if (interval > 0) schedule.interval_seconds = interval;
        schedule.next_run_at = schedule.enabled
          ? "2026-08-12T14:02:00.000000"
          : null;
      }
      return { ...schedule };
    },
    "/api/folders": () => folders,
    "/api/folders/1": () => folderOneSchema,
    "/api/watched": () => ({ folders: watched }),
    "/api/errors": (url) => {
      const fid = url.searchParams.get("folder_id");
      const list = fid
        ? errors.filter((e) => e.folder.endsWith("/inbox/" + (Number(fid) === 1 ? "acme" : "gamma")))
        : errors;
      return { count: list.length, errors: list };
    },
    "/api/runs": () => runs,
    "/api/processed-files/flagged": () => ({ count: processed.length, files: processed }),
    "/api/processed-files/1/resend": resendRoute(1),
    "/api/processed-files/2/resend": resendRoute(2),
    "/api/backups": () => ({ backups }),
    // --- run flow ---
    "/api/run": () => ({ run_id: completedRunReport.run_id }),
    "/api/runs/run-flow-1": () =>
      runningPollsLeft > 0
        ? (runningPollsLeft -= 1, { ...completedRunReport, status: "running" })
        : completedRunReport,
    "/api/runs/run-flow-1/log": () => rawResponse(200, sseStream(runLogFrames)),
    // --- resend flow ---
    "/api/resend": () => {
      // The resend sweep clears every flag, like the backend does.
      for (const f of processed) f.resend_flag = false;
      return { run_id: resendReport.run_id };
    },
    "/api/runs/run-resend-1": () =>
      resendPollsLeft > 0
        ? (resendPollsLeft -= 1, { ...resendReport, status: "running" })
        : resendReport,
  };
  return { routes, schedule };
}

/* ---------------- harness ---------------- */

const doms = [];

function bootDom() {
  const html = fs.readFileSync(path.join(STATIC, "index.html"), "utf8");
  const dom = new JSDOM(html, {
    url: "http://localhost:8000/",
    runScripts: "outside-only", // we eval the scripts ourselves, in order
  });
  doms.push(dom);
  const { window } = dom;

  // jsdom doesn't implement TextEncoder/TextDecoder; the run-log SSE
  // decoder needs them, so supply Node's implementations.
  window.TextEncoder = TextEncoder;
  window.TextDecoder = TextDecoder;

  const { routes, schedule } = buildRoutes();
  window.fetch = async (input, options) => {
    const url = new URL(String(input), window.location.href);
    const handler = routes[url.pathname];
    if (!handler) return rawResponse(404, { detail: `no route for ${url.pathname}` });
    const result = handler(url, options);
    if (result && result.__raw) return result;
    return {
      ok: true, status: 200, statusText: "OK",
      json: async () => result,
    };
  };
  // The handlers use these; stub them so nothing throws in jsdom. The
  // confirm stub records its messages so tests can assert dialog text.
  window.__confirmCalls = [];
  window.alert = () => {};
  window.confirm = (message) => {
    window.__confirmCalls.push(message);
    return true;
  };
  window.prompt = () => "";
  window.open = () => {};

  // Run each static file as a real script in the window's VM context so
  // top-level declarations become globals exactly like browser <script>
  // tags (window.eval would scope strict-mode declarations to the eval).
  for (const file of SCRIPT_FILES) {
    vm.runInContext(fs.readFileSync(path.join(STATIC, file), "utf8"), window);
  }
  return { dom, schedule };
}

function waitFor(fn, { timeout = 3000, interval = 10 } = {}) {
  const start = Date.now();
  return new Promise((resolve, reject) => {
    const tick = async () => {
      let value;
      try {
        value = fn();
      } catch (_e) { /* DOM not ready yet */ }
      if (value) return resolve(value);
      if (Date.now() - start > timeout) {
        return reject(new Error("timed out waiting for condition"));
      }
      setTimeout(tick, interval);
    };
    tick();
  });
}

after(() => {
  for (const dom of doms) {
    try { dom.window.close(); } catch (_e) { /* already closed */ }
  }
});

/* ---------------- tests ---------------- */

test("boots and renders the full dashboard from the stubbed API", async () => {
  const { dom } = bootDom();
  const { window } = dom;
  const document = window.document;

  await waitFor(() => document.querySelectorAll("#folders-body tr").length === 3);

  // Health + config chrome.
  assert.equal(document.getElementById("health-dot").className, "dot ok");
  assert.equal(document.getElementById("base-dir-pill").textContent, "base: /data");
  assert.equal(document.getElementById("run-btn").disabled, false);

  // Folders table.
  const folderRows = document.querySelectorAll("#folders-body tr");
  assert.equal(folderRows.length, 3);
  assert.equal(folderRows[0].querySelector("td b").textContent, "ACME");
  assert.ok(folderRows[2].textContent.includes("MISS"));
  assert.ok(folderRows[2].textContent.includes("○ inactive"));
  assert.equal(document.getElementById("folders-empty").hidden, true);
  assert.equal(document.getElementById("folders-wrap").hidden, false);

  // Watching table.
  const watchingRows = document.querySelectorAll("#watching-body tr");
  assert.equal(watchingRows.length, 2);
  assert.equal(watchingRows[0].querySelector("td:nth-child(3)").textContent, "2m");
  assert.equal(watchingRows[1].querySelector("td:nth-child(3)").textContent, "30s");
  assert.equal(document.getElementById("watching-count").textContent, "2 folders");

  // Errors table + folder filter dropdown.
  assert.equal(document.getElementById("errors-count").textContent, "3 errors");
  const errorRows = document.querySelectorAll("#errors-body tr");
  assert.equal(errorRows.length, 3);
  assert.equal(errorRows[0].querySelector("td:nth-child(2)").textContent, "/data/inbox/gamma");
  const filterOptions = [...document.getElementById("errors-filter").options].map((o) => o.textContent);
  assert.deepEqual(filterOptions, ["All folders", "ACME", "GAMMA", "OMEGA"]);
  assert.equal(document.getElementById("errors-filter-state").hidden, true);

  // Runs list (newest first is reversed for display).
  const runItems = document.querySelectorAll("#runs-list li");
  assert.equal(runItems.length, 2);
  assert.equal(runItems[0].dataset.run, "run-2026-08-12-0"); // older run shown first
  assert.ok(runItems[0].textContent.includes("1 ok · 2 fail"));
  assert.ok(runItems[0].querySelector(".dot").classList.contains("err"));
  assert.ok(runItems[1].textContent.includes("3 ok · 0 fail"));

  // Processed files (first row flagged + checked).
  const processedRows = document.querySelectorAll("#processed-body tr");
  assert.equal(processedRows.length, 2);
  assert.ok(processedRows[0].classList.contains("resend-row-flagged"));
  assert.equal(processedRows[0].querySelector("input[data-flag-id]").checked, true);
  assert.equal(processedRows[1].querySelector("input[data-flag-id]").checked, false);

  // Backups.
  const backupRows = document.querySelectorAll("#backups-body tr");
  assert.equal(backupRows.length, 1);
  assert.equal(backupRows[0].querySelector("td:nth-child(2)").textContent, "2.0 KB");

  // Schedule card.
  assert.equal(document.getElementById("schedule-status").textContent, "disabled");
  assert.ok(document.getElementById("schedule-status").classList.contains("state-off"));

  // Empty states are all hidden because every card has data.
  for (const id of ["folders-empty", "watching-empty", "errors-empty", "runs-empty", "processed-empty", "backups-empty"]) {
    assert.equal(document.getElementById(id).hidden, true, `${id} should be hidden`);
  }
});

test("interactions: folder panel opens, error filter narrows and clears", async () => {
  const { dom } = bootDom();
  const { window } = dom;
  const document = window.document;

  await waitFor(() => document.querySelectorAll("#folders-body tr").length === 3);

  // --- Click the ACME folder row: the edit panel should open. ---
  document.querySelectorAll("#folders-body .folder-row")[0].click();
  await waitFor(() => !document.getElementById("folder-panel").hidden);
  assert.equal(document.getElementById("folder-panel-title").textContent, "Edit: ACME");
  assert.equal(
    document.getElementById("folder-panel-form").elements.namedItem("alias").value,
    "ACME",
  );
  assert.equal(
    document.getElementById("folder-panel-form").elements.namedItem("watch_interval_seconds").value,
    "120",
  );
  document.getElementById("folder-panel-close").click();
  await waitFor(() => document.getElementById("folder-panel").hidden);

  // --- Filter the errors ledger to GAMMA via the dropdown. ---
  const filter = document.getElementById("errors-filter");
  filter.value = "2";
  filter.dispatchEvent(new window.Event("change", { bubbles: true }));
  await waitFor(() => document.querySelectorAll("#errors-body tr").length === 1);
  assert.equal(document.getElementById("errors-count").textContent, "1 error");
  assert.equal(document.getElementById("errors-filter-name").textContent, "GAMMA");
  assert.equal(document.getElementById("errors-filter-state").hidden, false);
  assert.equal(document.getElementById("errors-clear").textContent, "Clear folder");
  assert.equal(
    document.querySelector("#errors-body tr td:nth-child(2)").textContent,
    "/data/inbox/gamma",
  );

  // --- Clear the filter: everything comes back. ---
  document.getElementById("errors-filter-clear").click();
  await waitFor(() => document.querySelectorAll("#errors-body tr").length === 3);
  assert.equal(document.getElementById("errors-filter-state").hidden, true);
  assert.equal(document.getElementById("errors-clear").textContent, "Clear all");
  assert.equal(document.getElementById("errors-count").textContent, "3 errors");
});

test("run flow: progress, results, and the log toggle", async () => {
  const { dom } = bootDom();
  const { window } = dom;
  const document = window.document;

  await waitFor(() => document.querySelectorAll("#folders-body tr").length === 3);

  // --- Start a run: progress shows, the button locks. ---
  const runBtn = document.getElementById("run-btn");
  runBtn.click();
  await waitFor(() => !document.getElementById("run-progress").hidden);
  assert.equal(runBtn.disabled, true);
  // The elapsed ticker updates every 200ms — wait for the first tick.
  await waitFor(() =>
    /^\d+(\.\d+)?s$/.test(document.getElementById("run-elapsed").textContent),
  );

  // --- The SSE log streams in while the run is in flight. ---
  const logBody = document.getElementById("run-log-body");
  await waitFor(() => logBody.textContent.includes("processing INV-1001.edi"));
  assert.equal(document.getElementById("run-log").hidden, false);
  assert.equal(logBody.hidden, false);
  assert.equal(document.getElementById("log-toggle").textContent, "hide");
  assert.ok(logBody.textContent.includes("processing PO-77.edi"));

  // --- The run completes (detail endpoint stops answering "running"). ---
  await waitFor(() => document.getElementById("run-progress").hidden, { timeout: 6000 });
  assert.equal(runBtn.disabled, false);

  // Results rendered from the completed report.
  const results = document.getElementById("run-results");
  assert.ok(results.innerHTML.includes("ACME"));
  assert.ok(results.innerHTML.includes('processed <b>2</b>'));
  assert.ok(results.innerHTML.includes('failed <b>0</b>'));
  assert.ok(results.innerHTML.includes("GAMMA"));

  // renderRun swaps in the report's run_log and hides the body behind the toggle.
  assert.equal(logBody.textContent, completedRunReport.run_log);
  assert.equal(logBody.hidden, true);
  assert.equal(document.getElementById("log-toggle").textContent, "show");
  assert.equal(document.getElementById("run-log").hidden, false);

  // --- Toggle the log open and closed. ---
  const toggle = document.getElementById("log-toggle");
  toggle.click();
  assert.equal(logBody.hidden, false);
  assert.equal(toggle.textContent, "hide");
  toggle.click();
  assert.equal(logBody.hidden, true);
  assert.equal(toggle.textContent, "show");
});

test("schedule card: enable, persist interval, show run times, disable", async () => {
  const { dom, schedule } = bootDom();
  const { window } = dom;
  const document = window.document;

  await waitFor(() => document.querySelectorAll("#folders-body tr").length === 3);

  const status = document.getElementById("schedule-status");
  const intervalInput = document.getElementById("schedule-interval");
  const lastRun = document.getElementById("schedule-last-run");
  const nextRun = document.getElementById("schedule-next-run");

  // Disabled by default: pill, interval, no run times yet.
  assert.equal(status.textContent, "disabled");
  assert.ok(status.classList.contains("state-off"));
  assert.equal(intervalInput.value, "60");
  assert.equal(lastRun.textContent, "never");
  assert.equal(nextRun.textContent, "—");

  // Change the interval and enable via the form submit.
  intervalInput.value = "120";
  document.getElementById("schedule-form").dispatchEvent(
    new window.Event("submit", { bubbles: true, cancelable: true }),
  );
  await waitFor(() => status.textContent === "enabled");
  assert.ok(status.classList.contains("state-on"));
  assert.equal(intervalInput.value, "120"); // interval persisted from the POST
  assert.equal(lastRun.textContent, "never");
  assert.equal(nextRun.textContent, "2026-08-12 14:02:00");

  // Simulate a scheduled tick, then refresh the way the 8s poll does.
  schedule.last_run_at = "2026-08-12T14:00:00.000000";
  await window.refreshConfig();
  assert.equal(lastRun.textContent, "2026-08-12 14:00:00");
  assert.equal(nextRun.textContent, "2026-08-12 14:02:00");

  // Disable: pill flips back, interval is kept, next run clears.
  document.getElementById("schedule-disable").click();
  await waitFor(() => status.textContent === "disabled");
  assert.ok(status.classList.contains("state-off"));
  assert.equal(intervalInput.value, "120");
  assert.equal(lastRun.textContent, "2026-08-12 14:00:00"); // history kept
  assert.equal(nextRun.textContent, "—");
});

test("resend flow: flag a file, resend flagged, flags clear after the run", async () => {
  const { dom } = bootDom();
  const { window } = dom;
  const document = window.document;

  await waitFor(() => document.querySelectorAll("#folders-body tr").length === 3);

  // Initial state: row 2 (INV-1002) is flagged from the fixture, so the
  // button is enabled and shows the count.
  const resendBtn = document.getElementById("resend-btn");
  assert.equal(resendBtn.disabled, false);
  assert.equal(resendBtn.textContent, "Resend flagged (1)");

  // --- Flag a second file by checking its box: POST persists the flag. ---
  const rows = document.querySelectorAll("#processed-body tr");
  assert.equal(rows.length, 2);
  const cb = rows[1].querySelector("input[data-flag-id]");
  assert.equal(cb.checked, false);
  cb.checked = true;
  cb.dispatchEvent(new window.Event("change", { bubbles: true }));
  await waitFor(() => resendBtn.textContent === "Resend flagged (2)");
  assert.equal(resendBtn.disabled, false);
  assert.ok(rows[1].classList.contains("resend-row-flagged"));

  // --- Click Resend flagged: confirm dialog, run starts, button locks. ---
  resendBtn.click();
  assert.equal(window.__confirmCalls.length, 1);
  assert.equal(window.__confirmCalls[0], "Re-send 2 flagged file(s) through their original backends?");
  await waitFor(() => resendBtn.textContent === "Resending…");
  assert.equal(resendBtn.disabled, true);

  // --- The resend run completes (1 poll of "running", then done); the
  // sweep cleared every flag and loadProcessed re-read them. ---
  await waitFor(() => resendBtn.textContent === "Resend flagged", { timeout: 6000 });
  assert.equal(resendBtn.disabled, true); // nothing flagged anymore
  const rowsAfter = document.querySelectorAll("#processed-body tr");
  assert.equal(rowsAfter.length, 2);
  assert.equal(rowsAfter[0].querySelector("input[data-flag-id]").checked, false);
  assert.equal(rowsAfter[1].querySelector("input[data-flag-id]").checked, false);
  assert.equal(document.querySelectorAll("#processed-body .resend-row-flagged").length, 0);
});

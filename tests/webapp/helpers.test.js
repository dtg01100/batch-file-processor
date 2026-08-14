"use strict";

/*
 * Unit tests for webapp/static/helpers.js — the dashboard's pure
 * helpers: esc() (HTML escaping) and folderIdForPath() (ledger folder
 * path -> configured folder id).
 *
 * Run with:  node --test tests/webapp/helpers.test.js
 * (or:        make test-js)
 *
 * Uses only Node's built-in test runner (node:test) — no dependencies.
 * pytest ignores this file (it only collects test_*.py).
 */

const { test } = require("node:test");
const assert = require("node:assert/strict");
const { esc, folderIdForPath, fmtErrorStamp, fmtInterval } = require("../../webapp/static/helpers.js");

/* ---------------- esc ---------------- */

test("esc escapes the five markup-breaking characters", () => {
  assert.equal(esc('&<>"\'"'), "&amp;&lt;&gt;&quot;&#39;&quot;");
});

test("esc escapes an ampersand", () => {
  assert.equal(esc("ACME & Sons"), "ACME &amp; Sons");
});

test("esc escapes tags and quotes in a script snippet", () => {
  assert.equal(
    esc("<script>alert('x')</script>"),
    "&lt;script&gt;alert(&#39;x&#39;)&lt;/script&gt;",
  );
});

test("esc leaves plain text unchanged", () => {
  assert.equal(esc("plain text 123"), "plain text 123");
});

test("esc coerces non-strings", () => {
  assert.equal(esc(42), "42");
  assert.equal(esc(false), "false");
});

test("esc maps null and undefined to empty string", () => {
  assert.equal(esc(null), "");
  assert.equal(esc(undefined), "");
});

test("esc maps 0 to a string (not empty)", () => {
  assert.equal(esc(0), "0");
});

/* ---------------- folderIdForPath ---------------- */

const folders = [
  { id: 1, folder_name: "inbox/acme", resolved_path: "/data/inbox/acme" },
  { id: 2, folder_name: "inbox/gamma", resolved_path: "/data/inbox/gamma" },
  // Windows-style resolved path (the runner resolves with backslashes).
  { id: 3, folder_name: "windows/path", resolved_path: "C:\\data\\windows\\path" },
];

test("matches the resolved absolute path exactly", () => {
  assert.equal(folderIdForPath("/data/inbox/acme", folders), 1);
});

test("matches the stored relative name exactly", () => {
  assert.equal(folderIdForPath("inbox/gamma", folders), 2);
});

test("matches an absolute path ending in the relative name (base-dir changed)", () => {
  assert.equal(folderIdForPath("/oldroot/inbox/gamma", folders), 2);
});

test("normalizes Windows backslashes", () => {
  assert.equal(folderIdForPath("C:\\data\\windows\\path", folders), 3);
  assert.equal(folderIdForPath("C:/data/windows/path", folders), 3);
});

test("ignores a trailing slash on the recorded folder", () => {
  assert.equal(folderIdForPath("/data/inbox/acme/", folders), 1);
});

test("returns null when the folder text is empty or null", () => {
  assert.equal(folderIdForPath("", folders), null);
  assert.equal(folderIdForPath(null, folders), null);
  assert.equal(folderIdForPath(undefined, folders), null);
});

test("returns null when no folders are provided", () => {
  assert.equal(folderIdForPath("/data/inbox/acme", undefined), null);
  assert.equal(folderIdForPath("/data/inbox/acme", null), null);
});

test("returns null when no folder matches", () => {
  assert.equal(folderIdForPath("/data/inbox/omega", folders), null);
});

test("returns null for a path that only shares a leaf name", () => {
  // "inbox/acme" must not match "/data/other/inbox/acme" unless the full
  // relative name is the suffix — here it is, so it matches. A path that
  // merely ends in "acme" without "/inbox/acme" must not match.
  assert.equal(folderIdForPath("/data/other/acme", folders), null);
  assert.equal(folderIdForPath("/data/inbox/acme", folders), 1);
});

test("prefers an exact resolved-path match over a suffix match", () => {
  const dup = [
    { id: 1, folder_name: "test", resolved_path: "/data/test" },
    { id: 2, folder_name: "sub/test", resolved_path: "/data/sub/test" },
  ];
  // Exact resolved path wins regardless of iteration order.
  assert.equal(folderIdForPath("/data/sub/test", dup), 2);
  assert.equal(folderIdForPath("/data/test", dup), 1);
});

/* ---------------- fmtErrorStamp ---------------- */

test("fmtErrorStamp passes ctime strings through unchanged", () => {
  assert.equal(fmtErrorStamp("Tue Aug 12 10:00:00 2026"), "Tue Aug 12 10:00:00 2026");
});

test("fmtErrorStamp reformats ISO timestamps to display form", () => {
  assert.equal(fmtErrorStamp("2026-08-12T10:00:00.000000"), "2026-08-12 10:00:00");
  assert.equal(fmtErrorStamp("2026-08-12T10:00:00"), "2026-08-12 10:00:00");
});

test("fmtErrorStamp returns an em-dash for empty values", () => {
  assert.equal(fmtErrorStamp(""), "—");
  assert.equal(fmtErrorStamp(null), "—");
  assert.equal(fmtErrorStamp(undefined), "—");
});

/* ---------------- fmtInterval ---------------- */

test("fmtInterval formats sub-minute intervals in seconds", () => {
  assert.equal(fmtInterval(0), "0s");
  assert.equal(fmtInterval(30), "30s");
  assert.equal(fmtInterval(59), "59s");
});

test("fmtInterval formats minute-long intervals in minutes", () => {
  assert.equal(fmtInterval(60), "1m");
  assert.equal(fmtInterval(120), "2m");
  assert.equal(fmtInterval(150), "3m");
});

/* ---------------- dialog helpers ---------------- */
// The dashboard's confirmDialog / alertDialog rely on `document` and
// the global `__bfsTestStubs` injection. Node has neither — so we run
// the helpers module fresh inside a vm context that provides both, and
// verify behaviour through the injected stubs.

const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

function loadHelpersInSandbox(stubReturn = true) {
  const code = fs.readFileSync(
    path.join(__dirname, "../../webapp/static/helpers.js"),
    "utf8",
  );
  const sandbox = {
    __bfsTestStubs: {
      confirmDialog: () => Promise.resolve(stubReturn),
      alertDialog: () => Promise.resolve(),
    },
  };
  vm.createContext(sandbox);
  vm.runInContext(code, sandbox);
  return sandbox;
}

function loadHelpersInDom() {
  // Run helpers.js inside a jsdom window so document.body exists and
  // the dialog can be rendered + dismissed without our test stubs.
  const { JSDOM } = require("jsdom");
  const dom = new JSDOM(`<!doctype html><html><body></body></html>`, {
    url: "http://localhost/",
    runScripts: "outside-only",
  });
  const code = fs.readFileSync(
    path.join(__dirname, "../../webapp/static/helpers.js"),
    "utf8",
  );
  vm.runInContext(code, dom.getInternalVMContext());
  return dom;
}

test("confirmDialog returns the stubbed promise when __bfsTestStubs is set", async () => {
  const sb = loadHelpersInSandbox(true);
  const ok = await sb.confirmDialog("Proceed?", { title: "Confirm" });
  assert.equal(ok, true);
});

test("confirmDialog returns false when the stub resolves to false", async () => {
  const sb = loadHelpersInSandbox(false);
  const ok = await sb.confirmDialog("Proceed?");
  assert.equal(ok, false);
});

test("alertDialog resolves without throwing when stubbed", async () => {
  const sb = loadHelpersInSandbox(true);
  await sb.alertDialog("Heads up");
  // Resolves to undefined; no exception is enough.
  assert.ok(true);
});

test("confirmDialog renders an in-page dialog when no stub is set", async () => {
  const dom = loadHelpersInDom();
  const ctx = dom.getInternalVMContext();
  const { document, KeyboardEvent } = dom.window;

  // Open the dialog, then click the primary button to confirm.
  const promise = ctx.confirmDialog("Delete?", { title: "Are you sure?" });
  const dlg = document.querySelector(".dlg");
  assert.ok(dlg, "dialog element rendered");
  assert.equal(dlg.getAttribute("role"), "alertdialog");
  assert.equal(dlg.getAttribute("aria-modal"), "true");
  const titleEl = document.getElementById("dlg-title");
  assert.equal(titleEl.textContent, "Are you sure?");
  const msgEl = document.getElementById("dlg-msg");
  assert.equal(msgEl.textContent, "Delete?");

  document.querySelector('[data-dismiss="confirm"]').click();
  const result = await promise;
  assert.equal(result, true);
  // Dialog hidden after dismiss.
  assert.equal(document.getElementById("dlg-root").hidden, true);
});

test("confirmDialog resolves false on Escape", async () => {
  const dom = loadHelpersInDom();
  const ctx = dom.getInternalVMContext();
  const { document, KeyboardEvent } = dom.window;

  const promise = ctx.confirmDialog("Cancel me");
  const root = document.getElementById("dlg-root");
  const evt = new KeyboardEvent("keydown", { key: "Escape" });
  root.dispatchEvent(evt);
  const result = await promise;
  assert.equal(result, false);
});

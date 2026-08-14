"use strict";

/*
 * helpers.js — pure, DOM-free helpers shared by the dashboard scripts.
 *
 * Loaded as a classic script before app.js (defines the globals ``esc``
 * and ``folderIdForPath``), and also exported via ``module.exports`` so
 * the unit tests in tests/webapp/helpers.test.js can require() it under
 * Node without a DOM or a bundler.
 */

// HTML-escape a value for interpolation into innerHTML templates. The
// five characters that terminate or inject markup are the only ones that
// need escaping; everything else passes through.
function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[c]));
}

// Map a ledger ``folder`` value (the resolved path the pipeline records)
// back to a configured folder id. The API filters by folder_id, so rows
// whose folder no longer exists in the config aren't clickable.
//
// folders: the ``/api/folders`` array (each entry has ``id``,
// ``folder_name`` (relative) and ``resolved_path``).
function folderIdForPath(folderText, folders) {
  if (!folderText || !folders) return null;
  const norm = String(folderText).replace(/\\/g, "/").replace(/\/+$/, "");
  let best = null;
  let bestLen = -1;
  for (const f of folders) {
    const resolved = String(f.resolved_path || "").replace(/\\/g, "/").replace(/\/+$/, "");
    const rel = String(f.folder_name || "").replace(/\\/g, "/").replace(/\/+$/, "");
    if (norm === resolved || norm === rel || norm.endsWith("/" + rel)) {
      // Several folders can suffix-match one absolute path ("sub/test"
      // vs "test"), so prefer the longest relative name instead of
      // whichever folder the list happens to list first.
      if (rel.length > bestLen) {
        best = f.id;
        bestLen = rel.length;
      }
    }
  }
  return best;
}

// Format a ledger timestamp for display. The ledger stores time.ctime()
// strings ("Tue Aug 12 10:00:00 2026"); keep a fallback for ISO
// timestamps in case a future writer uses them. The ISO check matches a
// "T<HH>:" separator rather than any capital T — ctime day names like
// "Tue"/"Thu"/"Sat" also contain a T and must pass through unchanged.
function fmtErrorStamp(s) {
  if (!s) return "—";
  return /T\d{2}:/.test(s) ? s.replace("T", " ").slice(0, 19) : s;
}

// Format a watch interval in seconds as a compact human string.
function fmtInterval(s) {
  return s < 60 ? `${s}s` : `${Math.round(s / 60)}m`;
}

// -------------------- async dialog helpers --------------------
//
// Promise-based replacements for window.confirm / window.alert. The
// browser modals are blocking (suspend every event loop until the user
// clicks), look out of place in the dashboard theme, and aren't keyboard
// navigable in jsdom tests. The custom dialog below:
//
//   - is non-blocking: returns a Promise the caller awaits
//   - is keyboard accessible: Escape cancels, Tab focuses the primary
//     action first, Enter activates it
//   - is aria-correct: role="alertdialog", aria-modal, aria-labelledby
//   - falls back to window.confirm / window.alert when document.body is
//     missing (Node tests without jsdom, or pre-DOM load)
//   - honours ``globalThis.__bfsTestStubs.confirmDialog`` /
//     ``globalThis.__bfsTestStubs.alertDialog`` when set (jsdom tests
//     inject these to avoid rendering an in-page dialog they can't
//     observe or dismiss)

function _bfsTestStub(name) {
  const stubs = (typeof globalThis !== "undefined" && globalThis.__bfsTestStubs) || null;
  return stubs && typeof stubs[name] === "function" ? stubs[name] : null;
}

function _dialogRoot() {
  if (typeof document === "undefined" || !document.body) return null;
  let root = document.getElementById("dlg-root");
  if (root) return root;
  root = document.createElement("div");
  root.id = "dlg-root";
  root.className = "dlg-root";
  root.hidden = true;
  document.body.appendChild(root);
  return root;
}

function _closeDialog(root, returnValue) {
  if (!root) return;
  root.hidden = true;
  root.innerHTML = "";
  // Drop focus back to whatever opened the dialog — operators who
  // dismissed via keyboard should land where they started.
  const opener = root.__opener;
  if (opener && typeof opener.focus === "function") opener.focus();
  root.__opener = null;
  root.__resolver(returnValue);
  root.__resolver = null;
}

function _attachKeyTrap(root, primaryBtn) {
  function onKey(e) {
    if (e.key === "Escape") {
      e.preventDefault();
      e.stopPropagation();
      _closeDialog(root, false);
    } else if (e.key === "Enter" && document.activeElement !== primaryBtn) {
      // Enter on the dialog body activates the primary action.
      e.preventDefault();
      primaryBtn.click();
    }
  }
  root.addEventListener("keydown", onKey);
  return () => root.removeEventListener("keydown", onKey);
}

// Show a styled confirm dialog. Resolves true on confirm, false on
// cancel. ``title`` is optional; defaults to "Confirm".
function confirmDialog(message, opts = {}) {
  const stub = _bfsTestStub("confirmDialog");
  if (stub) return stub(message, opts);
  const root = _dialogRoot();
  if (!root) {
    // Fallback for Node tests / pre-DOM load.
    return Promise.resolve(typeof window !== "undefined" ? window.confirm(String(message ?? "")) : false);
  }
  const { title = "Confirm", okLabel = "OK", cancelLabel = "Cancel", opener = null } = opts;
  return new Promise((resolve) => {
    root.__resolver = resolve;
    root.__opener = opener || (typeof document !== "undefined" ? document.activeElement : null);
    root.hidden = false;
    root.setAttribute("aria-hidden", "false");
    root.innerHTML = `
      <div class="dlg-backdrop" data-dismiss="cancel"></div>
      <div class="dlg" role="alertdialog" aria-modal="true" aria-labelledby="dlg-title" aria-describedby="dlg-msg">
        <h3 id="dlg-title" class="dlg__title">${esc(title)}</h3>
        <p id="dlg-msg" class="dlg__msg">${esc(message ?? "")}</p>
        <div class="dlg__actions">
          <button type="button" class="btn btn--ghost" data-dismiss="cancel">${esc(cancelLabel)}</button>
          <button type="button" class="btn btn--primary" data-dismiss="confirm">${esc(okLabel)}</button>
        </div>
      </div>`;
    const dlg = root.querySelector(".dlg");
    const primary = root.querySelector('[data-dismiss="confirm"]');
    dlg.addEventListener("click", (e) => {
      const action = e.target && e.target.dataset && e.target.dataset.dismiss;
      if (action === "confirm") _closeDialog(root, true);
      else if (action === "cancel") _closeDialog(root, false);
    });
    root.querySelector(".dlg-backdrop").addEventListener("click", () => _closeDialog(root, false));
    _attachKeyTrap(root, primary);
    if (primary && typeof primary.focus === "function") primary.focus();
  });
}

// Show a styled alert dialog. Resolves when dismissed. Falls back to
// window.alert when the DOM is unavailable.
function alertDialog(message, opts = {}) {
  const stub = _bfsTestStub("alertDialog");
  if (stub) return stub(message, opts);
  const root = _dialogRoot();
  if (!root) {
    return Promise.resolve(
      typeof window !== "undefined" && window.alert ? (window.alert(String(message ?? "")), undefined) : undefined
    );
  }
  const { title = "Notice", okLabel = "OK", opener = null } = opts;
  return new Promise((resolve) => {
    root.__resolver = resolve;
    root.__opener = opener || (typeof document !== "undefined" ? document.activeElement : null);
    root.hidden = false;
    root.setAttribute("aria-hidden", "false");
    root.innerHTML = `
      <div class="dlg-backdrop" data-dismiss="confirm"></div>
      <div class="dlg" role="alertdialog" aria-modal="true" aria-labelledby="dlg-title" aria-describedby="dlg-msg">
        <h3 id="dlg-title" class="dlg__title">${esc(title)}</h3>
        <p id="dlg-msg" class="dlg__msg">${esc(message ?? "")}</p>
        <div class="dlg__actions">
          <button type="button" class="btn btn--primary" data-dismiss="confirm">${esc(okLabel)}</button>
        </div>
      </div>`;
    const primary = root.querySelector('[data-dismiss="confirm"]');
    const dlg = root.querySelector(".dlg");
    dlg.addEventListener("click", (e) => {
      if (e.target && e.target.dataset && e.target.dataset.dismiss === "confirm") {
        _closeDialog(root, true);
      }
    });
    root.querySelector(".dlg-backdrop").addEventListener("click", () => _closeDialog(root, true));
    _attachKeyTrap(root, primary);
    if (primary && typeof primary.focus === "function") primary.focus();
  });
}

// Browser: top-level function declarations are already globals. Node:
// expose the helpers for tests.
if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    esc,
    folderIdForPath,
    fmtErrorStamp,
    fmtInterval,
    confirmDialog,
    alertDialog,
  };
}

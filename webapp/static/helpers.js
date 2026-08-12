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

// Browser: top-level function declarations are already globals. Node:
// expose the helpers for tests.
if (typeof module !== "undefined" && module.exports) {
  module.exports = { esc, folderIdForPath, fmtErrorStamp, fmtInterval };
}

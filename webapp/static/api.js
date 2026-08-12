"use strict";

/*
 * api.js — fetch helper for the Batch File Sender webapp.
 *
 * Loaded as a classic script before app.js, so it defines the global
 * ``api`` the dashboard uses. It also exports via ``module.exports`` so
 * the unit tests in tests/webapp/api.test.js can require() it directly
 * under Node without a DOM or a bundler.
 */

async function api(path, options) {
  // The webapp's POST endpoints take their arguments as query parameters
  // (FastAPI reads plain params from the query string, not the body).
  // fetch() has no ``params`` option, so serialize it into the URL here;
  // without this every ``params: {...}`` call silently drops its
  // arguments.
  if (options && options.params) {
    const qs = new URLSearchParams();
    for (const [k, v] of Object.entries(options.params)) {
      if (v === undefined || v === null) continue;
      qs.append(k, v);
    }
    const query = qs.toString();
    if (query) path += (path.includes("?") ? "&" : "?") + query;
    delete options.params;
  }
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

// Browser: top-level function declaration is already a global. Node:
// expose the helper for tests.
if (typeof module !== "undefined" && module.exports) {
  module.exports = { api };
}

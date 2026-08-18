"use strict";

/*
 * api.js — fetch helper for the Batch File Sender webapp.
 *
 * Loaded as a classic script before app.js, so it defines the global
 * ``api`` the dashboard uses. It also exports via ``module.exports`` so
 * the unit tests in tests/webapp/api.test.js can require() it directly
 * under Node without a DOM or a bundler.
 *
 * Phase 6.2: attaches ``Authorization: Bearer <token>`` to every
 * request when a token has been stored via :func:`setApiToken`. The
 * token lives in ``localStorage`` under the ``bfs_api_token`` key —
 * the dashboard's login prompt sets it on the first 401 and clears
 * it via :func:`clearApiToken` when the operator signs out. The
 * fetch wrapper is intentionally tolerant: a missing token simply
 * means no header is attached; the server decides what to do (pass
 * through, 401, or 503).
 */

const API_TOKEN_STORAGE_KEY = "bfs_api_token";

let _currentApiToken = null;

function _loadStoredToken() {
  // Treat both ``null`` and ``undefined`` as "not cached yet" so a
  // unit test that calls ``_resetApiTokenCache()`` (which sets the
  // value to ``undefined``) re-reads from storage on the next call.
  // Without the ``undefined`` check, the first call after a reset
  // would return ``undefined`` instead of the freshly-stored value.
  if (_currentApiToken !== null && _currentApiToken !== undefined) {
    return _currentApiToken;
  }
  try {
    _currentApiToken = window.localStorage.getItem(API_TOKEN_STORAGE_KEY) || "";
  } catch (_e) {
    // localStorage can throw in sandboxed iframes / private-browsing
    // contexts; an empty token is the safe default.
    _currentApiToken = "";
  }
  return _currentApiToken;
}

function setApiToken(token) {
  _currentApiToken = token || "";
  try {
    if (token) {
      window.localStorage.setItem(API_TOKEN_STORAGE_KEY, token);
    } else {
      window.localStorage.removeItem(API_TOKEN_STORAGE_KEY);
    }
  } catch (_e) {
    // Same sandboxing tolerance as :func:`_loadStoredToken` — the
    // in-memory value still applies for the lifetime of the page.
  }
}

function clearApiToken() {
  setApiToken("");
}

function getApiToken() {
  return _loadStoredToken();
}

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
  // Clone the options so the caller's headers object isn't mutated by
  // the bearer-token injection. ``structuredClone`` is available in
  // every browser the dashboard supports; fall back to a shallow
  // copy for older runtimes (no observable difference for the
  // headers-only mutation).
  let opts = options;
  const token = _loadStoredToken();
  if (token) {
    opts = options ? { ...options } : {};
    const headers = { ...(opts.headers || {}) };
    headers["Authorization"] = `Bearer ${token}`;
    opts.headers = headers;
  }
  const resp = await fetch(path, opts);
  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const body = await resp.json();
      detail = body.detail || detail;
    } catch (_e) { /* non-JSON error body */ }
    const err = new Error(detail);
    err.status = resp.status;
    // Phase 6.2: notify any DOM listeners (the dashboard's login
    // modal) that the request was rejected for auth reasons. The
    // event fires on the global object so test fixtures under Node
    // (no ``window``) can no-op it cleanly via a try/catch.
    if (resp.status === 401) {
      try {
        if (typeof window !== "undefined" && typeof window.dispatchEvent === "function") {
          window.dispatchEvent(new CustomEvent("bfs:api-401", { detail: { path, status: resp.status } }));
        }
      } catch (_e) {
        // CustomEvent may not exist in very old test runners; an
        // uncaught event-dispatch error must not mask the original
        // 401 the caller is going to handle.
      }
    }
    throw err;
  }
  return resp.json();
}

// Reset the in-memory token cache. Intended for tests — the cache
// is correct in production (a token once set stays set until the
// operator signs out), but unit tests need a clean slate between
// cases so a token set in test #1 doesn't leak into test #2.
function _resetApiTokenCache() {
  _currentApiToken = undefined;
}

// Browser: top-level function declaration is already a global. Node:
// expose the helper for tests.
if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    _resetApiTokenCache,
    api,
    API_TOKEN_STORAGE_KEY,
    clearApiToken,
    getApiToken,
    setApiToken,
  };
}

"use strict";

/*
 * Unit tests for webapp/static/api.js — the fetch wrapper the dashboard
 * uses for every /api call.
 *
 * Run with:  node --test tests/webapp/api.test.js
 * (or:        make test-js)
 *
 * Uses only Node's built-in test runner (node:test) — no dependencies.
 * pytest ignores this file (it only collects test_*.py).
 */

const { test, after } = require("node:test");
const assert = require("node:assert/strict");
const { api } = require("../../webapp/static/api.js");

const originalFetch = global.fetch;

// Stub global.fetch, capture every call, and return a canned response.
// body can be a value (resolved by resp.json()) or a function (so a test
// can make json() throw to simulate a non-JSON error body).
function stubFetch({ ok = true, status = 200, statusText = "OK", body = {} } = {}) {
  const calls = [];
  global.fetch = async (path, options) => {
    calls.push({ path, options });
    return {
      ok,
      status,
      statusText,
      json: async () => (typeof body === "function" ? body() : body),
    };
  };
  return calls;
}

after(() => {
  global.fetch = originalFetch;
});

test("serializes params into the URL", async () => {
  const calls = stubFetch();
  await api("/api/schedule", {
    method: "POST",
    params: { enabled: true, interval_seconds: 60 },
  });
  assert.equal(calls[0].path, "/api/schedule?enabled=true&interval_seconds=60");
});

test("drops params from the options handed to fetch", async () => {
  const calls = stubFetch();
  await api("/api/schedule", {
    method: "POST",
    params: { enabled: false },
  });
  assert.deepEqual(calls[0].options, { method: "POST" });
});

test("appends with & when the path already has a query string", async () => {
  const calls = stubFetch();
  await api("/api/errors?limit=50", { params: { folder_id: 3 } });
  assert.equal(calls[0].path, "/api/errors?limit=50&folder_id=3");
});

test("skips null and undefined params", async () => {
  const calls = stubFetch();
  await api("/api/mark-processed", {
    method: "POST",
    params: { folder_id: 1, folder_alias: null, notes: undefined, file_path: "" },
  });
  // Empty strings are kept (FastAPI accepts folder_alias=), null/undefined are not.
  assert.equal(calls[0].path, "/api/mark-processed?folder_id=1&file_path=");
});

test("URL-encodes special characters in param values", async () => {
  const calls = stubFetch();
  await api("/api/mark-processed", {
    method: "POST",
    params: { file_path: "/data/a b/c?d=1&e=2" },
  });
  assert.equal(
    calls[0].path,
    "/api/mark-processed?file_path=%2Fdata%2Fa+b%2Fc%3Fd%3D1%26e%3D2",
  );
});

test("leaves the path untouched when there are no params", async () => {
  const calls = stubFetch();
  await api("/api/folders");
  assert.equal(calls[0].path, "/api/folders");
  assert.equal(calls[0].options, undefined);
});

test("passes through non-params options (headers, body)", async () => {
  const calls = stubFetch();
  const body = JSON.stringify({ id: 1 });
  await api("/api/folders/1", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body,
  });
  assert.deepEqual(calls[0].options, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body,
  });
});

test("returns the parsed JSON on success", async () => {
  stubFetch({ body: { count: 3, errors: [] } });
  const out = await api("/api/errors");
  assert.deepEqual(out, { count: 3, errors: [] });
});

test("throws with detail and status on an error JSON body", async () => {
  stubFetch({
    ok: false,
    status: 422,
    statusText: "Unprocessable Entity",
    body: { detail: "Missing required query parameter" },
  });
  await assert.rejects(
    api("/api/schedule", { method: "POST" }),
    (err) =>
      err instanceof Error &&
      err.message === "Missing required query parameter" &&
      err.status === 422,
  );
});

test("falls back to statusText when the error body is not JSON", async () => {
  stubFetch({
    ok: false,
    status: 500,
    statusText: "Internal Server Error",
    body: () => {
      throw new Error("not json");
    },
  });
  await assert.rejects(
    api("/api/config"),
    (err) =>
      err instanceof Error &&
      err.message === "Internal Server Error" &&
      err.status === 500,
  );
});

test("uses the statusText when the error JSON has no detail", async () => {
  stubFetch({ ok: false, status: 404, statusText: "Not Found", body: {} });
  await assert.rejects(api("/api/runs/missing"), {
    name: "Error",
    message: "Not Found",
    status: 404,
  });
});

/* ---------------- Phase 6.2: bearer-token helpers ---------------- */

const { _resetApiTokenCache, setApiToken, getApiToken, clearApiToken } = require("../../webapp/static/api.js");

function _reset() { _resetApiTokenCache(); }

function withLocalStorage(initial = {}) {
  const stored = { ...initial };
  const mock = {
    getItem: (k) => (k in stored ? stored[k] : null),
    setItem: (k, v) => { stored[k] = String(v); },
    removeItem: (k) => { delete stored[k]; },
  };
  // The browser-side helper accesses ``window.localStorage``; in Node
  // we have to wire both ``global.localStorage`` (used by jsdom-style
  // tests) and ``global.window.localStorage`` (used by the api.js
  // helper directly).
  global.localStorage = mock;
  global.window = global.window || { addEventListener: () => {}, dispatchEvent: () => {} };
  global.window.localStorage = mock;
  return stored;
}

test("getApiToken returns empty string when nothing stored", () => {
  _reset();  withLocalStorage({});
  assert.equal(getApiToken(), "");
});

test("setApiToken stores in localStorage and getApiToken reads it back", () => {
  _reset();  const stored = withLocalStorage({});
  setApiToken("round-trip-secret");
  assert.equal(getApiToken(), "round-trip-secret");
  assert.equal(stored.bfs_api_token, "round-trip-secret");
  clearApiToken();
  assert.equal(getApiToken(), "");
  assert.equal(stored.bfs_api_token, undefined);
});

test("setApiToken('') clears the stored token", () => {
  _reset();  const stored = withLocalStorage({ bfs_api_token: "stale" });
  setApiToken("");
  assert.equal(getApiToken(), "");
  assert.equal(stored.bfs_api_token, undefined);
});

test("api attaches Authorization header when token is set in storage", async () => {
  _reset();  withLocalStorage({ bfs_api_token: "header-test" });
  const calls = [];
  global.fetch = async (path, options) => {
    calls.push({ path, options });
    return { ok: true, status: 200, json: async () => ({}) };
  };
  await api("/api/folders");
  assert.equal(calls[0].options.headers.Authorization, "Bearer header-test");
});

test("api attaches no Authorization header when no token is stored", async () => {
  _reset();  withLocalStorage({});
  const calls = [];
  global.fetch = async (path, options) => {
    calls.push({ path, options });
    return { ok: true, status: 200, json: async () => ({}) };
  };
  await api("/api/folders");
  const headers = calls[0].options && calls[0].options.headers;
  if (headers) {
    assert.equal(headers.Authorization, undefined);
  }
});

test("api dispatches bfs:api-401 event on 401", async () => {
  _reset();  withLocalStorage({});
  global.fetch = async () => ({
    ok: false, status: 401, statusText: "Unauthorized",
    json: async () => ({ detail: "Invalid bearer token" }),
  });
  const dispatched = [];
  global.window = {
    addEventListener: () => {},
    dispatchEvent: (e) => dispatched.push(e),
    CustomEvent,
  };
  await assert.rejects(api("/api/folders"), (err) => err.status === 401);
  const ev = dispatched.find((e) => e && e.type === "bfs:api-401");
  assert.ok(ev, "expected bfs:api-401 event");
  delete global.window;
});

test("api does not dispatch bfs:api-401 on non-401 errors", async () => {
  _reset();  withLocalStorage({});
  global.fetch = async () => ({
    ok: false, status: 500, statusText: "Internal Server Error",
    json: async () => ({}),
  });
  const dispatched = [];
  global.window = {
    addEventListener: () => {},
    dispatchEvent: (e) => dispatched.push(e),
    CustomEvent,
  };
  await assert.rejects(api("/api/config"), (err) => err.status === 500);
  assert.equal(dispatched.find((e) => e && e.type === "bfs:api-401"), undefined);
  delete global.window;
});

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

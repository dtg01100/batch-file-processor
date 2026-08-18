# Spec: Webapp Phase 6 — Production Hardening

**Status:** DRAFT (2026-08-18)
**Author:** Project Owner
**Created:** 2026-08-18
**Updated:** 2026-08-18

---

## 1. Summary

Close the production-readiness gap that came with the webapp pivot.
Phase 5 made processing observable from the browser; Phase 6 makes it
safe to actually *deploy* the webapp on anything other than localhost.
The four items in this phase are graded by impact and ordered by
risk-reduction:

1. **6.1 Bind `127.0.0.1` by default** — `host="0.0.0.0"` today exposes
   every endpoint to anyone on the LAN. Three-line fix.
2. **6.2 Single-user bearer-token auth** — opt-in remote access via a
   `BFS_API_TOKEN` env var; matches the spec's "single-user local-first"
   constraint without inventing a user table.
3. **6.3 Backend health probe** — extend `collect_diagnostics` to actually
   TCP-open SMTP/FTP and stat the copy destination, so the Diagnostics
   card answers "is the SMTP server actually reachable right now?".
4. **6.4 Soft-delete with restore window** — turn the permanent
   `DELETE /api/folders/{id}` into a recoverable action with a
   configurable N-day restore window.

Items deferred to a future audit (gap-3.x): TLS termination (6.2
makes it unnecessary), audit log (6.2 makes "who" meaningful),
backup encryption (single-host deployment), mobile responsive
(operator persona), Playwright (UI is settling), plugin hot-reload
(no external plugin authors yet). See
`docs/architecture/webapp-gap-audit.md` §5.

---

## 2. Background

### 2.1 Problem Statement

`specs/PROJECT_SPEC.md` §3.4 states the security intent: *"Credentials
stored only in the local SQLite DB; never logged; never sent off-machine
except to configured destinations"*, with the implicit anchor that the
product has *"no inbound network surface"* (the desktop app, locally
installed, has none). §3.6 explicitly rejected the "Browser-based web
UI" alternative because it *"complicates single-user local-first story"*.

The webapp-pivot (commit `9864dc7e5`) built exactly that rejected
alternative. The webapp runs an HTTP server with `host="0.0.0.0"`
(`webapp/main.py:173`), the `Dockerfile` exposes port 8000 with no
auth layer, and the README's quick-start instructs operators to
launch with `--host 0.0.0.0`. The webapp is currently safe to run
on a workstation with no other machines on the LAN; it is *not* safe
to deploy as a shared service on a corporate network.

The other three gaps compound the same risk: there is no way to tell
the operator whether the SMTP/FTP servers are currently reachable
(§6.3), and a single wrong click on **Delete** in the folders card
permanently destroys configuration (no undo, no recycle bin — §6.4).

### 2.2 Motivation

Operators want to put the webapp behind a reverse proxy on a server
(or use the Docker container on a shared host) so they don't have to
keep a workstation running. Today they can't safely do that. Phase 6
makes three small, well-scoped changes that together:

- close the entire network-exposure problem class (6.1),
- open the door to safe remote access if needed (6.2),
- answer the operator's most common operational question (6.3),
- remove a permanent-delete foot-gun (6.4).

### 2.3 Prior Art

- The desktop app had no inbound surface at all — that's the gold
  standard for the spec's intent. Phase 6.1 (bind localhost) restores
  that posture by default.
- `fastapi.security.HTTPBearer` is the idiomatic FastAPI auth scheme;
  the `BFS_API_TOKEN` pattern matches the existing `BFS_BASE_DIR` /
  `BFS_DATA_DIR` env-var loading in `webapp/config.py::Settings.from_env`.
- The Diagnostics card surface (`webapp/diagnostics.py`,
  `webapp/routers/system.py::api_diagnostics`) is the established place
  for self-test data; `webapp/watcher.py::list_watched` already exposes
  the `last_tick_at` / `last_run_id` / `last_error` watcher-health
  columns (added in phase 5). 6.3 extends the same pattern to the
  SMTP/FTP/copy backends.
- The soft-delete pattern mirrors the existing `MAX_HISTORY_ROWS` cap
  in `webapp/history.py` and the `MAX_ERROR_ROWS` cap in
  `webapp/errors.py` — a configurable window with a module constant
  default, surfaced through the dashboard for visibility.

---

## 3. Design

### 3.1 Architecture Alignment

- [x] Reviewed `docs/ARCHITECTURE.md` — webapp module is the operator-facing layer; `dispatch/` pipeline is reused untouched. All four items are webapp-local.
- [x] Reviewed `docs/DATABASE_DESIGN.md` — 6.4 adds a new table (`folders_deleted`) in the "kv_settings / webapp-owned" category (§5.1 of the project spec), same `folders.db` file, idempotent `CREATE TABLE IF NOT EXISTS` (matches the 5.1 / 5.2 pattern).
- [x] Reviewed `docs/TESTING_DESIGN.md` — new tests land in `tests/webapp/` alongside the existing 17 files.
- [x] Reviewed `docs/SECURITY_DESIGN.md` — credentials continue to live in `folders.db` only; 6.2 adds a *read* token (one env var, server-side) — no change to credential storage.
- [x] Reviewed `AGENTS.md` — no silent `except: pass`; 6.4 restore path uses `contextlib.suppress` with `logger.debug(..., exc_info=True)`, mirroring the existing import / restore patterns.

### 3.2 Components affected

- [x] `webapp/main.py` — `_lifespan` reads `BFS_API_TOKEN` and stashes it on `app.state.api_token`; `main()` reads `BFS_HOST` / `BFS_PORT` env vars; `create_app()` adds a single auth dependency at the router-include layer.
- [x] `webapp/routers/_deps.py` (new dep) — `verify_api_token` reads `app.state.api_token`; raises 401 when the header is missing/wrong, 503 when the token isn't configured (i.e. operator hasn't opted in to remote access). Returns immediately for the `/` static mount and `/api/health`.
- [x] `webapp/config.py` — `Settings.from_env` gains `host` / `port` fields with safe defaults (`127.0.0.1` / `8000`); the existing `Settings` constructor is unchanged so test fixtures aren't disturbed.
- [x] `webapp/diagnostics.py` — `collect_diagnostics` adds a `backends_health` section: SMTP `socket.create_connection((server, port), timeout=2)` (TLS or plain), FTP `ftplib.FTP().connect(server, port, timeout=2)` (login optional, controlled by `smtp_port`/`smtp_try_login`), copy destination `Path.is_dir()`. Every probe is wrapped in `_safe()` so a hung server can't take down the endpoint.
- [x] `webapp/database.py` — new idempotent `folders_deleted` table (`id`, `folder_id`, `deleted_at`, `expires_at`, `original_row_json`); a periodic trim job in the lifespan (every hour, configurable) purges expired rows.
- [x] `webapp/routers/folders.py` — `DELETE /api/folders/{folder_id}` moves the row to `folders_deleted` instead of issuing `DELETE FROM folders`; the operator can list / restore via `GET /api/folders/deleted` and `POST /api/folders/{folder_id}/restore`.
- [x] `webapp/static/index.html` + `webapp/static/app.js` — folders card gains a "Recently deleted" collapsible section with a per-row Restore button; Diagnostics card gains a Backends table.
- [x] `README.md` + `docker-compose.yml` + `Dockerfile` — quick-start binds `127.0.0.1`; docker-compose exposes via `127.0.0.1:8000:8000` (operator opts in to expose by changing the bind).
- [x] `specs/PROJECT_SPEC.md` — new §3.7 addendum capturing the webapp's deployment model and the rationale for 6.1 + 6.2.

### 3.3 Technical Approach

#### 6.1 Localhost by default

Three changes:

- `webapp/config.py::Settings.from_env` reads `BFS_HOST` (default
  `127.0.0.1`) and `BFS_PORT` (default `8000`).
- `webapp/main.py::main()` passes those to `uvicorn.run`.
- `webapp/main.py::create_app()` docstring updated; README quick-start
  shows `--host 0.0.0.0` as the *opt-in* path.

The `Dockerfile` keeps `EXPOSE 8000` (this is metadata, not a real
binding); `docker-compose.yml`'s `ports:` line changes from
`"8000:8000"` to `"127.0.0.1:8000:8000"` so a fresh `docker compose up`
binds the host port to localhost only. Operators who *want* remote
exposure change one line.

Tests: assert `Settings.from_env()` defaults to `127.0.0.1`; assert
`create_app(settings=Settings(host="127.0.0.1"))` doesn't bind anything
else; assert `main()` honors `BFS_HOST`/`BFS_PORT`.

#### 6.2 Bearer-token auth

- `BFS_API_TOKEN` env var, default empty (auth disabled).
- When empty: the `verify_api_token` dependency is a no-op; every
  endpoint behaves exactly as today.
- When set: every endpoint other than `/`, `/api/health`, and the
  static files mount requires `Authorization: Bearer <token>`. Wrong
  / missing token → 401; server unconfigured → 503 (so a misconfigured
  remote deployment fails closed, not open).
- The static UI is updated to: read the token from a `BFS_API_TOKEN`
  cookie-or-localStorage entry (set via a tiny login screen the first
  time the dashboard loads if the token is required), attach it as
  `Authorization: Bearer <token>` on every `fetch`. No CSRF needed —
  same-origin only (no CORS), and the token is never sent in URLs or
  logged.

Tests: assert endpoint requires token when configured, returns 401 on
wrong / missing token, returns 503 when server token is missing;
assert UI attaches the header.

#### 6.3 Backend health probe

`webapp/diagnostics.py::collect_diagnostics` gains a `backends_health`
key in the snapshot, computed via `_safe()` wrappers:

- **SMTP**: read `email.email_smtp_server` + `smtp_port` from
  kv_settings; `socket.create_connection((server, port), timeout=2)`,
  then optional `starttls()` + login if credentials are present. The
  `_safe()` wrapper turns a hung server into `{ok: False, error: "..."}`
  without raising.
- **FTP**: read `ftp.ftp_server` + `ftp_port` from the per-folder row
  if available, or fall back to kv_settings if there's a global default.
  `ftplib.FTP().connect(server, port, timeout=2)`; login is best-effort.
- **Copy destination**: for each folder whose `process_backend_copy` is
  on, `Path(resolved_path).is_dir()` (the same `path_exists` flag
  already computed in `folder_summary`).

The Diagnostics card's existing table grows by three rows (SMTP / FTP /
Copy); each shows a green / amber / red dot with the error message on
hover. The `ok` flag turns false if any backend is down.

Tests: assert the snapshot has the new section; assert a configured
SMTP server reports `{ok: True, latency_ms: N}`; assert an
unreachable SMTP server reports `{ok: False, error: "..."}`; assert the
endpoint never raises even when all probes time out.

#### 6.4 Soft-delete with restore window

- New `folders_deleted` table: `id`, `folder_id`, `deleted_at`,
  `expires_at` (default 30 days, configurable via
  `FOLDERS_DELETED_TTL_DAYS` env var, clamped to `[1, 365]`),
  `original_row_json` (the full pre-delete row, JSON-serialized).
- `DELETE /api/folders/{folder_id}`:
  - load the row,
  - insert into `folders_deleted` with `expires_at = now + TTL`,
  - delete from `folders` + cascade delete from `processed_files`
    (existing behavior),
  - return `{"deleted": folder_id, "expires_at": "..."}`.
- New `GET /api/folders/deleted` returns non-expired rows.
- New `POST /api/folders/{folder_id}/restore` reads the row from
  `folders_deleted`, re-inserts into `folders` with the original id,
  and deletes the `folders_deleted` entry. **Edge case**: if the
  original id is now in use (operator manually re-created the folder),
  return 409 Conflict with a message; do not silently overwrite.
- Lifespan starts a small periodic trim job (interval = 1h) that
  deletes expired rows from `folders_deleted`.

The folders card UI gains a collapsible "Recently deleted (N)" section
under the search box — a per-row Restore button + a row-level countdown
(`Expires in 27d`). The TTL is a single number in the Settings card
under a new "Soft-delete" group; default 30 days.

Tests: assert delete + restore round-trip preserves all fields; assert
expired rows don't show in `GET /api/folders/deleted` and are purged by
the trim job (the trim job is tested with a 0-second interval
override); assert the conflict-on-id-reuse path returns 409.

### 3.4 API changes

```python
# 6.1
#   BFS_HOST (default "127.0.0.1") and BFS_PORT (default 8000) env vars.
#   main() now reads them; create_app()'s docstring + README updated.

# 6.2
#   BFS_API_TOKEN env var. When set, every endpoint (except /, /api/health,
#   /docs, /openapi.json, /redoc) requires Authorization: Bearer <token>.
#   No new endpoint.

# 6.3
#   GET /api/diagnostics response grows by one key:
#       "backends_health": {
#           "smtp":   {"ok": bool, "latency_ms": float?, "error": str?},
#           "ftp":    {"ok": bool, "latency_ms": float?, "error": str?},
#           "copy":   [{"folder_id": int, "alias": str, "ok": bool,
#                       "error": str?}, ...]
#       }

# 6.4
#   DELETE /api/folders/{folder_id}
#       -> {"deleted": folder_id, "expires_at": iso8601}
#   GET    /api/folders/deleted
#       -> {"count": N, "rows": [{folder_id, deleted_at, expires_at, alias}, ...]}
#   POST   /api/folders/{folder_id}/restore
#       -> {"restored": folder_id, "alias": str}
#       409 if the id is now in use (manual re-create happened).
#   FOLDERS_DELETED_TTL_DAYS env var (default 30, clamp 1..365).
```

### 3.5 Data flow

```
[6.1 bind]  uvicorn.run(host=os.environ.get("BFS_HOST","127.0.0.1"),
                         port=int(os.environ.get("BFS_PORT","8000")))

[6.2 auth]  HTTP request
                │
                ▼
          verify_api_token (FastAPI dependency)
                │
                ├── app.state.api_token == ""  ─► pass-through
                │
                ├── header == token             ─► pass-through
                │
                ├── header missing / wrong      ─► 401
                │
                └── token not configured        ─► 503 (fail closed)

[6.3 probe] collect_diagnostics(...)
                │
                ├── _safe(smtp_connect)         ─► {"ok": bool, "latency_ms", "error"?}
                ├── _safe(ftp_connect)          ─► {"ok": bool, "latency_ms", "error"?}
                └── _safe(copy_path.is_dir)    ─► per-folder {"ok": bool, "error"?}

[6.4 soft-delete]
   DELETE /api/folders/{id}
       │
       ├── SELECT row FROM folders WHERE id = ?
       ├── INSERT INTO folders_deleted (id, folder_id, deleted_at, expires_at,
                                        original_row_json) VALUES (...)
       ├── DELETE FROM folders WHERE id = ?
       ├── DELETE FROM processed_files WHERE folder_id = ?
       └── return {"deleted": id, "expires_at": "..."}

   POST /api/folders/{id}/restore
       │
       ├── SELECT row FROM folders_deleted WHERE folder_id = ?
       ├── if folders.id == folder_id: 409
       ├── INSERT INTO folders (original_row_json deserialized) id = folder_id
       ├── DELETE FROM folders_deleted WHERE folder_id = ?
       └── return {"restored": id, "alias": "..."}

   [lifespan trim job, every 1h]
       DELETE FROM folders_deleted WHERE expires_at < now
```

### 3.6 Alternatives Considered

| Alternative | Pros | Cons | Why Not Chosen |
|-------------|------|------|----------------|
| Reverse-proxy auth only (nginx with basic auth in front) | No app code change | Couples deployment to a specific proxy setup; operator can't run the webapp on bare localhost without a proxy; doesn't solve "default config exposes" | Bind-localhost + bearer-token is the in-app equivalent, no proxy required |
| Full user table + login form | Matches a "real" webapp | Spec §3.4 says single-user local-first; user table + password reset is huge complexity for zero operational benefit | Bearer-token from env var is the single-user solution |
| TLS termination inside the webapp | Self-contained | Adds cert management to a config-file operator; nginx / Caddy is better-suited; the bearer-token is a separate concern | Documented as deferred (gap-3.x); operator can put nginx in front if needed |
| `0.0.0.0` by default, with a "secure by config" disclaimer | Smallest diff | Doesn't fix the actual foot-gun (operator forgets the flag) | Bind-localhost by default is the safe choice; opt-out is the explicit action |
| SMTP `EHLO` test for 6.3 | More thorough | Adds 200ms per probe; the TCP-open + (optional) login is the right granularity for "is the server alive" | TCP-open is enough to answer "is it reachable"; full protocol probe is gap-3.x territory |
| Trash folder in folders table for 6.4 | One table | Mixes live + deleted state; folder queries need a `WHERE deleted = 0` everywhere | Separate `folders_deleted` table keeps `folders` clean (queries unchanged) and the restore window is a single trim job |
| Permanent delete stays the default, opt-in soft-delete | Smallest diff | Doesn't fix the actual foot-gun; "I clicked Delete by accident" is the use case we're solving | Soft-delete is the default; permanent delete is a separate `POST /api/folders/{id}/purge` for the explicit rare case |
| Playwright tests in 6.x | Catches real-browser regressions | JSDOM + python tests already cover the surface; CSS-level changes slow the loop | Deferred to gap-3.x (Phase 7+) |

---

## 4. Implementation Plan

### Phase 6.1: Localhost by default (Estimated: 0.5 day)

- [ ] Task 6.1.1: Add `host` / `port` to `webapp.config.Settings.from_env` with `127.0.0.1` / `8000` defaults. Don't change `Settings.__init__` — keep tests stable.
- [ ] Task 6.1.2: `webapp/main.py::main()` reads `BFS_HOST` / `BFS_PORT` env vars (fall back to the `Settings` defaults).
- [ ] Task 6.1.3: `webapp/main.py::create_app()` docstring updated. `Dockerfile` `EXPOSE 8000` unchanged (metadata). `docker-compose.yml` `ports:` becomes `"127.0.0.1:8000:8000"`.
- [ ] Task 6.1.4: `README.md` quick-start updated to show `BFS_HOST=127.0.0.1` default and the opt-in `--host 0.0.0.0` line for remote access.
- [ ] Deliverable: a fresh `python -m webapp.main` binds to `127.0.0.1`; `--host 0.0.0.0` (or `BFS_HOST=0.0.0.0`) opts in.

### Phase 6.2: Bearer-token auth (Estimated: 1–2 days)

- [ ] Task 6.2.1: `webapp/main.py::_lifespan` reads `BFS_API_TOKEN` and stashes on `app.state.api_token`. When empty, `verify_api_token` is a no-op.
- [ ] Task 6.2.2: `webapp/routers/_deps.py` gains `verify_api_token(request)`. 401 on missing/wrong header; 503 on server-misconfigured (token required but not set).
- [ ] Task 6.2.3: Exempt `/`, `/api/health`, `/docs`, `/openapi.json`, `/redoc` via a small allowlist in `verify_api_token`.
- [ ] Task 6.2.4: `webapp/main.py::create_app()` applies `dependencies=[Depends(verify_api_token)]` to every router include.
- [ ] Task 6.2.5: `webapp/static/app.js` — when a request gets 401, prompt for the token (small `<dialog>`), store in `localStorage` under `bfs_api_token`, retry the request. Same fetch interceptor adds the header on every subsequent request.
- [ ] Task 6.2.6: `webapp/static/index.html` — `BFS_API_TOKEN` cookie / `localStorage` is read on boot; if the server returns 401 the token prompt fires.
- [ ] Task 6.2.7: `README.md` documents `BFS_API_TOKEN` env var, the 401/503 semantics, and the login-prompt UI.
- [ ] Task 6.2.8: `Dockerfile` / `docker-compose.yml` — `docker-compose.yml` gains `BFS_API_TOKEN` in `environment:` (commented out by default); example shows how to set it.
- [ ] Deliverable: an operator can `BFS_API_TOKEN=<secret> python -m webapp.main --host 0.0.0.0` and the dashboard logs in via the prompt; without the env var, every endpoint behaves as before.

### Phase 6.3: Backend health probe (Estimated: 1 day)

- [ ] Task 6.3.1: `webapp/diagnostics.py` gains `_probe_smtp`, `_probe_ftp`, `_probe_copy` helpers, all wrapped in `_safe()`. `collect_diagnostics` adds a `backends_health` key with the three sections.
- [ ] Task 6.3.2: `webapp/routers/system.py` (the diagnostics endpoint) — response shape gains `backends_health`; no other change.
- [ ] Task 6.3.3: `webapp/static/index.html` + `webapp/static/app.js` — Diagnostics modal grows by a "Backends" table (three rows: SMTP, FTP, Copy); green / amber / red dot per row + error message on hover.
- [ ] Deliverable: the Diagnostics card reports SMTP / FTP / copy health on every page load; `ok` is false if any backend is down.

### Phase 6.4: Soft-delete with restore window (Estimated: 2 days)

- [ ] Task 6.4.1: `webapp/database.py::_ensure_columns` adds `folders_deleted` `CREATE TABLE IF NOT EXISTS` (id, folder_id, deleted_at, expires_at, original_row_json).
- [ ] Task 6.4.2: `webapp/config.py::Settings.from_env` reads `FOLDERS_DELETED_TTL_DAYS` (default 30, clamp 1..365).
- [ ] Task 6.4.3: `webapp/routers/folders.py::api_delete_folder` moves the row to `folders_deleted` instead of issuing `DELETE FROM folders`. Returns `{"deleted": id, "expires_at": "..."}`.
- [ ] Task 6.4.4: New `webapp/routers/folders.py::api_list_deleted` and `api_restore_folder` endpoints.
- [ ] Task 6.4.5: `webapp/main.py::_lifespan` starts a periodic trim task (1h interval) that deletes expired rows.
- [ ] Task 6.4.6: `webapp/static/index.html` + `webapp/static/app.js` — folders card gains a collapsible "Recently deleted (N)" section; per-row Restore button + countdown ("Expires in 27d"). Settings card gains a "Soft-delete" group with the TTL field.
- [ ] Deliverable: deleting a folder surfaces a Restore button for 30 days; restoring re-creates the row exactly as it was (id + alias + path + all 50+ settings); expired rows are purged by the trim job.

---

## 5. Database Changes

### 5.1 Schema Changes

```sql
-- New table (created idempotently in webapp/database.py::_ensure_columns,
-- same folders.db file, no version bump)
CREATE TABLE IF NOT EXISTS folders_deleted (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    folder_id           INTEGER NOT NULL,
    deleted_at          TEXT    NOT NULL,
    expires_at          TEXT    NOT NULL,
    original_row_json   TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS folders_deleted_expires_idx
    ON folders_deleted(expires_at);
```

### 5.2 Migration Strategy

- No `migrations/` version bump. The webapp already handles in-place
  additions via `webapp/database.py::_ensure_columns` (used for
  `watch_enabled` / `watch_interval_seconds` in 4.3,
  `dispatch_errors` + watcher-health columns in 5.1/5.2).
  `folders_deleted` follows the identical pattern; `DatabaseObj`
  migration logic is untouched.
- Backup: unaffected — the existing backup/restore feature snapshots
  `folders.db`, which now includes the new table.

### 5.3 Migration Checklist

- [ ] Add `folders_deleted` table + index to `_ensure_columns`
- [ ] Verify a pre-6.4 database (missing the table) upgrades in place
      on `open_database`
- [ ] No changes to `core/database/schema.py` or `migrations/`

---

## 6. Testing Strategy

### 6.1 Test Cases

| Test Case | Type | Description | Expected Result | Phase |
|-----------|------|-------------|-----------------|-------|
| `test_settings_default_host_is_localhost` | webapp | `Settings.from_env()` with no env vars | `host == "127.0.0.1"`, `port == 8000` | 6.1 |
| `test_main_honors_env_hosts` | webapp | `main()` with `BFS_HOST=0.0.0.0` | uvicorn bound to 0.0.0.0 | 6.1 |
| `test_endpoint_requires_token_when_configured` | webapp | `BFS_API_TOKEN` set, request without header | 401 | 6.2 |
| `test_endpoint_returns_503_when_token_unset` | webapp | Server requires token, request without header (token actually unset server-side) | 503 | 6.2 |
| `test_endpoint_passes_through_when_token_empty` | webapp | `BFS_API_TOKEN` unset, request without header | 200 | 6.2 |
| `test_health_exempt_from_auth` | webapp | Token required, GET `/api/health` without header | 200 | 6.2 |
| `test_diagnostics_includes_backends_health` | webapp | Probe a fake SMTP server | `backends_health.smtp.ok == True` | 6.3 |
| `test_diagnostics_unreachable_smtp` | webapp | Probe an unroutable SMTP server | `backends_health.smtp.ok == False, error != None` | 6.3 |
| `test_soft_delete_moves_row` | webapp | DELETE folder, list deleted | Row visible in `folders_deleted`, not in `folders` | 6.4 |
| `test_soft_delete_restore_round_trip` | webapp | DELETE then restore | Row matches original on every field | 6.4 |
| `test_restore_conflict_on_id_reuse` | webapp | DELETE folder #7, manually re-create folder #7, attempt restore | 409 Conflict | 6.4 |
| `test_expired_rows_purged_by_trim` | webapp | Insert row with `expires_at` in the past, run trim | Row deleted | 6.4 |
| `test_ttl_clamp` | webapp | `FOLDERS_DELETED_TTL_DAYS=999` | TTL clamped to 365 | 6.4 |

### 6.2 Test File Locations

- `tests/webapp/test_config.py` (new) — env-var defaults
- `tests/webapp/test_auth.py` (new) — 6.2 token behavior
- `tests/webapp/test_diagnostics.py` (extend) — backends_health section
- `tests/webapp/test_soft_delete.py` (new) — 6.4 behavior
- `tests/webapp/dom.test.js` (extend) — login prompt, restore button, backends health table

### 6.3 Coverage Requirements

- [ ] New code covered by tests
- [ ] Existing tests still pass (baseline 265 webapp python + 24 DOM)
- [ ] `ruff check webapp/ tests/webapp/` clean
- [ ] `black --check webapp/ tests/webapp/` clean on changed files

---

## 7. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Bind-localhost breaks an operator's existing deployment (today they rely on `--host 0.0.0.0`) | Med | Low | README + changelog note the default change; opt-in is one env var; the Dockerfile change is non-breaking (EXPOSE unchanged); only docker-compose.yml changes binding |
| Bearer-token sent over plain HTTP leaks to a network sniffer | Med | Med | The spec defers TLS to gap-3.x; the token is the same risk class as the SMTP/FTP credentials the operator already has in `folders.db`. Document the pairing: bearer-token + nginx-TLS-in-front |
| 6.3 SMTP probe leaves a hanging connection if the server accepts but doesn't respond | Low | Low | `socket.create_connection(..., timeout=2)` + `_safe()` wrapper; the probe runs on demand (not on a background loop), so a leak is bounded |
| 6.4 trim job races with a restore (row expires mid-restore) | Low | Low | Restore reads-then-deletes under `lock()`; the trim job also takes `lock()`. The race window is the inter-job interval; restore always re-checks `expires_at` before inserting |
| 6.4 restored folder's processed_files orphans reappear in `/api/processed-files` for a folder that was "deleted" between restore calls | Low | Low | Restore re-inserts the folders row but doesn't touch processed_files (which is correct — those rows belong to the folder). Documented in the restore endpoint docstring |
| Default-bind change surprises a CI test that assumes 0.0.0.0 | Low | Low | Existing tests use `create_app(settings=Settings())` and never inspect the bind; no test changes required |

### 7.1 Rollback Plan

Each phase is a self-contained commit. Reverting 6.1 reverts the env-var reading + the docker-compose change; reverts are safe because the original `host="0.0.0.0"` literal still exists as the fallback when `BFS_HOST` is unset (and tests pass `Settings(host="127.0.0.1")` explicitly). Reverting 6.2 reverts the auth dependency; the static UI's token-prompt is a no-op when the server has no token configured. Reverting 6.3 / 6.4 removes the diagnostic probes / `folders_deleted` table — no data migration to unwind (the new table is additive and harmless if left in place).

---

## 8. Success Criteria

- [ ] `python -m webapp.main` with no env vars binds to `127.0.0.1:8000` (verified by the smoke test in `test_main_honors_env_hosts`).
- [ ] `BFS_API_TOKEN=<secret>` enables bearer-token auth; 401 on wrong/missing header; UI login prompt stores the token and retries.
- [ ] Diagnostics card shows SMTP / FTP / copy health on every page load; the `ok` flag reflects the worst probe result.
- [ ] Deleting a folder surfaces a Restore button in the "Recently deleted" section; restoring re-creates the folder with all settings intact; expired rows are purged by the trim job.
- [ ] All existing webapp tests still pass (265 → baseline + new); ruff + black clean on changed files.
- [ ] `specs/PROJECT_SPEC.md` §3.7 addendum published with the deployment-model rationale.

---

## 9. Open Questions

1. Should the bearer-token be a long-lived secret (current design) or a short-lived JWT? JWT adds a refresh flow the spec doesn't want. **TENTATIVE:** long-lived secret from env var, documented as "rotate by restarting with a new `BFS_API_TOKEN`". Resolve during 6.2 implementation.
2. Should the 6.4 trim job be a real background thread (current design) or run on each `/api/folders` GET? Background thread is cleaner; on-demand is cheaper. **TENTATIVE:** background thread with 1h interval; the `Settings` constructor accepts an override (`trim_interval_seconds=0`) so tests can run synchronously. Resolve during 6.4 implementation.
3. Should 6.3 probe ALL folders' copy destinations (current design) or just the active ones? All-folder gives the operator a complete view; active-only is faster on a 200-folder setup. **TENTATIVE:** all folders (the probe is a stat call, ~µs each; 200 folders is sub-millisecond). Resolve during 6.3 implementation.
4. Should 6.1 change the `Dockerfile` to also `USER` to a non-root account (small Docker-hardening bonus)? Not strictly 6.1, but it's a related "production-safe by default" change. **TENTATIVE:** add a `USER` line at the end of the `Dockerfile` (non-root uid). Tracked separately if pursued.

---

## 10. Appendix

### 10.1 References

- `specs/PROJECT_SPEC.md` §3.4 (NFRs), §3.5 (release channels), §3.6 (alternatives), §3.7 (new addendum, Phase 6 follow-on)
- `docs/architecture/webapp-gap-audit.md` §5 (gap-2.x audit)
- `webapp/main.py` (`uvicorn.run`, `_lifespan`)
- `webapp/config.py` (`Settings.from_env`)
- `webapp/diagnostics.py` (`collect_diagnostics`, `_safe`)
- `webapp/database.py` (`_ensure_columns` idempotent DDL)
- `webapp/errors.py` (`MAX_ERROR_ROWS` cap pattern — model for 6.4 trim job)
- `webapp/history.py` (`MAX_HISTORY_ROWS` cap pattern)
- Commit `9864dc7e5` (pivot)
- Phase-5 spec: `specs/webapp-phase-5-observability.md` (template)

### 10.2 Changelog

| Date | Author | Change |
|------|--------|--------|
| 2026-08-18 | Project Owner | Initial draft — 6.1/6.2/6.3/6.4 scope; gap-2.x audit §5 candidates graded |

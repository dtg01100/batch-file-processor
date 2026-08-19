# Operator Runbook

> **Who this is for:** an operator with a broken run, a missing
> file, an unreachable backend, or a database that "looks weird"
> — and 30 seconds to figure out where to look. The webapp
> already exposes every endpoint the answers live on; this
> document is the index.
>
> **Auth note:** if you set `BFS_API_TOKEN` (Phase 6.2), every
> endpoint below except `/api/health` requires
> `Authorization: Bearer <token>`. The `curl` examples include
> the header conditionally; replace `$BFS_API_TOKEN` with your
> actual token or omit the `-H` line if auth is disabled.

---

## 1. "A run failed"

Start at the run itself, then drill down.

```bash
# List recent runs (newest first; in-memory + persisted).
curl -s http://localhost:8000/api/runs | jq '.[:5]'

# Pull one run's per-folder breakdown + status + timing.
curl -s http://localhost:8000/api/runs/$RUN_ID | jq

# Stream the per-folder log (SSE; blocks until the run finishes
# or curl times out).
curl -N -s http://localhost:8000/api/runs/$RUN_ID/log
```

If the run detail shows `status: "failed"` for any folder, the
error is usually already in the **error ledger** — Phase 5 wired
the runner to write to `dispatch_errors` on every processing error:

```bash
# All errors (filter by folder if needed).
curl -s "http://localhost:8000/api/errors?limit=50" | jq

# Errors for one folder.
curl -s "http://localhost:8000/api/errors?folder_id=$FOLDER_ID&limit=20" | jq
```

Each ledger row has `error_message`, `stack_trace`, `timestamp`,
`severity` (Phase 5.5 added `major`/`minor` for EDI validation
failures). If the ledger is empty, fall back to the raw error-text
artifact on disk (per-folder, in `data/config/errors/`), downloadable
via:

```bash
curl -s -OJ "http://localhost:8000/api/errors/file?folder=$FOLDER_NAME"
```

**What you'll see (run detail shape):**

```json
{
  "run_id": "8d4f-...",
  "status": "failed",
  "started_at": "2026-08-18T03:00:00",
  "finished_at": "2026-08-18T03:01:23",
  "duration_seconds": 83.4,
  "folders": [
    {"folder_id": 1, "alias": "ACME", "status": "failed",
     "files_processed": 12, "files_failed": 1,
     "error": "OSError: [Errno 22] Invalid argument"}
  ]
}
```

**What to do next:** fix the underlying error (config typo, backend
unreachable, file-permission issue), then either re-run via the
dashboard's **Run all folders** button or
`curl -X POST http://localhost:8000/api/run`.

---

## 2. "Files aren't being picked up"

The watcher is a polling thread per folder (Phase 4.3). When it
stops seeing files, the first question is "did the tick even run?"

```bash
curl -s http://localhost:8000/api/watched | jq
```

Each row has `last_tick_at`, `last_run_id`, `last_error`. A
folder with `last_tick_at` older than 5× its `watch_interval_seconds`
is stuck. The dashboard's **Watching** card shows the same data
with the per-row error surfaced inline.

If the row is missing entirely, the folder's `watch_enabled`
flag is off — fix that via the folder editor (`PUT /api/folders/{folder_id}`)
or the dashboard's folder panel.

If the row is present but `last_error` is set, the row points at
the failure mode:

```bash
curl -s "http://localhost:8000/api/errors?folder_id=$FOLDER_ID" | jq '.rows[0]'
```

Common causes (in order of likelihood):

- **Folder path doesn't exist.** The watcher logs `OSError` on
  `iterdir`. The Diagnostics card's `paths.database_exists` row
  shows whether the *DB* exists; the folder path itself is
  resolved against `BFS_BASE_DIR` and isn't checked separately.
- **Permission denied.** Same `OSError`, different errno. Check
  that the webapp process user can read the folder.
- **Backend unreachable at send time.** The watcher catches
  per-file send failures but doesn't always crash the tick; check
  §3 below.

**What to do next:** if the tick is genuinely stuck, force a refresh:

```bash
curl -X POST http://localhost:8000/api/watcher/refresh
```

This re-reads the watch list and re-starts any tickers that died.
It's safe to call repeatedly.

---

## 3. "The dashboard says SMTP/FTP is unreachable"

Phase 6.3 added the Backends table in the Diagnostics card. The
JSON is `backends_health.{smtp, ftp, copy}`:

```bash
curl -s http://localhost:8000/api/diagnostics | jq '.backends_health'
```

**What you'll see:**

```json
{
  "smtp": {
    "ok": false,
    "latency_ms": 2.0,
    "error": "Connection refused (errno 111)"
  },
  "ftp": {
    "ok": true,
    "latency_ms": 87.3
  },
  "copy": [
    {"folder_id": 1, "alias": "ACME", "ok": true,
     "error": null},
    {"folder_id": 2, "alias": "GLOBEX", "ok": false,
     "error": "/mnt/archive/globex does not exist"}
  ]
}
```

Each probe is bounded by a 2-second timeout, so a hung server
can't stall the diagnostics card. "not configured" is a sentinel
string (not an error) meaning the operator hasn't pointed this
backend at a server yet — the dashboard renders it as amber but
doesn't light up the global "warnings" banner.

**What to do next:**

- **smtp**: check `email.smtp_server` and `smtp_port` in the
  Settings card; verify the SMTP server is reachable from the
  webapp host (`nc -zv $SMTP_HOST $SMTP_PORT`).
- **ftp**: check `ftp_server` / `ftp_port` / credentials per folder.
- **copy**: check that the destination directory exists and is
  writable. The `paths.base_dir` row in the same diagnostics
  payload tells you what the webapp thinks the base directory is.

---

## 4. "I deleted a folder by accident"

Phase 6.4 turned delete into soft-delete with a configurable
restore window (`FOLDERS_DELETED_TTL_DAYS`, default 30 days). The
row sits in `folders_deleted` until the trim supervisor purges it.

```bash
# List non-expired soft-deleted folders (sorted by expires_at asc
# — the row closest to expiry is at the top).
curl -s http://localhost:8000/api/folders/deleted | jq

# Restore one.
curl -X POST http://localhost:8000/api/folders/$FOLDER_ID/restore
```

**What you'll see (list):**

```json
{
  "count": 1,
  "rows": [
    {"folder_id": 7, "deleted_at": "2026-08-18T19:00:00+00:00",
     "expires_at": "2026-09-17T19:00:00+00:00", "alias": "ACME"}
  ]
}
```

**Edge cases:**

- **404**: no tombstone with that `folder_id`. The row is either
  already restored or already trimmed. The dashboard's
  "Recently deleted" section won't show it either.
- **409**: the operator manually recreated a folder with the
  same id between delete and restore. The new row would be
  silently overwritten; the API refuses instead. Rename or
  delete the new folder first, then restore.
- **410 Gone**: the tombstone expired but the trim hasn't run
  yet. The row will be gone on the next trim tick (default 1h).

**What to do next:** the restored row preserves the original `id`,
so any `processed_files` references from before the delete are
re-attached to the restored row. No data loss.

---

## 5. "I want to know if the operator-configured things still work"

The Diagnostics card is the single source of truth. It's a single
endpoint that surfaces platform, paths, DB, runtime, backends,
modules, and recent runs in one payload:

```bash
curl -s http://localhost:8000/api/diagnostics | jq
```

The `ok` field is `true` only if **all** of:

- every expected Python module imports cleanly,
- no run failed in the last 24h,
- no watcher is in a bad state,
- SMTP/FTP probes are either up or "not configured" (down with an
  error is a warning, not a module failure).

The `warnings` list is the human-readable summary. The dashboard
banner is green when `ok: true`, amber otherwise.

**What to do next:** click the Diagnostics modal in the
dashboard — it has a "Copy JSON" button (Phase 5.2) that drops
the same payload into your clipboard for ticket attachments.

---

## 6. "The database looks weird"

Start with the read-only overview:

```bash
curl -s http://localhost:8000/api/config | jq
```

This is the answer to "where does the webapp think the DB lives,
and does the file exist?" — `base_dir`, `data_dir`,
`database_path`, `database_exists`, `database_size_bytes`.

If the database is fine but you want to roll back to a known-good
state:

```bash
# List timestamped backups.
curl -s http://localhost:8000/api/backups | jq

# Snapshot the current DB (creates a new entry in the list).
curl -X POST http://localhost:8000/api/backup/create

# Restore a named backup as the active DB.
curl -X POST http://localhost:8000/api/backup/restore \
  -H 'Content-Type: application/json' \
  -d '{"name": "folders-20260818-180000.db"}'

# Download a backup file (out-of-band).
curl -s -OJ "http://localhost:8000/api/backup/download?name=folders-20260818-180000.db"
```

**What you'll see (config shape):**

```json
{
  "base_dir": "/data",
  "data_dir": "/data/config",
  "database_path": "/data/config/folders.db",
  "database_exists": true,
  "database_size_bytes": 75648000,
  "backups_dir": "/data/config/backups"
}
```

**What to do next:** if the restore hangs or fails, the
Diagnostics card's `database.version` row tells you what the
webapp thinks the schema version is. Phase 7.1's
`schema_repaired_at` marker means a healthy at-version DB no
longer pays the migration-repair cost on every open; if you
suspect schema drift, look at `webapp/diagnostics.py::collect_diagnostics`
to see what the probes are actually checking.

---

## Appendix: endpoints this runbook references

Every endpoint above is defined in `webapp/routers/`:

| Endpoint | Router file |
|----------|-------------|
| `GET /api/runs` | `webapp/routers/runs.py` |
| `GET /api/runs/{run_id}` | `webapp/routers/runs.py` |
| `GET /api/runs/{run_id}/log` | `webapp/routers/runs.py` (SSE) |
| `POST /api/run` | `webapp/routers/runs.py` |
| `GET /api/errors` | `webapp/routers/errors.py` |
| `GET /api/errors/file` | `webapp/routers/errors.py` |
| `GET /api/errors/folder-file` | `webapp/routers/errors.py` |
| `GET /api/watched` | `webapp/routers/watcher.py` |
| `POST /api/watcher/refresh` | `webapp/routers/watcher.py` |
| `GET /api/folders/deleted` | `webapp/routers/folders.py` |
| `POST /api/folders/{folder_id}/restore` | `webapp/routers/folders.py` |
| `GET /api/diagnostics` | `webapp/routers/system.py` |
| `GET /api/config` | `webapp/routers/system.py` |
| `GET /api/backups` | `webapp/routers/backups.py` |
| `POST /api/backup/create` | `webapp/routers/backups.py` |
| `POST /api/backup/restore` | `webapp/routers/backups.py` |
| `GET /api/backup/download` | `webapp/routers/backups.py` |

If a future phase retires one of these, the runbook's
`test_runbook_endpoints_referenced` test (Phase 7.1, currently
skipped pending this doc) catches the drift at CI time.
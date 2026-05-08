# Backend/Tweaks Selection: 730c42b69 vs Current — Analysis Summary

**Date:** May 8, 2026
**Purpose:** Ensure recipients get the same file formats after upgrading from commit 730c42b69

---

## Commit 730c42b69af4be753867d117b6e326470ffbd6d6

This commit (Jan 21, 2026) contained a single `.gitignore` change — it is not a meaningful point in the dispatch refactoring history. However, the commit **was reachable** and the state of `dispatch.py` at that commit represents the "pre-refactor" code that was later replaced.

---

## Old Code Path (dispatch.py at 730c42b69)

The old dispatch code had three blocks, all nested inside `if os.path.exists(output_send_filename):`:

```python
# Block 1: COPY block (process_edi != "True")
if parameters_dict['process_edi'] != "True" and errors is False:
    shutil.copyfile(output_send_filename, output_filename)
    output_send_filename = output_filename

# Block 2 + 3: inside `if valid_edi_file: if errors is False:`
    # CONVERSION block (gated by process_edi)
    if parameters_dict['process_edi'] == "True":
        output_send_filename = module.edi_convert(...)

    # TWEAKS block (NO process_edi gate)
    if parameters_dict['tweak_edi'] is True:
        output_send_filename = edi_tweaks.edi_tweak(...)
```

### Key Findings About Old Code

1. **Copy block runs when `process_edi != "True"`** — copies original EDI to scratch dir (same content)
2. **Conversion block requires `process_edi == "True"`** — skipped otherwise. With `process_edi="True"` and empty `convert_to_format`, it tries to `import convert_to_` which raises `ImportError` → `errors=True`, file not sent.
3. **Tweaks block only requires `tweak_edi is True`** — no `process_edi` check. Both blocks 2 and 3 are inside `if valid_edi_file:`, so tweaks also require EDI validation to pass (which it always does when triggered by `tweak_edi=True`).

This means **tweaks ran even when `process_edi='False'`**, as long as `tweak_edi=True`.

4. **Validation triggered by** `process_edi=="True" OR tweak_edi OR split_edi OR force_edi_validation`

### Important: String vs. Boolean Storage

In the v32 legacy database, booleans were stored as Python string literals (`'True'`/`'False'`). The old code compared `process_edi == "True"` (string match) and `tweak_edi is True` (Python bool). This means `process_edi='False'` did **not** prevent tweaks from running.

---

## Production Database State (all installs at v32)

All production databases are at v32. The fixture `tests/fixtures/legacy_v32_folders.db` is representative:

- **530 total folders**
- **150 enabled** (`process_edi='True'`)
- **380 disabled** (`process_edi='False'`)
- **110 had `tweak_edi=1`** — all 110 also had `process_edi='False'`

These 110 folders received **Tweaked EDI** in the old code despite `process_edi='False'`, because `tweak_edi` bypassed the `process_edi` gate entirely.

Format breakdown of the 110 tweak folders:

| `convert_to_format` | Count | Old result |
|---------------------|-------|-----------|
| `'csv'` | 85 | **Tweaked EDI** (conversion skipped, tweaks ran) |
| `'Estore eInvoice Generic'` | 15 | **Tweaked EDI** |
| `'YellowDog CSV'` | 4 | **Tweaked EDI** |
| `'simplified_csv'` | 2 | **Tweaked EDI** |
| `'stewarts_custom'` | 2 | **Tweaked EDI** |
| `'scansheet-type-a'` | 1 | **Tweaked EDI** |
| `''` | 1 | **Tweaked EDI** |

The stored `convert_to_format` was irrelevant — conversion was skipped because `process_edi='False'`. Only tweaks ran.

---

## What the Migration Did (v44 in folders_database_migrator.py)

Before v44, `_normalize_legacy_v32_values()` runs and converts all string booleans:
- `process_edi='False'` → `0` (integer)
- `tweak_edi=1` stays `1`

Then v44 runs with these rules:

```python
# Case A (enabled): tweak_edi=1 + (process_edi=NULL/≠0) + format stored
#   → process_edi=1, tweak_edi=0 (honour stored format)

# Case B (enabled): tweak_edi=1 + (process_edi=NULL/≠0) + NO format
#   → convert_to_format='tweaks', process_edi=1, tweak_edi=0

# Case C (disabled): tweak_edi=1 + process_edi=0 + format stored
#   → tweak_edi=0 only (respect explicit disable)

# Case D (disabled): tweak_edi=1 + process_edi=0 + NO format
#   → tweak_edi=0 only (respect explicit disable)
```

**The bug**: all 110 production folders have `process_edi='False'` → normalized to `0` → fall into Case C/D → `tweak_edi` cleared but `process_edi` kept at `0`. At runtime `process_edi=0` blocks the converter and these folders go back to sending **plain EDI** — losing the tweaks that recipients were receiving.

The intent behind Cases C/D was to respect folders where the user had explicitly disabled processing. But `process_edi='False'` with `tweak_edi=1` was not an explicitly-disabled folder — it was a folder where the UI's inconsistency allowed tweaks to run despite `process_edi` being false. The user expected tweaks to run.

---

## All Configurations Traced (Old Code)

| process_edi | tweak_edi | convert_to_format | Old Result | Notes |
|-------------|-----------|-------------------|-----------|-------|
| False | False | '' | EDI (copy only) | Pass-through |
| False | False | 'csv' | EDI | Copy runs, conversion skipped (process_edi gate) |
| True | False | '' | Error/no send | import `convert_to_` fails with ImportError |
| True | False | 'csv' | CSV | Normal conversion |
| False | True | '' | **Tweaked EDI** | Tweaks bypass process_edi |
| False | True | 'csv' | **Tweaked EDI** | Conversion skipped, tweaks run |
| True | True | '' | Error/no send | import fails, tweaks never reached |
| True | True | 'csv' | **CSV then Tweaked EDI** | Both fire |

---

## New Code Runtime Logic

In `dispatch/orchestrator.py:_build_processing_context()`:

```python
if normalize_bool(effective_folder.get("tweak_edi", False)):
    effective_folder["convert_to_format"] = "tweaks"
    effective_folder["process_edi"] = True

has_convert_target = bool(effective_folder.get("convert_to_format"))

# _normalize_edi_flags():
if process_edi_raw is None:
    convert_edi = has_convert_target
else:
    convert_edi = process_edi_bool   # explicit 0 → False, stays disabled

if convert_edi:
    process_edi = True
```

And in `dispatch/pipeline/converter.py`:

```python
# Pre-check 1: no format → skip (return input_path)
if not convert_to_format or convert_to_format == "do_nothing":
    return ConverterResult(output_path=input_path, ...)

# Pre-check 2: process_edi disabled → skip (return input_path)
if not process_edi:
    return ConverterResult(output_path=input_path, ...)

# then validates format, loads module, converts
```

---

## Corrected Behavioral Comparison

| Config | Old Result | Post-migration DB state | New Result | Recipient Impact |
|--------|-----------|------------------------|-----------|-----------------|
| `PE=False, TE=False, TF=''` | EDI | PE=0, TF='' | EDI | **Same** |
| `PE=False, TE=False, TF='csv'` | EDI | PE=0, TF='csv' | EDI | **Same** (process_edi=0 blocks converter) |
| `PE=True, TE=False, TF=''` | Error/no send | PE=1, TF='' | EDI (graceful) | **Better** — new code skips cleanly instead of erroring |
| `PE=True, TE=False, TF='csv'` | CSV | PE=1, TF='csv' | CSV | **Same** |
| `PE=False, TE=True, TF=''` | **Tweaked EDI** | PE=0, TF='' ← BUG | EDI | **BROKEN** — tweaks lost |
| `PE=False, TE=True, TF='csv'` | **Tweaked EDI** | PE=0, TF='csv' ← BUG | EDI | **BROKEN** — tweaks lost, csv not applied |
| `PE=True, TE=True, TF=''` | Error/no send | PE=1, TF='tweaks' | Tweaked EDI | **Better** — was broken before |
| `PE=True, TE=True, TF='csv'` | CSV+Tweaked EDI | PE=1, TF='csv' | CSV | **Changed** — tweaks lost, CSV only |

### Errors in Prior Analysis

The original analysis document contained three incorrect "New Result" claims:

| Row | Claimed | Actual |
|-----|---------|--------|
| `PE=False, TE=False, TF='csv'` | "CSV (auto-correct)" | EDI — `process_edi=0` blocks converter |
| `PE=False, TE=True, TF='csv'` | "CSV (auto-correct)" | EDI — Case C migration keeps PE=0, converter blocked |
| `PE=True, TE=True, TF='csv'` | "Tweaks only (TF→'tweaks')" | CSV — Case A migration keeps stored TF='csv' |

---

## Root Cause of the Migration Bug

The migration's disabled-folder guard (`process_edi=0 → don't promote`) was designed to prevent accidentally enabling folders where the user had intentionally turned off all processing. This was correct for the 270 pure-disabled folders (no tweaks).

However, for the 110 folders with `tweak_edi=1, process_edi='False'`, the user had **not** fully disabled processing — they had enabled tweaks specifically. The old UI was inconsistent in allowing this, but these folders were actively sending tweaked EDI. The correct migration is to treat `tweak_edi=1` as a signal of intent regardless of `process_edi`.

### Fix Required

The v44 migration Cases C/D must be changed: when `tweak_edi=1` and `process_edi=0`, the folder should be promoted to `convert_to_format='tweaks', process_edi=1` (same as Cases A/B), not left disabled.

This affects:
- `migrations/folders_database_migrator.py` — the v44 SQL blocks
- `migrations/folders_database_migrator.py` — the early `_migrate_v33_to_v50()` consolidated block
- Test assertions in `test_folders_database_migrator.py` that expected 380 disabled folders and blocked `process_edi=0 → 1` promotion

---

## Key Files for Reference

| File | Purpose |
|------|---------|
| `dispatch/orchestrator.py:1219-1226` | `_build_processing_context()` — tweak override logic |
| `dispatch/orchestrator.py:1170-1195` | `_normalize_edi_flags()` — convert_edi derivation |
| `dispatch/send_manager.py:274-303` | `get_enabled_backends()` — backend selection |
| `dispatch/pipeline/converter.py:420-456` | `_is_process_edi_disabled()` — early-exit check |
| `migrations/folders_database_migrator.py:47-115` | `_normalize_legacy_v32_values()` — string→int normalization (runs before v44) |
| `migrations/folders_database_migrator.py:375-426` | v44 consolidated block SQL |
| `migrations/folders_database_migrator.py:1594-1680` | v44 individual step SQL |
| `dispatch/converters/convert_to_tweaks.py` | `TweaksConverter` — tweaks as conversion target |
| `tests/fixtures/legacy_v32_folders.db` | Representative production DB (530 folders) |

---

## Summary

**Broken upgrade cases (all 110 tweak_edi folders in production):**

All 110 production folders with `tweak_edi=1` had `process_edi='False'`. In the old code tweaks ran despite `process_edi` being false. The migration incorrectly classified these as "intentionally disabled" and cleared `tweak_edi` without enabling conversion. After upgrade these folders send plain EDI instead of Tweaked EDI.

**Working upgrade cases:**

- Pure pass-through folders (`PE=False, TE=False`) — identical behavior
- Pure conversion folders (`PE=True, TE=False, TF=format`) — identical behavior
- The `PE=True, TF=''` edge case is handled more gracefully (no error, clean skip)

**Fix:** Change the v44 migration to always treat `tweak_edi=1` as intent to process, regardless of `process_edi`. Set `convert_to_format='tweaks', process_edi=1, tweak_edi=0` for all `tweak_edi=1` folders unconditionally.

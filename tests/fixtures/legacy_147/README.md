# Tests

## Vendored 1.47 source (behaviour oracle)

`tests/fixtures/legacy_147/` contains **verbatim copies** of the dispatch and
converter modules from the `1.47_release` git branch, used as a behavioural
oracle for the routing-harness tests (`tests/unit/dispatch/test_legacy_147_routing.py`)
and the master-parity tests (`tests/unit/dispatch/test_master_routing_matches_147.py`).

### Files in this directory

| File                              | Provenance (`git show 1.47_release:<path>`) |
|-----------------------------------|--------------------------------------------|
| `dispatch.py`                     | `dispatch.py`                              |
| `convert_to_csv.py`               | `convert_to_csv.py`                        |
| `convert_to_scannerware.py`       | `convert_to_scannerware.py`                |
| `convert_to_scansheet_type_a.py`  | `convert_to_scansheet_type_a.py`           |
| `convert_to_jolley_custom.py`     | `convert_to_jolley_custom.py`              |
| `convert_to_stewarts_custom.py`   | `convert_to_stewarts_custom.py`            |
| `convert_to_simplified_csv.py`    | `convert_to_simplified_csv.py`             |
| `convert_to_estore_einvoice.py`   | `convert_to_estore_einvoice.py`            |
| `convert_to_estore_einvoice_generic.py` | `convert_to_estore_einvoice_generic.py` |
| `convert_to_yellowdog_csv.py`     | `convert_to_yellowdog_csv.py`              |
| `convert_to_fintech.py`           | `convert_to_fintech.py`                    |
| `edi_tweaks.py`                   | `edi_tweaks.py`                            |

### Hard-dependency stubs (under `stubs/`)

The vendored modules import several siblings that are not vendored because
they pull in heavyweight or external dependencies. The test harness installs
these `stubs/*.py` modules into `sys.modules` *before* importing any vendored
module, so the `import` statements at the top of the vendored files resolve
to the stubs.

| Stub                            | Replaces 1.47 module    | Notes                                       |
|---------------------------------|-------------------------|---------------------------------------------|
| `stubs/utils.py`                | `utils.py`              | Pure-python functions only                  |
| `stubs/query_runner.py`         | `query_runner.py`       | No pyodbc; `run_arbitrary_query` returns `()`|
| `stubs/mtc_edi_validator.py`    | `mtc_edi_validator.py`  | Always reports valid                        |
| `stubs/record_error.py`         | `record_error.py`       | Captures to in-memory list                  |
| `stubs/doingstuffoverlay.py`    | `doingstuffoverlay.py`  | No-op Tk overlay                            |

### Py2 -> Py3 shims

`convert_to_scansheet_type_a.py` does `import ImageOps as pil_ImageOps`,
which is a Python 2 style import that no longer resolves under Python 3.
The harness injects a shim into `sys.modules` before the vendored module is
loaded:

```python
import PIL.ImageOps
sys.modules["ImageOps"] = PIL.ImageOps  # Py2-style alias for PIL.ImageOps
```

This is implemented in `tests/unit/conftest.py`'s
`_install_legacy_147_stubs` autouse fixture.

Other vendored converters that require `barcode`, `openpyxl`, or
`dateutil` (notably `convert_to_scansheet_type_a`, `_jolley_custom`,
`_stewarts_custom`) will fail at import time if those third-party modules
are missing from the venv. The routing tests are written to be tolerant:
they inspect `convert_to_format` before deciding whether to load the
matching vendored converter, and they `pytest.skip` formats that cannot be
imported without third-party deps.

### Refreshing from `1.47_release`

```bash
# Default: refresh from the 1.47_release branch.
tests/fixtures/legacy_147/refresh.sh

# Or, against a different ref (e.g. a tagged release branch):
tests/fixtures/legacy_147/refresh.sh 1.47.3
```

`refresh.sh` is generated to overwrite the vendored files; it does **not**
touch the stubs. The CI guard `tests/fixtures/legacy_147/test_no_drift.py`
runs the same `git show` invocation and fails if the on-disk copy drifts.

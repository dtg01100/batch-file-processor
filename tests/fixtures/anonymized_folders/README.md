# Anonymized folder fixtures

This directory holds one JSON file per **anonymized folder row** exported from
a production customer DB via `scripts/export_anonymized_folders.py`. They are
the input matrix for the 1.47 routing-harness tests
(`tests/unit/dispatch/test_legacy_147_routing.py`) and the master-parity tests
(`tests/unit/dispatch/test_master_routing_matches_147.py`).

## Layout

```
tests/fixtures/anonymized_folders/
├── README.md    <- this file
└── folders/
    ├── 0001_<alias-safename>.json
    ├── 0002_<alias-safename>.json
    └── ...
```

Each JSON file holds one folder row's full `parameters_dict` shape that
1.47's `folders_database.find()` would return.

## Schema (per row)

```json
{
  "id": 1,
  "alias": "012258",
  "folder_name": "/abs/path/to/inbox",
  "convert_to_format": "csv",
  "process_edi": "True",
  "tweak_edi": "False",
  "split_edi": "False",
  "force_edi_validation": "False",
  "rename_file": "",
  "process_backend_copy": "True",
  "process_backend_ftp": "False",
  "process_backend_email": "False",
  "copy_to_directory": "...",
  "ftp_server": "",
  "ftp_folder": "",
  "email_to": ""
}
```

> **NOTE:** Field names in this JSON **must match** the keys that 1.47's
> `dispatch.py` reads off `parameters_dict` directly. Document any
> master-vs-1.47 column drift in the README generated alongside an export.

## Generating fixtures

```bash
DB_PATH=/path/to/anonymized.sqlite .venv/bin/python scripts/export_anonymized_folders.py
```

The export script is **deterministic and idempotent**: rows are sorted by
`id`, JSON keys are sorted (`json.dump(sort_keys=True, indent=2)`). Re-runs
produce no diffs.

## Test behaviour when this directory is empty

The harness fails loudly with
`"no anonymized folder fixtures found; run scripts/export_anonymized_folders.py"`
instead of passing vacuously. See `test_anonymized_fixtures_present` in the
routing tests.

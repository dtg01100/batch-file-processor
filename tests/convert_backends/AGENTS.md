# CONVERT BACKENDS TESTS (Parity & Baselines)

Converter test fixtures, parity verification, baseline comparisons. Deep nesting (depth 4) intentional.

## STRUCTURE

```
convert_backends/
├── baselines/                     # Baseline fixtures per backend
│   ├── csv/                       # CSV converter fixtures
│   ├── scannerware/               # ScannerWare fixtures
│   ├── simplified_csv/            # Simplified CSV fixtures
│   ├── estore_einvoice/           # EstoreEinvoice fixtures
│   ├── edi_tweaks/                # EDI tweaks fixtures
│   ├── csv_metadata.json          # Fixture enumeration
│   ├── scannerware_metadata.json
│   └── ...
├── data/                          # Shared test data, format specs
├── conftest.py                    # Corpus fixtures, markers
├── test_parity_verification.py    # Compare outputs to baselines
├── test_backends_smoke.py         # Converter smoke tests
└── test_*.py                      # Per-backend unit/integration tests
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Parity tests | `test_parity_verification.py` | Compares outputs to stored baselines |
| Baseline fixtures | `baselines/<backend>/` | fintech_edi_*, basic_edi_*, malformed_edi_* |
| Metadata | `baselines/*_metadata.json` | Enumerates fixtures, maps logical names |
| Corpus fixtures | `conftest.py` | Many fixtures skip if corpus missing |
| Smoke tests | `test_backends_smoke.py` | Quick converter validation |

## BASELINE CONVENTIONS

**Fixture naming** (consistent across backends):
- `fintech_edi_<hash>.ext` — Primary fintech sample
- `basic_edi_<hash>.ext` — Simple/basic case
- `complex_edi_<hash>.ext` — Complex invoice case
- `malformed_edi_<hash>.ext` — Intentionally malformed (error handling tests)
- `edge_cases_edi_<hash>.ext` — Edge case inputs
- `empty_edi_<hash>.ext` — Empty file variant

**Hash suffix**: Short hex (e.g., `4a1915e8`) — stable unique filenames for variants

**Metadata JSON**: Maps logical names to actual files
- Example: `csv_metadata.json` lists `{"fintech_edi": "fintech_edi_4a1915e8.csv", ...}`
- Tests load metadata to enumerate fixtures programmatically

## PARITY VERIFICATION

**Pattern**: test_parity_verification.py compares converter outputs to baseline files
- If baseline missing: `pytest.skip("baseline not found")`
- Parametrized tests with `ids=` derived from fixture names
- Regeneration: special test flag to update baselines when intentional changes made

**Baseline locations**: `baselines/<backend>/<fixture>`

## CORPUS FIXTURES

**Pattern** (conftest.py):
```python
if not corpus_file.exists():
    pytest.skip("corpus file not available")
```
- Corpus files (`alledi/`) are NOT committed
- Tests gracefully skip when corpus unavailable
- Markers: `convert_backend`, `parity`

## DEEP NESTING (Intentional)

Baseline fixtures at depth 4: `tests/convert_backends/baselines/<backend>/<files>`
- **Purposeful**: Groups converter-specific test data
- Metadata JSON files centralize fixture discovery
- Do NOT flatten — organization serves clear purpose

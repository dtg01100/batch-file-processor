# performance-regression-monitoring Skill

Workspace-scoped helper skill for identifying and preventing pipeline performance regressions.

## Purpose

- Add a standard benchmarking and assertion process for critical dispatch operations.
- Guard against latency and throughput degradations during code changes.

## When to use

- Upon optimization or refactoring of parser, converter, or backend stacks.
- If there is performance slippage after dependency updates.

## Input

- Target scenario (e.g., 10k invoice conversion, 1k file transfer operations).
- Baseline performance metric thresholds.

## Workflow

1. Establish baseline timer snapshots using existing helper scripts or new tests.
   - Use `time.perf_counter()` in integration tests in `tests/perf/test_dispatch_perf.py`.
2. Implement threshold assertions and optional trending storage.
3. Run benchmarks in CI shot (e.g., `pytest tests/perf -q --timeout=300`) conditionally in nightly.
4. If regression detected, profile with cProfile and diagnose hotspots.
5. Add docs to `docs/TESTING.md` and `docs/ARCHITECTURE.md` specifying target QPS/latency.

## Decision points

- Use deterministic data sizes; random seeds for run-to-run stability.
- Mark as `pytest.mark.slow` to avoid gating fast feedback loop, but run on nightly.

## Output

- Performance benchmark tests and guardrails in CI.

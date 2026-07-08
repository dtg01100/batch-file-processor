"""In-memory stubs that replace the hard dependencies imported by the vendored
1.47 ``dispatch.py`` and ``convert_to_*.py`` modules.

Each module here shadows a 1.47 module name. The harness installs them into
``sys.modules`` *before* the vendored code is imported, so ``import utils`` and
``from query_runner import query_runner`` inside the vendored files resolve to
these in-memory shadows rather than the real production modules.

The signatures of the stubbed callables must match what the vendored code
expects (see ``tests/fixtures/legacy_147/README.md``).
"""

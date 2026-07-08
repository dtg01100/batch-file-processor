"""CI guard: detect drift between vendored 1.47 files and their git source.

Each vendored file in ``tests/fixtures/legacy_147/`` is supposed to be a
verbatim copy of the corresponding file from the ``1.47_release`` branch
(see ``tests/fixtures/legacy_147/README.md``). If this test fails, run
``tests/fixtures/legacy_147/refresh.sh`` to bring the on-disk files back
in sync with the branch.

This test is intentionally independent of the rest of the routing-harness
suite; it imports nothing heavy and runs in well under a second.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
LEGACY_DIR = REPO_ROOT / "tests" / "fixtures" / "legacy_147"
REF = "1.47_release"


VENDORED_FILES = (
    "dispatch.py",
    "edi_tweaks.py",
    "convert_to_csv.py",
    "convert_to_scannerware.py",
    "convert_to_scansheet_type_a.py",
    "convert_to_jolley_custom.py",
    "convert_to_stewarts_custom.py",
    "convert_to_simplified_csv.py",
    "convert_to_estore_einvoice.py",
    "convert_to_estore_einvoice_generic.py",
    "convert_to_yellowdog_csv.py",
    "convert_to_fintech.py",
)


def _git_show(ref: str, path: str) -> str | None:
    result = subprocess.run(
        ["git", "show", f"{ref}:{path}"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def _has_branch(ref: str) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", f"refs/heads/{ref}"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


@pytest.mark.parametrize("filename", VENDORED_FILES)
def test_vendored_file_matches_branch(filename: str) -> None:
    if not _has_branch(REF):
        pytest.skip(f"Branch {REF!r} not available locally")
    on_disk_path = LEGACY_DIR / filename
    if not on_disk_path.exists():
        pytest.fail(f"Vendored file missing: {on_disk_path}")
    expected = _git_show(REF, filename)
    if expected is None:
        pytest.fail(
            f"Could not read {REF}:{filename} from git; "
            "is the 1.47_release branch fetched?"
        )
    actual = on_disk_path.read_text(encoding="utf-8")
    if actual != expected:
        pytest.fail(
            f"{filename} has drifted from {REF}. "
            f"Run tests/fixtures/legacy_147/refresh.sh to refresh."
        )

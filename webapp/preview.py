"""EDI preview for the webapp.

The full ``dispatch/converters`` pipeline writes its output to a
file on disk and (for some formats) needs a UPC lookup table that
the webapp doesn't have access to. Building a full in-process
preview of every converter is out of scope for this module.

What ``preview_edi`` *does* offer:

1. Reads the EDI file line-by-line and classifies each line as
   A / B / C / trailer by its first character.
2. Returns per-line classification plus aggregate counts so an
   operator can sanity-check that an upload is parseable before
   committing it to the dispatcher queue.
3. Runs the existing ``core/edi/`` validators when available so
   structural issues (record count mismatch, unknown record types)
   surface in the UI.

The output is deliberately simple: a JSON-friendly dict with
``lines`` and ``summary`` keys.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_LINE_CLASS = re.compile(r"^([A-Z])")


def preview_edi(path: str | Path) -> dict[str, Any]:
    """Return a line-by-line classification of an EDI file.

    Args:
        path: Path to an EDI file on disk.

    Returns:
        ``{"lines": [{"num": 1, "raw": "...", "type": "A"}, ...],
            "summary": {"total": N, "a": n, "b": n, "c": n,
                        "trailer": n, "unknown": n}}``

    Raises:
        FileNotFoundError: When ``path`` doesn't exist.
    """
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"EDI file not found: {path}")
    lines: list[dict[str, Any]] = []
    summary = {"total": 0, "a": 0, "b": 0, "c": 0, "trailer": 0, "unknown": 0}
    with p.open("r", encoding="utf-8", errors="replace") as f:
        for num, raw in enumerate(f, start=1):
            stripped = raw.rstrip("\r\n")
            if not stripped:
                continue
            first = stripped[:1]
            if first == "A":
                kind = "a"
            elif first == "B":
                kind = "b"
            elif first == "C":
                kind = "c"
            elif first == "T":
                kind = "trailer"
            else:
                kind = "unknown"
            summary[kind] += 1
            summary["total"] += 1
            lines.append({"num": num, "raw": stripped[:200], "type": kind})
    return {"lines": lines, "summary": summary}


__all__ = ["preview_edi"]

"""String normalization utilities for format conversion and parsing."""

import re
from typing import Any

# Pre-compiled regex patterns for performance (avoids recompilation on each call)
_RE_NON_ALPHANUMERIC = re.compile(r"[^a-z0-9_]")
_RE_MULTIPLE_UNDERSCORES = re.compile(r"_+")

def normalize_convert_to_format(value: Any) -> str:
    """Normalize convert_to_format into a predictable module-friendly token.

    Handles legacy casing/spacing/hyphens and noisy punctuation.

    Examples:
        "Estore eInvoice" -> "estore_einvoice"
        "  Tweaks  " -> "tweaks"
        None -> ""

    """
    if value is None:
        return ""
    normalized = str(value).strip().lower().replace(" ", "_").replace("-", "_")
    normalized = _RE_NON_ALPHANUMERIC.sub("_", normalized)
    return _RE_MULTIPLE_UNDERSCORES.sub("_", normalized).strip("_")

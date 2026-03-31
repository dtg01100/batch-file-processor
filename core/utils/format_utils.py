"""String normalization utilities for format conversion and parsing."""

import re
from typing import Any


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
    normalized = re.sub(r"[^a-z0-9_]", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized

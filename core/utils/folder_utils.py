"""Utility functions for folder processing."""

from core.constants import FOLDER_DEFAULTS
from core.utils import normalize_bool, normalize_convert_to_format


def build_effective_folder(folder: dict) -> dict:
    """Build effective folder with defaults applied.

    Normalizes a folder configuration by applying FOLDER_DEFAULTS for any
    missing/NULL fields, normalizing UPC target length, and handling the
    tweak_edi flag. Used by both DispatchOrchestrator and FolderPipelineExecutor
    so they produce identical effective configurations.

    Args:
        folder: Original folder configuration dictionary.

    Returns:
        Normalized folder dict with defaults applied and EDI flags normalized.

    """
    effective_folder = folder.copy()

    for key, default in FOLDER_DEFAULTS.items():
        if effective_folder.get(key) is None:
            effective_folder[key] = default

    if not effective_folder.get("upc_target_length"):
        effective_folder["upc_target_length"] = FOLDER_DEFAULTS["upc_target_length"]

    effective_folder["convert_to_format"] = normalize_convert_to_format(
        effective_folder.get("convert_to_format", "")
    )

    if normalize_bool(effective_folder.get("tweak_edi", False)):
        effective_folder["convert_to_format"] = "tweaks"
        effective_folder["process_edi"] = True

    has_convert_target = bool(effective_folder.get("convert_to_format"))

    process_edi_raw = effective_folder.get("process_edi")
    process_edi_bool = (
        normalize_bool(process_edi_raw) if process_edi_raw is not None else False
    )

    if "convert_edi" not in effective_folder:
        if process_edi_raw is None:
            effective_folder["convert_edi"] = has_convert_target
        else:
            effective_folder["convert_edi"] = process_edi_bool

    if effective_folder.get("convert_edi", False):
        effective_folder["process_edi"] = True

    if "process_edi" not in effective_folder and (
        effective_folder.get("split_edi", False)
        or effective_folder.get("convert_edi", False)
    ):
        effective_folder["process_edi"] = True

    return effective_folder

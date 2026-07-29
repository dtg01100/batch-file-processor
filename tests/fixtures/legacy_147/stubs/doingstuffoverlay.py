"""Stub for 1.47 ``doingstuffoverlay.py``.

Tk-based overlay that we never instantiate. The vendored dispatch.py only
calls ``update_overlay``/``make_overlay``/``destroy_overlay`` — and only when
``args.automatic`` is False; the harness forces ``automatic=True`` so the
overlay branch is skipped. We still install these as no-ops so that any
unexpected import resolves cleanly.
"""


def make_overlay(*args, **kwargs):
    return None


def update_overlay(*args, **kwargs):
    return None


def destroy_overlay(*args, **kwargs):
    return None


class DoingStuffOverlay:
    def __init__(self, parent):
        self.parent = parent


__all__ = ["DoingStuffOverlay", "destroy_overlay", "make_overlay", "update_overlay"]

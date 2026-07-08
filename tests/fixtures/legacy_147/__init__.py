"""Vendored 1.47 source code for behaviour-oracle tests.

All ``*.py`` files in this directory are verbatim copies of the corresponding
files in the ``1.47_release`` git branch. Do not edit them by hand; refresh via
``refresh.sh`` (or ``make refresh-legacy-147`` once wired in).

Stubs for the hard dependencies ``utils``, ``query_runner``, ``mtc_edi_validator``,
``edi_tweaks``, ``record_error``, and ``doingstuffoverlay`` live under ``stubs/``
and are inserted into ``sys.modules`` by the test harness before any vendored
module is loaded.
"""

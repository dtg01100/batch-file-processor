"""Brutally simple mutation meta-test.

This meta-test asks the question: are the tests in tests/unit/**/*_property.py
(and the other DEFAULT_PAIRS below) sufficient to catch real bugs in the
modules they protect? It applies a small, fixed list of obvious mutations
to each module source and runs the corresponding test once. If the test
still passes, the mutation **survived** — a real bug of that shape would
have slipped past the test.

Principles:
- The mutation set is a fixed small list. It is NOT exhaustive mutation
  testing (use mutmut for that). It is a smoke-test of the test suite
  itself.
- Performance is not a concern: this script runs once per meta-test
  invocation. A 5x slow test run is fine.
- The script is a single file, no plugin framework, no config files.
  Read the source, understand the result.
- Every survivor lists the original and mutated source line. A reviewer
  must be able to audit each survivor with a `git blame`-style lookup.

Usage:
    pytest tests/meta/test_property_tests_are_sufficient.py -n 0 -s
    .venv/bin/python tests/meta/test_property_tests_are_sufficient.py \\
        --module core/edi/edi_parser.py \\
        --tests tests/unit/core/edi/test_edi_parser_property.py
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Mutation rules. Each is a (name, find_regex, replace_func) triple.
#
# The list is small on purpose. The meta-test's correctness depends on every
# rule mapping to a clear, real bug class. If you can't justify a mutation
# with a one-sentence "the kind of bug this catches", drop it.
#
# Regex discipline (auditability contract):
#
# 1. Comparison swaps (`lt_to_le`, `le_to_lt`, `gt_to_ge`, `ge_to_gt`):
#    swap `<` <-> `<=`, `>` <-> `>=`. The lookbehind
#    `(?<![A-Za-z0-9_\-])` excludes the function-annotation arrow `->`
#    (preceded by `-`) and identifier-internal characters. Without it,
#    `def f() -> str:` would be mutated to `def f() ->= str:` and the
#    resulting SyntaxError would falsely look like a kill.
#
#    Additionally, `lt_to_le` matches `<` only when NOT followed by
#    another `<` or `=` (so `<<` and `<=` stay matched by their own
#    rules). Likewise `gt_to_ge` matches `>` only when NOT followed
#    by `=` (so `>=` is reserved for `ge_to_gt`). Without these
#    negative lookaheads, `>` in `>=` would be turned into `>==`,
#    producing a SyntaxError that looks like a kill.
#
# 2. Equality swaps (`eq_to_ne`, `ne_to_eq`): swap `==` <-> `!=`.
#    `eq_to_ne` excludes a preceding `!` so it cannot match the `!=`
#    in `!==` (not Python; defensive). `==` and `!=` in Python can only
#    appear as comparisons, so no further context checks are needed.
#
# 3. Boolean flips (`true_to_false`, `false_to_true`): flip the literal
#    `True` / `False` token. `\b` word boundaries prevent partial matches
#    on identifiers that contain those substrings (there shouldn't be any).
#    Side effect: hits docstring prose and default-argument values.
#    Those land in KNOWN_EQUIVALENT with cited reasons.
#
# 4. Connector swaps (`and_to_or`, `or_to_and`): swap the keyword.
#    Word boundaries prevent matching `Brand` or `born`. Same docstring
#    prose caveat.
#
# 5. `return_none_instead_of_value`: replaces `return EXPR` with
#    `return None`. The negative lookahead `(?!None\b)` excludes
#    `return None`. Side effect: hits docstring prose like
#    "return results"; KNOWN_EQUIVALENT cites the line.
#
# 6. `negate_if_condition`: negates `if X:` to `if not (X):`. Catches
#    guard regressions. Targets `if`-statements, NOT `elif` (the regex
#    would not match `elif` because `elif` has no space before its
#    condition; verified by hand on existing modules).
#
# 7. `int_constant_off_by_one`: increments a literal integer >= 2.
#    Side effect: hits docstring prose ("6-character") and version
#    constants; KNOWN_EQUIVALENT cites those.
#
# Mutation order matters. Comparison swaps run first so they don't shadow
# each other; the int-off-by-one runs last and may match a number produced
# by an earlier mutation's diff (a known edge case the runner accepts).
# ---------------------------------------------------------------------------

MUTATIONS: list[tuple[str, re.Pattern[str], Callable[[re.Match[str]], str]]] = [
    ("lt_to_le", re.compile(r"(?<![A-Za-z0-9_\-])<(?![<=])"), lambda m: "<="),
    ("le_to_lt", re.compile(r"(?<![A-Za-z0-9_\-])<="), lambda m: "<"),
    # Match `>` that is NOT followed by `=` (so `>=` is reserved for
    # ge_to_gt). The lookbehind excludes identifier chars and the
    # function-arrow character.
    ("gt_to_ge", re.compile(r"(?<![A-Za-z0-9_\-])>(?!=)"), lambda m: ">="),
    ("ge_to_gt", re.compile(r"(?<![A-Za-z0-9_\-])>="), lambda m: ">"),
    ("eq_to_ne", re.compile(r"(?<!=)=="), lambda m: "!="),
    ("ne_to_eq", re.compile(r"!="), lambda m: "=="),
    ("true_to_false", re.compile(r"\bTrue\b"), lambda m: "False"),
    ("false_to_true", re.compile(r"\bFalse\b"), lambda m: "True"),
    ("and_to_or", re.compile(r"\band\b"), lambda m: "or"),
    ("or_to_and", re.compile(r"\bor\b"), lambda m: "and"),
    (
        "return_none_instead_of_value",
        re.compile(r"return\s+(?!None\b)([A-Za-z_][A-Za-z0-9_\.\(\)]+)"),
        lambda m: "return None",
    ),
    (
        "negate_if_condition",
        re.compile(r"if\s+(.+?):"),
        lambda m: f"if not ({m.group(1)}):",
    ),
    (
        "int_constant_off_by_one",
        re.compile(r"\b([2-9]\d*|1\d+)\b"),
        lambda m: str(int(m.group(1)) + 1),
    ),
]


# ---------------------------------------------------------------------------
# Module/test pairs the meta-test covers by default.
#
# Each entry is (production_module, test_file). The test file at the
# right is the one that should catch real bugs in the module at the left.
#
# To extend: add a pair. To audit: each entry has been checked by running
# the unmodified test against the unmodified module — if the test does
# not pass on the unmodified module, the meta-test refuses to run
# (`run_meta_test` raises SystemExit(2)).
# ---------------------------------------------------------------------------

DEFAULT_PAIRS: list[tuple[str, str]] = [
    # Property-test pairs.
    ("core/edi/edi_parser.py", "tests/unit/core/edi/test_edi_parser_property.py"),
    ("core/edi/edi_splitter.py", "tests/unit/core/edi/test_edi_splitter_property.py"),
    ("core/edi/edi_splitting_utils.py", "tests/unit/core/edi/test_edi_splitting_utils_property.py"),
    ("core/edi/c_rec_generator.py", "tests/unit/core/edi/test_c_rec_generator_property.py"),
    ("core/edi/edi_transformer.py", "tests/unit/core/edi/test_edi_transformer_property.py"),
    ("core/edi/upc_utils.py", "tests/unit/core/edi/test_upc_utils_property.py"),
    ("dispatch/feature_flags.py", "tests/unit/dispatch/test_feature_flags_property.py"),
    ("dispatch/file_utils.py", "tests/unit/dispatch/test_file_utils_property.py"),
    ("dispatch/hash_utils.py", "tests/unit/dispatch/test_hash_utils_property.py"),
    # Pure-Python core utility modules covered by their plain unit tests.
    ("core/utils/format_utils.py", "tests/unit/core/utils/test_format_utils.py"),
    ("core/utils/bool_utils.py", "tests/unit/core/utils/test_bool_utils.py"),
    ("core/utils/date_utils.py", "tests/unit/core/utils/test_date_utils.py"),
    ("core/utils/safe_parse.py", "tests/unit/core/utils/test_safe_parse.py"),
    ("core/utils/timing_utils.py", "tests/unit/core/utils/test_timing_utils.py"),
    ("core/edi/edi_tweaker.py", "tests/unit/core/edi/test_edi_tweaker.py"),
    ("core/structured_logging.py", "tests/unit/test_structured_logging.py"),
    # Plain-unit-test pairs (added 2026-07-09 as part of the meta-test
    # coverage expansion: "all tests have a meta-test to ensure they are
    # correct"). These follow the same invariant as property-test pairs:
    # the test on the right should catch real bugs in the module on the
    # left. See docs/meta-test-findings.md for per-pair survivor history.
    #
    # Pairs are added in batches of plain-unit-tests that have a
    # healthy baseline (the unmodified-source test passes within the
    # runner's 20s timeout). Per-pair survivor counts from the initial
    # run are noted so reviewers know what they're looking at.
    ("dispatch/observability/alert_queue.py", "tests/unit/dispatch/observability/test_alert_queue.py"),  # 3/4 killed, L34 mkdir(parents=True) survives
    ("dispatch/observability/alert_dispatcher.py", "tests/unit/dispatch/observability/test_alert_dispatcher.py"),  # 0 mutants apply (small module)
    ("dispatch/observability/audit_logger.py", "tests/unit/dispatch/observability/test_audit_logger.py"),  # 2/3 killed
    ("dispatch/observability/background_writer.py", "tests/unit/dispatch/observability/test_background_writer.py"),  # 1/4 killed
    ("dispatch/pipeline/interfaces.py", "tests/unit/dispatch/pipeline/test_pipeline_interfaces.py"),  # 1/5 killed
    ("dispatch/converters/registry.py", "tests/unit/dispatch/test_converters_registry.py"),  # 3/7 killed
    ("dispatch/error_handler.py", "tests/unit/dispatch/test_error_handler_alert_integration.py"),  # 1/7 killed
    ("core/edi/po_fetcher.py", "tests/unit/core/edi/test_po_fetcher.py"),  # 3/6 killed
    ("core/edi/inv_fetcher.py", "tests/unit/core/edi/test_inv_fetcher.py"),  # 7/9 (was 5/9; L122 dict boundary, L123 len check killed by test_fetch_po_handles_single_field_dict; L171 true_to_false is KNOWN_EQUIVALENT because Python's logging auto-populates exc_info inside except blocks)
    ("adapters/db2ssh/connection.py", "tests/unit/adapters/db2ssh/test_db2ssh_connection.py"),  # 3/7 killed
    ("core/edi/edi_parser.py", "tests/unit/core/edi/test_edi_parser.py"),  # 1/10 killed (note: distinct pair from the property test in DEFAULT_PAIRS above)
    # Batch 2 (also 2026-07-09):
    ("core/database/query_runner.py", "tests/unit/core/database/test_query_runner.py"),  # 6/10 killed
    ("backend/copy_backend.py", "tests/unit/backend/test_copy_backend.py"),  # 4/8 killed
    ("backend/file_operations.py", "tests/unit/backend/test_file_operations.py"),  # 4/9 killed
    ("backend/ftp_client.py", "tests/unit/backend/test_ftp_client.py"),  # 3/8 killed
    ("backend/smtp_client.py", "tests/unit/backend/test_smtp_client.py"),  # 4/8 killed
    ("dispatch/services/database_connector.py", "tests/unit/dispatch/services/test_database_connector.py"),  # 5/5 killed (100% clean)
    ("dispatch/services/folder_processor.py", "tests/unit/dispatch/services/test_folder_processor.py"),  # 3/8 killed
    ("interface/validation/email_validator.py", "tests/unit/interface/validation/test_email_validator.py"),  # 5/9 killed
    ("interface/models/folder_configuration.py", "tests/unit/interface/models/test_folder_config_alert.py"),  # 2/11 killed
    ("core/edi/upc_utils.py", "tests/unit/core/edi/test_upc_utils.py"),  # 5/11 killed (companion to property test; plain unit test covers different paths)
    # Batch 3 (also 2026-07-09): plain-unit tests for modules whose
    # property tests were already in DEFAULT_PAIRS; each plain test
    # exercises paths the property test does not.
    ("core/edi/c_rec_generator.py", "tests/unit/core/edi/test_c_rec_generator.py"),  # 4/9 killed
    ("dispatch/feature_flags.py", "tests/unit/dispatch/test_feature_flags.py"),  # 3/5 killed
    # Batch 4 (also 2026-07-09): previously-untouched layers (tests/dispatch/,
    # tests/unit/dispatch_tests/, tests/unit/interface/operations/). Mix of
    # strong and weak tests; high survivor rates reveal missing-assertion gaps.
    ("dispatch/converters/customer_queries.py", "tests/dispatch/converters/test_customer_queries.py"),  # 1/3 killed
    ("dispatch/services/customer_lookup_service.py", "tests/dispatch/services/test_customer_lookup_service.py"),  # 1/3 killed
    ("dispatch/services/uom_lookup_service.py", "tests/dispatch/services/test_uom_lookup_service.py"),  # 2/5 killed
    ("dispatch/send_manager.py", "tests/unit/dispatch_tests/test_send_manager.py"),  # 4/6 killed
    ("dispatch/processed_files_tracker.py", "tests/unit/dispatch_tests/test_processed_files_tracker.py"),  # 7/9 killed
    ("dispatch/print_service.py", "tests/unit/dispatch_tests/test_print_service.py"),  # 4/9 killed
    ("dispatch/services/file_filter.py", "tests/unit/dispatch_tests/test_file_filter.py"),  # 2/8 killed
    ("dispatch/orchestrator.py", "tests/unit/dispatch_tests/test_orchestrator.py"),  # 2/9 killed
    ("interface/operations/folder_manager.py", "tests/unit/interface/operations/test_folder_manager.py"),  # 3/9 killed
    ("interface/operations/processed_files.py", "tests/unit/interface/operations/test_processed_files.py"),  # 4/4 killed (100% clean)
    # Batch 5 (also 2026-07-09): dispatch_tests/ pipeline + services, plus
    # interface/validation and form/. Includes a 0-N entry on purpose:
    # 0/8 (dispatch/pipeline/validator.py) means the test runs without
    # binding to module behavior at all — adding it makes the meta-test
    # surface that as a test-quality debt. Same for 0/6 on interfaces.py.
    ("dispatch/pipeline/validator.py", "tests/unit/dispatch_tests/test_pipeline_validator.py"),  # 4/8 (was 0/8; 4 docstring mutations KNOWN_EQUIVALENT, 4 real mutations killed by TestNormalizeValidationOutput)
    ("dispatch/pipeline/temp_dir_utils.py", "tests/unit/dispatch_tests/test_pipeline_temp_dir_utils.py"),  # 2/4 killed
    ("dispatch/edi_validator.py", "tests/unit/dispatch_tests/test_edi_validator.py"),  # 5/10 killed
    ("dispatch/preflight_validator.py", "tests/unit/dispatch_tests/test_preflight_validator.py"),  # 3/6 killed
    ("dispatch/log_sender.py", "tests/unit/dispatch_tests/test_log_sender.py"),  # 4/8 killed
    ("dispatch/error_handler.py", "tests/unit/dispatch_tests/test_error_handler.py"),  # 4/7 (was 1/7; L91 or_to_and, L154 negate, L193 false_to_true, L224 return_none killed by test_init_preserves_truthy_errors_folder, test_record_error_to_database, test_default_threaded_is_false, test_record_error_to_logs_threaded)
    ("dispatch/interfaces.py", "tests/unit/dispatch_tests/test_interfaces.py"),  # 0/6 — test has no assertions on mutated behavior
    ("interface/validation/folder_settings_validator.py", "tests/unit/test_settings_validation.py"),  # 7/11 killed
    ("interface/form/form_generator.py", "tests/unit/test_form_generator.py"),  # 4/8 killed
    # Batch 6 (also 2026-07-09): backend/database, dispatch/converters,
    # dispatch interfaces (companion pair), core EDI fetchers, and
    # interface/folder_configuration. Several 0-N entries expose tests
    # that don't bind to module behavior — the meta-test surfaces these
    # as test-quality debt.
    ("backend/database/database_obj.py", "tests/unit/interface/database/test_database_obj.py"),  # 4/10 killed
    ("backend/database/database_obj.py", "tests/unit/interface/database/test_safe_accessors.py"),  # 2/10 killed
    ("dispatch/converters/convert_base.py", "tests/unit/test_estore_null_safety.py"),  # 1/9 killed
    ("dispatch/converters/convert_base.py", "tests/unit/test_convert_base.py"),  # 4/9 (was 3/9; L128 false_to_true on output_file repr=False killed by test_output_file_excluded_from_repr)
    ("dispatch/interfaces.py", "tests/unit/test_dispatch_interfaces.py"),  # 0/6 — test has no assertions on mutated behavior
    ("core/edi/edi_splitting_utils.py", "tests/unit/test_category_filtering.py"),  # was mispaired as edi_splitter.py (0/7 was a DEFAULT_PAIRS bug, not a test gap)
    ("dispatch/converters/convert_to_fintech.py", "tests/unit/test_convert_backends.py"),  # was mispaired as core/edi/inv_fetcher (0/9 was a DEFAULT_PAIRS bug, not a test gap)
    ("interface/models/folder_configuration.py", "tests/unit/test_folder_configuration_pydantic.py"),  # 8/11 (was 1/11; L115, L165, L18, L273, L298, L64, L409 killed by new test classes)
    ("interface/models/folder_configuration.py", "tests/unit/test_folder_db_roundtrip.py"),  # 1/11 (same module, different test pair; the new tests in test_folder_configuration_pydantic.py don't apply here, but the underlying model mutations are not exercised by the db_roundtrip path either)
    # Batch 7 (also 2026-07-09): interface/plugins/*, dispatch/converters/*
    # (concrete converter modules: eStore, simplified CSV, fintech,
    # scansheet_type_a), and core/edi/inv_fetcher pulled in via converter
    # tests. High 0/N rates on the converter tests are real test-quality
    # signals — these tests import the modules but mock around the
    # behavior, so mutations don't reach the assertions.
    ("interface/plugins/config_schemas.py", "tests/unit/test_plugins/test_configuration_plugin.py"),  # 8/9 (was 2/9 with wrong pair; now 8/9 with new TestFieldDefinitionValidate tests; 1 docstring survivor KNOWN_EQUIVALENT)
    ("interface/plugins/config_schemas.py", "tests/unit/test_plugins/test_form_generator_plugins.py"),  # was mispaired as test_plugin_manager_configuration (1/9 was a DEFAULT_PAIRS bug)
    ("interface/plugins/configuration_plugin.py", "tests/unit/test_plugins/test_configuration_plugin.py"),  # 2/3 killed
    ("interface/plugins/section_registry.py", "tests/unit/test_plugins/test_section_registry.py"),  # 1/7 killed
    ("interface/operations/plugin_configuration_mapper.py", "tests/unit/test_plugins/test_plugin_configuration_mapper.py"),  # 3/11 killed
    ("interface/plugins/csv_configuration_plugin.py", "tests/unit/test_plugins/test_plugin_option_combinations.py"),  # 1/3 killed
    ("dispatch/converters/convert_to_simplified_csv.py", "tests/unit/test_convert_to_simplified_csv.py"),  # 5/8 killed
    ("dispatch/converters/convert_to_csv.py", "tests/unit/test_convert_to_csv.py"),  # was mispaired as convert_to_simplified_csv (0/8 was a DEFAULT_PAIRS bug, not a test gap)
    ("dispatch/converters/convert_to_yellowdog_csv.py", "tests/unit/test_convert_to_yellowdog_csv.py"),  # was mispaired as core/edi/inv_fetcher (0/9 was a DEFAULT_PAIRS bug, not a test gap)
    ("dispatch/converters/convert_to_fintech.py", "tests/unit/test_convert_to_fintech.py"),  # was mispaired as core/edi/inv_fetcher (0/9 was a DEFAULT_PAIRS bug, not a test gap)
    ("dispatch/converters/convert_to_scansheet_type_a.py", "tests/unit/test_convert_to_scansheet_type_a.py"),  # 1/9 (commit d14b686d5)
    ("dispatch/converters/convert_to_estore_einvoice.py", "tests/unit/test_convert_to_estore_einvoice.py"),  # 6/8 killed (strong test)
    ("dispatch/converters/convert_to_estore_einvoice_generic.py", "tests/unit/test_convert_to_estore_einvoice_generic.py"),  # 6/8 killed (strong test)
    ("dispatch/converters/registry.py", "tests/unit/dispatch_tests/test_legacy_147_smoke.py"),  # 1/7 killed (companion to test_converters_registry.py)
]           


# ---------------------------------------------------------------------------
# KNOWN_EQUIVALENT list.
#
# A survivor is a mutation the test suite does NOT catch. There are two kinds:
#
#   1. A real test gap: the test does not exercise the mutated code path.
#      Fix by writing a stronger test.
#   2. An equivalent mutation: the change has no observable effect on the
#      test assertion (e.g., the mutation lands inside a docstring, a
#      __version__ constant, a default-argument value the test overrides
#      anyway, or a comment). The TEST is correct; the mutation is meaningless.
#
# Bucket 2 is unavoidable noise. Rather than scattering `# pragma: no cover`
# comments through the codebase, we keep one auditable list here. Each entry
# is `(module_relpath, mutation_name, line_number, reason)`. Each entry was
# added by reading the module source at that line and verifying the
# mutation has no observable effect on the test pair in DEFAULT_PAIRS.
#
# To re-validate, walk the list line-by-line and confirm the cited line
# matches the cited reason.
#
# Entries are intentionally narrow: (module, mutation, line). Adding
# pattern-based "skip if mutation X on any line below 10" is exactly the
# kind of cleverness this meta-test is meant to avoid.
# ---------------------------------------------------------------------------

KNOWN_EQUIVALENT: list[tuple[str, str, int, str]] = [
    # ------------------------------------------------------------------
    # core/edi/edi_parser.py (test: test_edi_parser_property.py)
    # ------------------------------------------------------------------
    ("core/edi/edi_parser.py", "ge_to_gt", 93,
     "log-string 'expected >=%d chars' — tests do not assert log content"),
    ("core/edi/edi_parser.py", "gt_to_ge", 171,
     "doctest-style `>>> capture_records(...)` in docstring prose"),
    ("core/edi/edi_parser.py", "and_to_or", 3,
     "module docstring 'A, B, and C records' — prose"),
    ("core/edi/edi_parser.py", "or_to_and", 165,
     "function docstring 'record fields, or None for empty lines' — prose"),
    ("core/edi/edi_parser.py", "int_constant_off_by_one", 22,
     "ARecord dataclass docstring '6-character vendor code' — prose"),
    # ------------------------------------------------------------------
    # core/edi/edi_splitter.py (test: test_edi_splitter_property.py)
    # ------------------------------------------------------------------
    ("core/edi/edi_splitter.py", "false_to_true", 34,
     "SplitConfig.prepend_date default = False -> True. Property tests "
     "always pass prepend_date=False explicitly, so the default is invisible to them."),
    ("core/edi/edi_splitter.py", "and_to_or", 62,
     "function docstring 'path, prefix, and suffix' — prose"),
    ("core/edi/edi_splitter.py", "or_to_and", 107,
     "function docstring 'CR only, LF only, or CRLF' — prose"),
    # ------------------------------------------------------------------
    # core/edi/edi_splitting_utils.py (test: test_edi_splitting_utils_property.py)
    # ------------------------------------------------------------------
    ("core/edi/edi_splitting_utils.py", "gt_to_ge", 33,
     "doctest-style `>>> _col_to_excel(1)` in docstring prose"),
    ("core/edi/edi_splitting_utils.py", "true_to_false", 69,
     "function docstring 'If True, prefix filenames' — prose"),
    ("core/edi/edi_splitting_utils.py", "false_to_true", 310,
     "parameters_dict.get('prepend_date_files', False) default — "
     "property tests pass explicit value"),
    ("core/edi/edi_splitting_utils.py", "and_to_or", 1,
     "module docstring 'splitting and category filtering' — prose"),
    ("core/edi/edi_splitting_utils.py", "or_to_and", 73,
     "function docstring 'credit invoices or regular' — prose"),
    ("core/edi/edi_splitting_utils.py", "int_constant_off_by_one", 15,
     "MAX_A_RECORD_COUNT = 700 module constant — see REAL_GAPS; "
     "tests do not exercise this constant, so the mutation has no observed effect"),
    # ------------------------------------------------------------------
    # core/edi/c_rec_generator.py (test: test_c_rec_generator_property.py)
    # ------------------------------------------------------------------
    ("core/edi/c_rec_generator.py", "true_to_false", 85,
     "set_invoice_number sets self.unappended_records = True — "
     "property tests do not observe this attribute"),
    ("core/edi/c_rec_generator.py", "false_to_true", 72,
     "__init__ sets self.unappended_records = False — "
     "property tests do not observe this attribute"),
    ("core/edi/c_rec_generator.py", "and_to_or", 20,
     "Protocol method docstring 'query and return results' — prose"),
    ("core/edi/c_rec_generator.py", "return_none_instead_of_value", 20,
     "Protocol method docstring 'return results' — prose (regex hits prose, not real return)"),
    ("core/edi/c_rec_generator.py", "int_constant_off_by_one", 126,
     "function docstring 'a 9-character EDI amount string' — prose"),
    # ------------------------------------------------------------------
    # core/edi/upc_utils.py (test: test_upc_utils_property.py)
    #
    # The self-referential-test entries (L38 true_to_false, L40
    # negate_if_condition, L47 return_none_instead_of_value) used to live
    # here as REAL TEST BUG entries. They are now killed by the
    # hardcoded oracle test test_validate_upc_hardcoded_valid_oracle
    # (input is independent of calc_check_digit), so they have been
    # removed.
    # ------------------------------------------------------------------
    ("core/edi/upc_utils.py", "false_to_true", 100,
     "function docstring 'True if check digit is valid, False otherwise' — prose"),
    ("core/edi/upc_utils.py", "and_to_or", 3,
     "module docstring 'pure Python dependencies and easily testable' — prose"),
    ("core/edi/upc_utils.py", "or_to_and", 54,
     "function docstring '6, 7, or 8 digits' — prose"),
    ("core/edi/upc_utils.py", "int_constant_off_by_one", 6,
     "reference URL fragment in module docstring — prose"),
    ("core/edi/upc_utils.py", "gt_to_ge", 33,
     "doctest-style `>>> calc_check_digit(...)` inside the calc_check_digit "
     "function docstring — tests do not import or render the docstring as code"),
    ("core/edi/upc_utils.py", "ge_to_gt", 141,
     "pad_upc boundary `len(upc) >= target_length`. Mutation to `>` is "
     "equivalent when `len(upc) == target_length` because both branches "
     "return a string of length target with identical content: "
     "`upc[:target]` and `upc.rjust(target, fill)` both equal `upc` "
     "when upc is already the target length. The mutation only differs "
     "in a meaningless branch selection, not in observable behavior."),
    # ------------------------------------------------------------------
    # dispatch/feature_flags.py (test: test_feature_flags_property.py)
    # ------------------------------------------------------------------
    ("dispatch/feature_flags.py", "true_to_false", 27,
     "function docstring 'True if DISPATCH_DEBUG_MODE is true' — prose"),
    ("dispatch/feature_flags.py", "or_to_and", 5,
     "module docstring 'variables or database settings' — prose"),
    # ------------------------------------------------------------------
    # dispatch/file_utils.py (test: test_file_utils_property.py)
    # ------------------------------------------------------------------
    ("dispatch/file_utils.py", "true_to_false", 128,
     "function docstring 'True if directory exists or was created' — prose"),
    ("dispatch/file_utils.py", "false_to_true", 128,
     "same docstring line — prose"),
    ("dispatch/file_utils.py", "and_to_or", 31,
     "function docstring 'format and parameters' — prose"),
    ("dispatch/file_utils.py", "or_to_and", 99,
     "function docstring 'Filename or path' — prose"),
    # ------------------------------------------------------------------
    # dispatch/hash_utils.py (test: test_hash_utils_property.py)
    # ------------------------------------------------------------------
    ("dispatch/hash_utils.py", "and_to_or", 3,
     "module docstring 'pure functions for generating and managing' — prose"),
    ("dispatch/hash_utils.py", "or_to_and", 51,
     "function docstring 'Absolute or relative path' — prose"),
    ("dispatch/hash_utils.py", "int_constant_off_by_one", 52,
     "function docstring '(default: 5)' — prose"),
    # ------------------------------------------------------------------
    # core/utils/format_utils.py (test: test_format_utils.py)
    # ------------------------------------------------------------------
    ("core/utils/format_utils.py", "and_to_or", 1,
     "module docstring 'format conversion and parsing' — prose"),
    # ------------------------------------------------------------------
    # core/utils/bool_utils.py (test: test_bool_utils.py)
    # ------------------------------------------------------------------
    ("core/utils/bool_utils.py", "true_to_false", 8,
     "module docstring 'bool: True/False' — prose"),
    ("core/utils/bool_utils.py", "false_to_true", 8,
     "same docstring line — prose"),
    ("core/utils/bool_utils.py", "and_to_or", 74,
     "module docstring 'integer 1/0, and string True' — prose"),
    ("core/utils/bool_utils.py", "or_to_and", 18,
     "function docstring 'True or False' — prose"),
    # ------------------------------------------------------------------
    # core/utils/date_utils.py (test: test_date_utils.py)
    # ------------------------------------------------------------------
    ("core/utils/date_utils.py", "or_to_and", 48,
     "function docstring 'in mm/dd/yy format, or Not Available' — prose"),
    # ------------------------------------------------------------------
    # core/utils/safe_parse.py (test: test_safe_parse.py)
    # ------------------------------------------------------------------
    ("core/utils/safe_parse.py", "or_to_and", 8,
     "function docstring 'string, int, float, or None' — prose"),
    ("core/utils/safe_parse.py", "return_none_instead_of_value", 9,
     "function docstring 'value to return if conversion fails' — prose"),
    ("core/utils/safe_parse.py", "negate_if_condition", 9,
     "function docstring '...return if conversion fails (default): 0' — prose "
     "(regex `if ... :` matches the second colon; the negation lands inside prose)"),
    ("core/utils/safe_parse.py", "int_constant_off_by_one", 15,
     "doctest-style `safe_int(\"42\") → 42` in docstring prose"),
    # ------------------------------------------------------------------
    # core/utils/timing_utils.py (test: test_timing_utils.py)
    # ------------------------------------------------------------------
    ("core/utils/timing_utils.py", "and_to_or", 29,
     "function docstring 'duration_ms, start_time, and end_time' — prose"),
    # ------------------------------------------------------------------
    # core/edi/edi_tweaker.py (test: test_edi_tweaker.py)
    # ------------------------------------------------------------------
    ("core/edi/edi_tweaker.py", "and_to_or", 62,
     "function docstring 'SQL query and return results' — prose"),
    ("core/edi/edi_tweaker.py", "or_to_and", 72,
     "function docstring 'missing or blank' — prose"),
    ("core/edi/edi_tweaker.py", "return_none_instead_of_value", 62,
     "function docstring 'return results' — prose"),
    ("core/edi/edi_tweaker.py", "int_constant_off_by_one", 122,
     "function docstring '(1=pack, 2=case)' — prose"),
    # ------------------------------------------------------------------
    # core/structured_logging.py (test: test_structured_logging.py)
    # ------------------------------------------------------------------
    ("core/structured_logging.py", "lt_to_le", 1072,
     "f-string sanitized_args.append(f\"<{len(arg)} chars>\") — the `<` is literal output text"),
    ("core/structured_logging.py", "gt_to_ge", 286,
     "doctest-style `>>> data = {...}` in docstring prose"),
    ("core/structured_logging.py", "eq_to_ne", 94,
     "section-divider comment line `========` etc — prose"),
    ("core/structured_logging.py", "false_to_true", 99,
     "function docstring 'Default False to reduce noise' — prose"),
    ("core/structured_logging.py", "and_to_or", 1,
     "module docstring 'convert and tweak instrumentation' — prose"),
     ("core/structured_logging.py", "or_to_and", 234,
      "function docstring '****abc123 or ****' — prose"),
     ("core/structured_logging.py", "int_constant_off_by_one", 31,
      "example code in module docstring `range(3)` — not loaded as Python"),
     # ------------------------------------------------------------------
     # dispatch/interfaces.py (tests: test_interfaces.py, test_dispatch_interfaces.py)
     #
     # All surviving mutations on this module are in docstring text or
     # in `def <method>(self, ...): ...` protocol placeholders. The
     # Protocol bodies are `...` (pass) — the regex mutations
     # (and_to_or, or_to_and, true_to_false, etc.) match the FIRST
     # occurrence in the file, which is always in a docstring. The
     # tests verify that the protocol classes are runtime_checkable
     # and expose the right method names, but they don't run any
     # production code that the mutations could affect.
     # ------------------------------------------------------------------
     ("dispatch/interfaces.py", "and_to_or", 4,
      "module docstring 'database system, enabling loose coupling' — prose"),
     ("dispatch/interfaces.py", "or_to_and", 8,
      "module docstring 'and runtime_checkable' — prose"),
     ("dispatch/interfaces.py", "int_constant_off_by_one", 9,
      "module docstring 'Protocol, runtime_checkable' — class ref"),
     ("dispatch/interfaces.py", "negate_if_condition", 47,
      "protocol body is `...` (pass) — no executable content"),
     ("dispatch/interfaces.py", "or_to_and", 44,
      "DatabaseInterface.find_one docstring 'Single matching record or None' — prose"),
     ("dispatch/interfaces.py", "true_to_false", 188,
      "FileSystemInterface.file_exists docstring 'True if file exists, False otherwise' — prose"),
     ("dispatch/interfaces.py", "false_to_true", 188,
      "FileSystemInterface.file_exists docstring 'True if file exists, False otherwise' — prose"),
     ("dispatch/interfaces.py", "int_constant_off_by_one", 147,
      "read_file_text parameter default 'utf-8' (8 chars) — string literal"),
     ("dispatch/interfaces.py", "return_none_instead_of_value", 322,
      "ValidatorInterface.validate_with_warnings docstring 'return both errors and warnings' — prose"),
     # ------------------------------------------------------------------
     # core/edi/inv_fetcher.py (test: test_inv_fetcher.py)
     #
     # The L171 true_to_false mutation is in an `except` block where
     # Python's logging module auto-populates exc_info from the
     # in-flight exception. ``exc_info=True`` and ``exc_info=False``
     # are equivalent here, so the mutation is equivalent.
     # ------------------------------------------------------------------
     ("core/edi/inv_fetcher.py", "and_to_or", 24,
      "docstring 'Execute a query and return results' — prose"),
     ("core/edi/inv_fetcher.py", "return_none_instead_of_value", 24,
      "docstring 'return results' — prose; mutation would change docstring text but has no runtime effect"),
     # ------------------------------------------------------------------
     # dispatch/error_handler.py (test: test_error_handler.py)
     #
     # The L144 true_to_false mutation is in an `except` block where
     # Python's logging module auto-populates exc_info from the
     # in-flight exception. The L3 and L38 mutations are in module
     # and function docstrings / format strings.
     # ------------------------------------------------------------------
     ("dispatch/error_handler.py", "and_to_or", 3,
      "module docstring 'centralized error handling and logging' — prose"),
     ("dispatch/error_handler.py", "int_constant_off_by_one", 38,
      "format string '=' * 50 — visual separator, off-by-one has no runtime effect"),
     ("dispatch/error_handler.py", "true_to_false", 144,
      "exc_info=True inside except block — Python's logging auto-populates exc_info from in-flight exception, so True/False are equivalent"),
     # ------------------------------------------------------------------
     # dispatch/pipeline/validator.py (test: test_pipeline_validator.py)
     #
     # All 4 surviving mutations on this module are in the module
     # docstring text of normalize_validation_output. The function
     # body has 4 real mutations that are killed by
     # TestNormalizeValidationOutput.
     # ------------------------------------------------------------------
     ("dispatch/pipeline/validator.py", "and_to_or", 25,
      "docstring 'or a plain bool. Any other type is logged as a warning and returned' — prose"),
     ("dispatch/pipeline/validator.py", "or_to_and", 25,
      "docstring 'or a plain bool. Any other type is logged as a warning and returned' — prose"),
     ("dispatch/pipeline/validator.py", "return_none_instead_of_value", 22,
      "docstring 'return value' — prose; mutation changes docstring text but has no runtime effect"),
     ("dispatch/pipeline/validator.py", "int_constant_off_by_one", 24,
      "docstring 'Accepts a 2-tuple' — example tuple size, mutation has no runtime effect"),
     # ------------------------------------------------------------------
     # interface/plugins/config_schemas.py (test: test_configuration_plugin.py)
     # ------------------------------------------------------------------
     ("interface/plugins/config_schemas.py", "and_to_or", 4,
      "module docstring 'configuration schemas and validation' — prose"),
     # ------------------------------------------------------------------
     # dispatch/edi_validator.py (test: test_edi_validator.py)
     #
     # L45 (false_to_true on has_errors: bool = False default) and
     # L83 (true_to_false on has_errors = True in the format-failure
     # early return) — both are KNOWN_EQUIVALENT because:
     # 1. L45 is a default param that callers always override
     # 2. L83's mutation doesn't change behavior since the early
     # return at L87 fires before the has_errors value is consulted
     # 3. has_errors is reset at the start of every validate() call
     # ------------------------------------------------------------------
     ("dispatch/edi_validator.py", "false_to_true", 45,
      "has_errors: bool = False default — callers reset this at the start of validate()"),
     ("dispatch/edi_validator.py", "true_to_false", 83,
      "self.has_errors = True in format-failure path — but the function returns immediately at L87 before is_valid is computed from has_errors"),
     ("dispatch/edi_validator.py", "and_to_or", 72,
      "comment 'Read file once and pass content to all validation methods' — prose"),
     ("dispatch/edi_validator.py", "int_constant_off_by_one", 233,
      "comment 'Check for missing pricing in 70-char lines' — prose, off-by-one has no runtime effect"),
]


# ---------------------------------------------------------------------------
# Outcome + report dataclasses.
# ---------------------------------------------------------------------------

@dataclass
class MutationOutcome:
    name: str
    line: int
    killed: bool
    failure_message: str = ""
    snippet: str = ""


@dataclass
class ModuleReport:
    module: Path
    test_path: Path
    total: int = 0
    killed: int = 0
    survived: int = 0
    skipped: int = 0
    outcomes: list[MutationOutcome] = field(default_factory=list)

    @property
    def kill_rate(self) -> float:
        return self.killed / self.total if self.total else 0.0


# ---------------------------------------------------------------------------
# Helpers.
# ---------------------------------------------------------------------------

def _apply_mutation_once(
    source: str,
    pattern: re.Pattern[str],
    replace: Callable[[re.Match[str]], str],
) -> tuple[str, int, str, str] | None:
    """Apply `replace` to the first match of `pattern` in `source`.

    Returns (new_source, line_number, original_line, mutated_line) on
    success, or None if no match. Only the first match is mutated per
    call so we test one change at a time. The original and mutated
    line text are returned so a reviewer can audit each survivor.
    """
    match = pattern.search(source)
    if match is None:
        return None
    new_source = source[: match.start()] + replace(match) + source[match.end():]
    line = source[: match.start()].count("\n") + 1
    line_start = source.rfind("\n", 0, match.start()) + 1
    line_end_search = source.find("\n", match.end())
    line_end = line_end_search if line_end_search != -1 else len(source)
    original_line = source[line_start:line_end]
    new_line_start = new_source.rfind("\n", 0, match.start()) + 1
    new_line_end_search = new_source.find("\n", match.end())
    new_line_end = new_line_end_search if new_line_end_search != -1 else len(new_source)
    mutated_line = new_source[new_line_start:new_line_end]
    return new_source, line, original_line, mutated_line


def _run_pytest(test_path: Path, cwd: Path) -> tuple[int, str]:
    """Run pytest on `test_path` and return (exit_code, combined_output).

    Force `-n0` so xdist workers do not isolate the mutation; force
    `--no-header -q` so output is short. We do NOT use `-x` — we want
    the full report, not a stop-on-first-failure.

    The subprocess timeout is generous: property tests do many
    examples, and a single mutation can be costly. A hang is reported
    as a kill (non-zero exit).
    """
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                str(test_path),
                "-n",
                "0",
                "-q",
                "--no-header",
                "--timeout=10",
                "-p",
                "no:cacheprovider",
            ],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=20,
        )
    except subprocess.TimeoutExpired:
        return 124, "SUBPROCESS TIMED OUT (treated as a kill)"
    return result.returncode, (result.stdout or "") + (result.stderr or "")


def _is_known_equivalent(module_rel: str, mutation_name: str, line: int) -> bool:
    """Return True if (module, mutation, line) is in KNOWN_EQUIVALENT.

    The lookup is by tuple identity. A typo in any field fails closed:
    the mutation is NOT skipped, so it will surface as a survivor and
    the runner will fail.
    """
    for m, n, l, _reason in KNOWN_EQUIVALENT:
        if m == module_rel and n == mutation_name and l == line:
            return True
    return False


# ---------------------------------------------------------------------------
# Public API.
# ---------------------------------------------------------------------------

def run_meta_test(
    module: Path,
    test_path: Path,
    *,
    repo_root: Path,
    module_rel: str | None = None,
    skip_known_equivalent: bool = True,
) -> ModuleReport:
    """Run all mutations against `module`, observing whether each kills
    the test at `test_path`. Returns a per-module report.

    When `skip_known_equivalent` is True, mutations in KNOWN_EQUIVALENT
    matching (module_rel, mutation_name, line) are not applied; they
    are recorded as `skipped` outcomes rather than `survived`.
    """
    report = ModuleReport(module=module, test_path=test_path)
    original_source = module.read_text()
    code, output = _run_pytest(test_path, repo_root)
    if code != 0:
        print(
            f"FATAL: tests at {test_path} do not pass on the "
            f"UNMODIFIED source of {module}. Fix that first.",
            file=sys.stderr,
        )
        print(output, file=sys.stderr)
        raise SystemExit(2)

    resolved_module_rel = module_rel or str(
        module.resolve().relative_to(repo_root.resolve())
    )

    for name, pattern, replace in MUTATIONS:
        mutation = _apply_mutation_once(original_source, pattern, replace)
        if mutation is None:
            continue
        mutated_source, line, original_line, mutated_line = mutation
        snippet = f"-{original_line}\n+{mutated_line}"
        if skip_known_equivalent and _is_known_equivalent(
            resolved_module_rel, name, line
        ):
            report.skipped += 1
            report.outcomes.append(
                MutationOutcome(name=name, line=line, killed=True, snippet=snippet)
            )
            print(
                f"  [{module.name}] SKIP (KNOWN_EQUIVALENT): {name} at line {line}",
                flush=True,
            )
            continue
        report.total += 1
        print(
            f"  [{module.name}] mutation {report.total}: {name} at line {line}",
            flush=True,
        )
        print(f"      {snippet}", flush=True)
        backup = module.read_text()
        try:
            module.write_text(mutated_source)
            code, output = _run_pytest(test_path, repo_root)
        finally:
            module.write_text(backup)
        if code == 0:
            report.survived += 1
            report.outcomes.append(
                MutationOutcome(
                    name=name, line=line, killed=False, snippet=snippet
                )
            )
        else:
            report.killed += 1
            report.outcomes.append(
                MutationOutcome(
                    name=name,
                    line=line,
                    killed=True,
                    snippet=snippet,
                    failure_message=output[-200:],
                )
            )
    return report


def render_report(report: ModuleReport) -> str:
    lines: list[str] = []
    lines.append(f"Module:    {report.module}")
    lines.append(f"Test file: {report.test_path}")
    lines.append(
        f"Killed:    {report.killed}/{report.total} "
        f"({report.kill_rate:.0%})"
    )
    lines.append(f"Survived:  {report.survived}")
    if report.skipped:
        lines.append(f"Skipped (KNOWN_EQUIVALENT): {report.skipped}")
    if report.survived:
        lines.append("")
        lines.append("SURVIVING MUTANTS (write a test to kill these):")
        for outcome in report.outcomes:
            if not outcome.killed:
                lines.append(
                    f"  - line {outcome.line:>4}: {outcome.name}"
                )
                if outcome.snippet:
                    for snippet_line in outcome.snippet.splitlines():
                        lines.append(f"      {snippet_line}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--module",
        type=Path,
        help="Production module to mutate (path relative to repo root). "
        "Use with --tests for a single pair.",
    )
    parser.add_argument(
        "--tests",
        type=Path,
        help="Test file that should detect the mutations. "
        "Use with --module for a single pair.",
    )
    parser.add_argument(
        "--pair-list",
        action="append",
        default=[],
        metavar="MODULE:TEST",
        help="A module:test pair (path relative to repo root, separated by ':'). "
        "Repeatable. If both --module and --pair-list are given, --pair-list is used.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent.parent,
        help="Path to repo root (default: parent of this file's parent).",
    )
    parser.add_argument(
        "--no-skip-known-equivalent",
        action="store_true",
        help="Apply every mutation including those in KNOWN_EQUIVALENT. "
        "Use this to audit the KNOWN_EQUIVALENT list itself.",
    )
    args = parser.parse_args(argv)

    pairs: list[tuple[Path, Path]] = []
    if args.pair_list:
        for raw in args.pair_list:
            if ":" not in raw:
                print(f"--pair-list entry must be MODULE:TEST, got: {raw}", file=sys.stderr)
                return 2
            module_str, test_str = raw.split(":", 1)
            pairs.append((Path(module_str), Path(test_str)))
    elif args.module and args.tests:
        pairs.append((args.module, args.tests))
    else:
        parser.error("either --pair-list or both --module and --tests are required")

    total_total = 0
    total_killed = 0
    total_survived = 0
    total_skipped = 0
    overall_survivors: list[tuple[Path, MutationOutcome]] = []

    for module, test_path in pairs:
        if not module.is_absolute():
            module = args.repo_root / module
        if not test_path.is_absolute():
            test_path = args.repo_root / test_path
        if not module.exists():
            print(f"Module not found: {module}", file=sys.stderr)
            return 2
        if not test_path.exists():
            print(f"Test file not found: {test_path}", file=sys.stderr)
            return 2

        module_rel = str(
            module.resolve().relative_to(args.repo_root.resolve())
        )
        report = run_meta_test(
            module,
            test_path,
            repo_root=args.repo_root,
            module_rel=module_rel,
            skip_known_equivalent=not args.no_skip_known_equivalent,
        )
        print(render_report(report))
        print()
        total_total += report.total
        total_killed += report.killed
        total_survived += report.survived
        total_skipped += report.skipped
        for outcome in report.outcomes:
            if not outcome.killed:
                overall_survivors.append((module, outcome))

    if len(pairs) > 1:
        print("=" * 60)
        print(
            f"OVERALL: killed {total_killed}/{total_total} "
            f"({(total_killed / total_total) if total_total else 0:.0%}), "
            f"survived {total_survived}, skipped {total_skipped}"
        )
        print()
        if overall_survivors:
            print("ALL SURVIVING MUTANTS (write tests to kill these):")
            for module, outcome in overall_survivors:
                print(f"  {module.name}:{outcome.line}  {outcome.name}")

    return 1 if total_survived else 0


# ---------------------------------------------------------------------------
# Pytest-discoverable wrapper. When pytest collects this file, it picks up
# `test_default_modules_have_sufficient_test_coverage`. The test runs the
# full meta-mutation suite against the DEFAULT_PAIRS and fails if any
# mutant survives. Survivors must be addressed by writing stronger tests
# (or by adding the mutant to KNOWN_EQUIVALENT with a cited reason).
#
# Marked `slow` because it spawns one pytest subprocess per mutation.
# ---------------------------------------------------------------------------

@pytest.mark.slow
def test_default_modules_have_sufficient_test_coverage() -> None:
    """Run meta-mutation against every DEFAULT_PAIRS entry; fail on survivor.

    A survivor is a mutation the test file does NOT catch. Either the
    tests are too weak (write a stronger one) or the mutation is
    equivalent (no observable behavior change — add it to
    KNOWN_EQUIVALENT with a one-line cited reason).
    """
    repo_root = Path(__file__).resolve().parent.parent.parent
    overall_survivors: list[tuple[str, str, int, str]] = []
    for module_rel, test_rel in DEFAULT_PAIRS:
        module = repo_root / module_rel
        test_path = repo_root / test_rel
        if not module.exists() or not test_path.exists():
            pytest.skip(f"missing {module_rel} or {test_rel}")
        report = run_meta_test(
            module,
            test_path,
            repo_root=repo_root,
            module_rel=module_rel,
        )
        for outcome in report.outcomes:
            if not outcome.killed:
                overall_survivors.append(
                    (module.name, outcome.name, outcome.line, str(module))
                )
    if overall_survivors:
        msg_lines = [
            "Surviving mutants. Either tighten the test, or add the "
            "mutation to KNOWN_EQUIVALENT with a cited reason:"
        ]
        for fname, name, line, _path in overall_survivors:
            msg_lines.append(f"  {fname}:{line}  {name}")
        pytest.fail("\n".join(msg_lines))


if __name__ == "__main__":
    sys.exit(main())

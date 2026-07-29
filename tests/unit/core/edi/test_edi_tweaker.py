"""Unit tests for EDITweaker."""

import os
from unittest.mock import MagicMock, patch

import pytest

from core.edi.edi_tweaker import EDITweaker, TweakerConfig, TweakerQueryRunnerProtocol


def make_a_record(
    cust_vendor="VENDOR",
    invoice_number="0000000001",
    invoice_date="010125",
    invoice_total="0000010000",
):
    return (
        "A"
        + cust_vendor[:6].ljust(6)
        + invoice_number[:10].ljust(10)
        + invoice_date[:6].ljust(6)
        + invoice_total[:10].ljust(10)
    )


def make_b_record(
    upc="01234567890",
    description="Test Item Description    ",
    vendor_item="123456",
    unit_cost="000100",
    combo="01",
    unit_multiplier="000006",
    quantity="00010",
    retail="00199",
    pack="001",
    parent_item="000000",
):
    return (
        "B"
        + upc[:11].ljust(11)
        + description[:25].ljust(25)
        + vendor_item[:6].ljust(6)
        + unit_cost[:6].ljust(6)
        + combo[:2].ljust(2)
        + unit_multiplier[:6].ljust(6)
        + quantity[:5].ljust(5)
        + retail[:5].ljust(5)
        + pack[:3].ljust(3)
        + parent_item[:6].ljust(6)
    )


def make_c_record(
    charge_type="TAB",
    description="Sales Tax               ",
    amount="000010000",
):
    return (
        "C"
        + charge_type[:3].ljust(3)
        + description[:25].ljust(25)
        + amount[:9].ljust(9)
    )


VALID_EDI = make_a_record() + "\n" + make_b_record() + "\n" + make_c_record() + "\n"


class TestTweakerConfig:
    """Tests for TweakerConfig dataclass."""

    def test_config_defaults(self):
        config = TweakerConfig()
        assert config.pad_arec is False
        assert config.force_txt_file_ext is False
        assert config.invoice_date_offset == 0
        assert config.override_upc is False

    def test_from_params_empty(self):
        config = TweakerConfig.from_params({})
        assert config.pad_arec is False
        assert config.force_txt_file_ext is False

    def test_from_params_with_values(self):
        config = TweakerConfig.from_params(
            {
                "pad_a_records": "True",
                "force_txt_file_ext": "True",
                "invoice_date_offset": 5,
            }
        )
        assert config.pad_arec is True
        assert config.force_txt_file_ext is True
        assert config.invoice_date_offset == 5


class TestEDITweaker:
    """Tests for EDITweaker class."""

    @pytest.fixture
    def mock_query_runner(self):
        return MagicMock(spec=TweakerQueryRunnerProtocol)

    @pytest.fixture
    def tweaker(self, mock_query_runner):
        return EDITweaker(mock_query_runner)

    @pytest.fixture
    def edi_file(self, tmp_path):
        f = tmp_path / "test.edi"
        f.write_text(VALID_EDI, encoding="utf-8")
        return str(f)

    def test_init_stores_query_runner(self, mock_query_runner):
        t = EDITweaker(mock_query_runner)
        assert t.query_runner is mock_query_runner

    def test_init_default_config(self, mock_query_runner):
        t = EDITweaker(mock_query_runner)
        assert t.config is not None
        assert isinstance(t.config, TweakerConfig)

    def test_init_custom_config(self, mock_query_runner):
        config = TweakerConfig(force_txt_file_ext=True)
        t = EDITweaker(mock_query_runner, config)
        assert t.config.force_txt_file_ext is True

    def test_tweak_passthrough(self, tweaker, edi_file, tmp_path):
        output = str(tmp_path / "output.edi")
        result = tweaker.tweak(edi_file, output, {}, {"pad_a_records": "False"}, {})
        assert result == output
        with open(output) as f:
            content = f.read()
        assert "A" in content
        assert "B" in content

    def test_tweak_progress_log_fires_only_at_multiples_of_100(
        self, mock_query_runner, tmp_path
    ):
        """Regression test for gt_to_ge + eq_to_ne mutations at L386.

        The progress-log condition ``line_num > 0 and line_num % 100 == 0``
        fires exactly at line 100 (0-indexed: the 101st line). With
        101 B records, expect exactly 1 progress-log call.
        - gt_to_ge mutation (>= 0): fires at line 0 too -> 2 calls
        - eq_to_ne mutation (!= 0): fires at every non-multiple -> 100 calls
        """
        # Create EDI with 101 B records so line_num=100 triggers the log
        lines = [make_b_record() for _ in range(101)]
        content = "\n".join(lines) + "\n"
        input_path = tmp_path / "in.edi"
        input_path.write_text(content, encoding="utf-8")
        output_path = str(tmp_path / "out.edi")

        tweaker = EDITweaker(mock_query_runner)
        with patch("core.edi.edi_tweaker.StructuredLogger.log_debug") as mock_log:
            tweaker.tweak(str(input_path), output_path, {}, {}, {})

        # Filter to progress-log calls (the "Processing: N/M lines" message)
        progress_calls = [
            call for call in mock_log.call_args_list if "Processing:" in str(call)
        ]
        assert (
            len(progress_calls) == 1
        ), f"Expected 1 progress-log call at line 100, got {len(progress_calls)}"

    def test_apply_upc_calc_pads_non_numeric_upc(self, mock_query_runner):
        """Regression test for true_to_false mutation at L622.

        When ``int(fields['upc_number'])`` raises ValueError (non-numeric
        UPC), the code sets ``blank_upc = True`` and pads the UPC with
        ``upc_padding_pattern[:upc_target_length]`` (default: 11 spaces).
        A mutation to ``blank_upc = False`` would skip padding and leave
        the non-numeric UPC unchanged, or crash on a later int() call.
        """
        config = TweakerConfig()
        t = EDITweaker(mock_query_runner, config)
        fields = {"upc_number": "ABC123XYZ"}  # non-numeric -> ValueError

        result = t._apply_upc_calc(fields)

        # The non-numeric UPC must be replaced with the padding pattern
        assert result["upc_number"] == "           "  # 11 spaces
        assert result["upc_number"] != "ABC123XYZ"

    def test_tweak_force_txt_extension(self, tweaker, edi_file, tmp_path):
        output = str(tmp_path / "output")
        result = tweaker.tweak(edi_file, output, {}, {"force_txt_file_ext": "True"}, {})
        assert result == output + ".txt"

    def test_tweak_pad_a_record(self, mock_query_runner, edi_file, tmp_path):
        config = TweakerConfig(pad_arec=True, arec_padding="TEST", arec_padding_len=6)
        t = EDITweaker(mock_query_runner, config)
        output = str(tmp_path / "output.edi")
        t.tweak(edi_file, output, {}, {}, {})
        with open(output) as f:
            first_line = f.readline()
        assert first_line.startswith("ATEST  ")

    def test_tweak_invoice_date_offset(self, mock_query_runner, edi_file, tmp_path):
        config = TweakerConfig(invoice_date_offset=5)
        t = EDITweaker(mock_query_runner, config)
        output = str(tmp_path / "output.edi")
        t.tweak(edi_file, output, {}, {}, {})
        with open(output) as f:
            first_line = f.readline()
        # Original date 010125 + 5 days = 010625
        assert "010625" in first_line

    def test_tweak_upc_override(self, mock_query_runner, edi_file, tmp_path):
        config = TweakerConfig(
            override_upc=True, override_upc_level=2, override_upc_category_filter="ALL"
        )
        t = EDITweaker(mock_query_runner, config)
        output = str(tmp_path / "output.edi")
        upc_dict = {123456: ("CAT", "11111111111", "22222222222")}
        t.tweak(edi_file, output, {}, {}, upc_dict)
        with open(output) as f:
            lines = f.readlines()
        assert len(lines) >= 2
        assert "22222222222" in lines[1]

    def test_tweak_upc_calc(self, mock_query_runner, edi_file, tmp_path):
        """Test that calc_upc adds check digit to 11-digit UPC."""
        # B record with 11-digit UPC (no check digit)
        b_no_check = make_b_record(upc="01234567890")
        content = make_a_record() + "\n" + b_no_check + "\n"
        f = tmp_path / "no_check.edi"
        f.write_text(content, encoding="utf-8")

        config = TweakerConfig(calc_upc=True)
        t = EDITweaker(mock_query_runner, config)
        output = str(tmp_path / "output.edi")
        t.tweak(str(f), output, {}, {}, {})
        with open(output) as f_out:
            lines = f_out.readlines()
        upc_line = lines[1]
        # 01234567890 + check digit should be 12 chars
        assert len(upc_line.strip()) > 11

    @pytest.mark.parametrize(
        "make_record_fn,record_type",
        [
            (make_a_record, "A"),
            (make_b_record, "B"),
            (make_c_record, "C"),
        ],
    )
    def test_tweak_each_record_type(
        self, tweaker, tmp_path, make_record_fn, record_type
    ):
        content = make_record_fn() + "\n"
        f = tmp_path / "single.edi"
        f.write_text(content, encoding="utf-8")
        output = str(tmp_path / "output.edi")
        result = tweaker.tweak(str(f), output, {}, {}, {})
        with open(result) as f_out:
            line = f_out.readline()
        assert line.startswith(record_type)

    def test_tweak_empty_file_does_not_crash(self, tweaker, tmp_path):
        f = tmp_path / "empty.edi"
        f.write_text("", encoding="utf-8")
        output = str(tmp_path / "output.edi")
        result = tweaker.tweak(str(f), output, {}, {}, {})
        with open(result) as f_out:
            assert f_out.read() == ""

    def test_handle_negative_digits(self, mock_query_runner):
        config = TweakerConfig()
        t = EDITweaker(mock_query_runner, config)
        fields = {
            "unit_cost": "-00100",
            "unit_multiplier": "000006",
            "qty_of_units": "00010",
            "suggested_retail_price": "00199",
        }
        result = t._handle_negative_digits(fields)
        # Only unit_cost had a leading -; it should be preserved
        assert result["unit_cost"] == "-00100"
        assert result["qty_of_units"] == "00010"

    def test_handle_negative_digits_moves_to_front(self, mock_query_runner):
        config = TweakerConfig()
        t = EDITweaker(mock_query_runner, config)
        fields = {
            "unit_cost": "00-100",
            "unit_multiplier": "000006",
            "qty_of_units": "00010",
            "suggested_retail_price": "00199",
        }
        result = t._handle_negative_digits(fields)
        assert result["unit_cost"] == "-00100"

    def test_validate_parent_item_truncates_if_oversize(self, mock_query_runner):
        config = TweakerConfig()
        t = EDITweaker(mock_query_runner, config)
        # projected_line shorter than EDI_B_RECORD_STANDARD_LENGTH
        projected = "B" + "a" * 60
        fields = {"parent_item_number": "123456"}
        result = t._validate_parent_item_length(fields, projected)
        assert result["parent_item_number"] == ""

    def test_validate_parent_item_preserves_if_valid(self, mock_query_runner):
        config = TweakerConfig()
        t = EDITweaker(mock_query_runner, config)
        projected = "B" + "x" * 76
        fields = {"parent_item_number": "123456"}
        result = t._validate_parent_item_length(fields, projected)
        assert result["parent_item_number"] == "123456"


class TestEDITweakerFileHandles:
    """Tests for file handle safety in EDITweaker.tweak()."""

    @pytest.fixture
    def mock_query_runner(self):
        return MagicMock(spec=TweakerQueryRunnerProtocol)

    def test_file_handles_closed_on_success(self, tmp_path, mock_query_runner):
        t = EDITweaker(mock_query_runner)
        content = make_a_record() + "\n"
        f = tmp_path / "in.edi"
        f.write_text(content, encoding="utf-8")
        output = str(tmp_path / "out.edi")

        t.tweak(str(f), output, {}, {}, {})

        with open(str(f)) as fh:
            assert fh.read() == content
        with open(output) as fh:
            assert fh.read() != ""

    def test_file_handles_closed_on_tweak_error(self, tmp_path, mock_query_runner):
        """When _process_records raises, both file handles must be closed."""
        t = EDITweaker(mock_query_runner)
        content = make_a_record() + "\n" + make_b_record() + "\n"
        f = tmp_path / "in.edi"
        f.write_text(content, encoding="utf-8")
        output = str(tmp_path / "out.edi")

        with patch.object(
            t, "_process_records", side_effect=RuntimeError("tweak failed")
        ):
            with pytest.raises(RuntimeError, match="tweak failed"):
                t.tweak(str(f), output, {}, {}, {})

        with open(str(f)) as fh:
            assert fh.read() != ""

        if os.path.exists(output):
            with open(output) as fh:
                fh.read()

    def test_open_input_retry_on_oserror(self, mock_query_runner, tmp_path):
        t = EDITweaker(mock_query_runner)
        f = tmp_path / "retry.edi"
        f.write_text("test", encoding="utf-8")

        with patch.object(t, "_open_input_with_retry", wraps=t._open_input_with_retry):
            result = t._open_input_with_retry(str(f))
            assert result is not None
            result.close()

    def test_open_input_with_retry_raises_oserror_after_5_attempts(
        self, mock_query_runner, tmp_path
    ):
        """Regression test for lt_to_le mutation at L322.

        The retry boundary ``attempt + 1 < max_retries`` (max_retries=5)
        determines whether the 5th attempt raises or retries. With
        ``<``, the 5th attempt (attempt+1=5) raises OSError. With
        ``<=``, the 5th attempt retries, the loop ends, and the
        unreachable RuntimeError fires instead.
        """
        t = EDITweaker(mock_query_runner)
        f = tmp_path / "missing.edi"
        # File doesn't exist -> open() raises FileNotFoundError (OSError subclass)

        with patch("time.sleep"), pytest.raises(OSError) as exc_info:
            t._open_input_with_retry(str(f))

        # Original: OSError propagated from the 5th attempt
        # Mutated (<=): RuntimeError from the unreachable fallback
        assert not isinstance(
            exc_info.value, RuntimeError
        ), "Expected OSError, got RuntimeError — suggests <= mutation"


class TestQueryRunnerAdapter:
    """Tests for _create_query_runner_adapter."""

    def test_noop_runner_when_missing_credentials(self):
        from core.edi.edi_tweaker import _create_query_runner_adapter

        runner = _create_query_runner_adapter(
            {"as400_username": "", "as400_password": "", "as400_address": ""}
        )
        assert runner.run_query("SELECT 1") == []

    def test_noop_runner_partial_credentials(self):
        from core.edi.edi_tweaker import _create_query_runner_adapter

        runner = _create_query_runner_adapter(
            {"as400_username": "user", "as400_password": "", "as400_address": ""}
        )
        assert runner.run_query("SELECT 1") == []

    def test_noop_runner_implements_protocol(self):
        from core.edi.edi_tweaker import _create_query_runner_adapter

        runner = _create_query_runner_adapter(
            {"as400_username": "", "as400_password": "", "as400_address": ""}
        )
        assert isinstance(runner, TweakerQueryRunnerProtocol)


class TestEachUOMCategoryFilter:
    """Tests for the each_uom_categories / each_uom_mode filter on retail UOM."""

    @pytest.fixture
    def mock_query_runner(self):
        return MagicMock(spec=TweakerQueryRunnerProtocol)

    def test_tweaker_config_defaults(self):
        config = TweakerConfig()
        assert config.each_uom_categories == "ALL"
        assert config.each_uom_mode == "include"

    def test_from_params_each_uom_filter(self):
        config = TweakerConfig.from_params(
            {
                "each_uom_categories": "1,2",
                "each_uom_mode": "exclude",
            }
        )
        assert config.each_uom_categories == "1,2"
        assert config.each_uom_mode == "exclude"

    @pytest.mark.parametrize(
        "categories,mode,vendor_item,upc_dict,expected",
        [
            ("ALL", "include", 123, {123: ("1", "u", "v")}, True),
            ("", "include", 123, {123: ("1", "u", "v")}, True),
            ("1", "include", 123, {123: ("1", "u", "v")}, True),
            ("1", "include", 123, {123: ("2", "u", "v")}, False),
            ("1,2", "include", 123, {123: ("2", "u", "v")}, True),
            ("1", "exclude", 123, {123: ("1", "u", "v")}, False),
            ("1", "exclude", 123, {123: ("2", "u", "v")}, True),
            # Item not in upc dict -> passes through (transform runs)
            ("1", "include", 999, {123: ("1", "u", "v")}, True),
        ],
    )
    def test_should_apply_retail_uom_helper(
        self, categories, mode, vendor_item, upc_dict, expected
    ):
        from dispatch.converters.csv_utils import should_apply_retail_uom

        fields = {"vendor_item": str(vendor_item)}
        assert should_apply_retail_uom(fields, upc_dict, categories, mode) is expected

    def test_transform_retail_uom_gated_by_filter(self, mock_query_runner):
        config = TweakerConfig(
            retail_uom=True,
            each_uom_categories="1",
            each_uom_mode="include",
        )
        t = EDITweaker(mock_query_runner, config)
        fields = {
            "vendor_item": "123",
            "unit_cost": "10000",
            "unit_multiplier": "000006",
            "qty_of_units": "00010",
            "upc_number": "           ",
        }
        original_cost = fields["unit_cost"]
        result = t._transform_retail_uom(fields, {123: ("2", "u", "v")})
        assert result["unit_cost"] == original_cost

    def test_transform_retail_uom_passes_with_all(self, mock_query_runner):
        config = TweakerConfig(retail_uom=True)
        t = EDITweaker(mock_query_runner, config)
        fields = {
            "vendor_item": "123",
            "unit_cost": "10000",
            "unit_multiplier": "000006",
            "qty_of_units": "00010",
            "upc_number": "           ",
        }
        result = t._transform_retail_uom(fields, {123: ("2", "u", "v")})
        assert result["unit_cost"] != "10000"

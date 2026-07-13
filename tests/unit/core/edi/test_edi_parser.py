"""Unit tests for EDI parser functions."""

import pytest

from core.edi.edi_parser import (
    ARecord,
    BRecord,
    CRecord,
    build_a_record,
    build_b_record,
    build_c_record,
    capture_records,
    parse_a_record,
    parse_b_record,
    parse_c_record,
)


class TestARecord:
    """Tests for A record dataclass."""

    def test_a_record_creation(self):
        """Test creating an ARecord instance."""
        record = ARecord(
            record_type="A",
            cust_vendor="VENDOR",
            invoice_number="0000000001",
            invoice_date="012424",
            invoice_total="0000000123",
        )
        assert record.record_type == "A"
        assert record.cust_vendor == "VENDOR"
        assert record.invoice_number == "0000000001"
        assert record.invoice_date == "012424"
        assert record.invoice_total == "0000000123"

    def test_a_record_equality(self):
        """Test ARecord equality comparison."""
        record1 = ARecord("A", "VENDOR", "0000000001", "012424", "0000000123")
        record2 = ARecord("A", "VENDOR", "0000000001", "012424", "0000000123")
        assert record1 == record2


class TestBRecord:
    """Tests for B record dataclass."""

    def test_b_record_creation(self):
        """Test creating a BRecord instance."""
        record = BRecord(
            record_type="B",
            upc_number="00123456789",
            description="Test Item Description   ",
            vendor_item="123456",
            unit_cost="001234",
            combo_code="01",
            unit_multiplier="000001",
            qty_of_units="00005",
            suggested_retail_price="00123",
            price_multi_pack="   ",
            parent_item_number="      ",
        )
        assert record.record_type == "B"
        assert record.upc_number == "00123456789"
        assert record.vendor_item == "123456"


class TestCRecord:
    """Tests for C record dataclass."""

    def test_c_record_creation(self):
        """Test creating a CRecord instance."""
        record = CRecord(
            record_type="C",
            charge_type="FRT",
            description="Freight Charge          ",
            amount="000001234",
        )
        assert record.record_type == "C"
        assert record.charge_type == "FRT"
        assert record.amount == "000001234"


class TestCaptureRecords:
    """Tests for capture_records function."""

    def test_capture_a_record(self):
        """Test parsing an A record line."""
        # A record: A(1) + cust_vendor(6) + invoice_number(10) + invoice_date(6) + invoice_total(10)
        # Total: 33 chars before newline
        # Positions: 0=A, 1-6=cust_vendor, 7-16=invoice_number, 17-22=invoice_date, 23-32=invoice_total
        line = "AVENDOR00000000010101240000000123\n"
        result = capture_records(line)

        assert result is not None
        assert result["record_type"] == "A"
        assert result["cust_vendor"] == "VENDOR"
        assert result["invoice_number"] == "0000000001"
        assert result["invoice_date"] == "010124"
        assert result["invoice_total"] == "0000000123"

    def test_capture_b_record(self):
        """Test parsing a B record line."""
        # B record: B(1) + upc(11) + desc(25) + vendor_item(6) + unit_cost(6) + combo(2) + multiplier(6) + qty(5) + retail(5) + multi_pack(3) + parent(6)
        # Total: 76 chars before newline
        # Create a properly formatted B record with exactly 25 char description
        # desc = "Test Item Description    " (25 chars with trailing space)
        line = "B00123456789Test Item Description    123456001234010000010000500123      \n"
        result = capture_records(line)

        assert result is not None
        assert result["record_type"] == "B"
        assert result["upc_number"] == "00123456789"
        assert result["description"] == "Test Item Description    "
        assert result["vendor_item"] == "123456"
        assert result["unit_cost"] == "001234"
        assert result["combo_code"] == "01"
        assert result["unit_multiplier"] == "000001"
        assert result["qty_of_units"] == "00005"
        assert result["suggested_retail_price"] == "00123"

    def test_capture_c_record(self):
        """Test parsing a C record line."""
        # C record: C(1) + charge_type(3) + desc(25) + amount(9)
        # Total: 38 chars before newline
        # desc = "Freight Charge           " (25 chars with trailing space)
        line = "CFRTFreight Charge           000001234\n"
        result = capture_records(line)

        assert result is not None
        assert result["record_type"] == "C"
        assert result["charge_type"] == "FRT"
        assert result["description"] == "Freight Charge           "
        assert result["amount"] == "000001234"

    def test_capture_empty_line(self):
        """Test parsing an empty line."""
        result = capture_records("")
        assert result is None

    def test_capture_eof_marker(self):
        """Test parsing EOF marker (Ctrl+Z)."""
        result = capture_records("\x1a")
        assert result is None

    def test_capture_unknown_record_type(self):
        """Test parsing unknown record type returns None."""
        result = capture_records("X123456\n")
        assert result is None

    def test_capture_a_record_negative_total(self):
        """Test parsing A record with negative total (credit)."""
        # A record with negative total - the minus sign is part of the total field
        # Positions: 0=A, 1-6=cust_vendor, 7-16=invoice_number, 17-22=invoice_date, 23-32=invoice_total
        line = "AVENDOR0000000001010124-000000123\n"
        result = capture_records(line)

        assert result is not None
        # The total field is 10 chars starting at position 23
        assert result["invoice_total"] == "-000000123"

    def test_capture_records_with_parser_returns_parser_result(self):
        """Regression: when a parser is provided, capture_records must
        return whatever the parser returns. The mutation runner's
        ``return_none_instead_of_value`` at edi_parser.py:182
        (flipping ``return result`` to ``return None``) was not caught
        by existing tests because no test exercised the
        ``parser is not None`` code path with a parser that returned
        a non-None result.
        """
        sentinel = {"record_type": "A", "from": "parser"}

        class _FakeParser:
            def parse_line(self, _line: str) -> dict:
                return sentinel

        result = capture_records("ignored\n", parser=_FakeParser())
        assert result == sentinel, (
            f"expected parser's return value {sentinel!r}, got {result!r}"
        )

    def test_capture_records_with_parser_returns_none_for_eof_marker(self):
        """Regression: when a parser is provided and returns None for a
        line that is just the EOF marker (``\\x1a`` after strip), the
        function must return None, NOT raise EDIParseError. The
        mutation runner's ``eq_to_ne`` at edi_parser.py:179 (flipping
        ``==`` to ``!=``) would cause the function to raise for the
        EOF marker line.

        See commit ea1ed275d (Phase 3 bug 5) for the audit trail.
        """
        class _FakeParser:
            def parse_line(self, _line: str) -> dict | None:
                return None

        # Single Ctrl-Z character (the SUB / EOF marker).
        result = capture_records("\x1a", parser=_FakeParser())
        assert result is None, (
            f"expected None for EOF marker line, got {result!r}"
        )

    def test_capture_records_with_parser_raises_on_unparseable_nonempty(self):
        """Regression: when a parser is provided and returns None for a
        non-empty line that isn't just the EOF marker, the function
        must raise EDIParseError. The mutation runner's ``ne_to_eq``
        at edi_parser.py:178 (flipping ``!=`` to ``==`` in
        ``line.strip() != ""``) would cause the function to
        short-circuit and silently return None instead of raising.

        See commit ea1ed275d (Phase 3 bug 5) for the audit trail.
        """
        from core.edi.edi_parser import EDIParseError

        class _FakeParser:
            def parse_line(self, _line: str) -> dict | None:
                return None

        # A non-empty, non-EOF-marker line. Parser returns None.
        # Expected: capture_records raises EDIParseError.
        with pytest.raises(EDIParseError, match="Not An EDI"):
            capture_records("garbage", parser=_FakeParser())


class TestParseARecord:
    """Tests for parse_a_record function."""

    def test_parse_a_record_valid(self):
        """Test parsing valid A record."""
        line = "AVENDOR00000000010101240000000123\n"
        record = parse_a_record(line)

        assert isinstance(record, ARecord)
        assert record.record_type == "A"
        assert record.cust_vendor == "VENDOR"

    def test_parse_a_record_invalid_b(self):
        """Test parsing B record as A record raises error."""
        line = "B00123456789Test Item Description    123456001234010000010000500123      \n"

        with pytest.raises(ValueError, match="Not an A record"):
            parse_a_record(line)

    def test_parse_a_record_empty(self):
        """Test parsing empty line as A record raises error."""
        with pytest.raises(ValueError):
            parse_a_record("")

    def test_parse_a_record_minimum_length_exactly_33_chars(self):
        """Regression: a 33-char A record (exactly EDI_A_RECORD_MIN_LENGTH)
        must parse successfully. The mutation runner's ``lt_to_le`` at
        edi_parser.py:89 (flipping ``<`` to ``<=``) was not caught by
        the existing tests because every A-record test used a 34-char
        line (33 + newline), so both ``<`` and ``<=`` returned False
        for the length check and the parser succeeded either way.
        A 33-char line is the boundary; with the mutation applied,
        the function would short-circuit and return None.

        See commit ea1ed275d (Phase 3 bug 5) for the audit trail.
        """
        # Exactly 33 chars, no newline — the boundary case.
        line_33 = "AVENDOR00000000010101240000000123"
        assert len(line_33) == 33, "test setup error: line should be exactly 33 chars"

        record = parse_a_record(line_33)
        assert isinstance(record, ARecord), (
            f"expected ARecord at boundary len=33, got {record!r}"
        )
        assert record.record_type == "A"
        assert record.cust_vendor == "VENDOR"


class TestParseBRecord:
    """Tests for parse_b_record function."""

    def test_parse_b_record_valid(self):
        """Test parsing valid B record."""
        line = "B00123456789Test Item Description    123456001234010000010000500123      \n"
        record = parse_b_record(line)

        assert isinstance(record, BRecord)
        assert record.record_type == "B"
        assert record.upc_number == "00123456789"

    def test_parse_b_record_invalid_a(self):
        """Test parsing A record as B record raises error."""
        line = "AVENDOR00000000010101240000000123\n"

        with pytest.raises(ValueError, match="Not a B record"):
            parse_b_record(line)


class TestParseCRecord:
    """Tests for parse_c_record function."""

    def test_parse_c_record_valid(self):
        """Test parsing valid C record."""
        line = "CFRTFreight Charge           000001234\n"
        record = parse_c_record(line)

        assert isinstance(record, CRecord)
        assert record.record_type == "C"
        assert record.charge_type == "FRT"

    def test_parse_c_record_invalid(self):
        """Test parsing A record as C record raises error."""
        line = "AVENDOR00000000010101240000000123\n"

        with pytest.raises(ValueError, match="Not a C record"):
            parse_c_record(line)


class TestBuildARecord:
    """Tests for build_a_record function."""

    def test_build_a_record_basic(self):
        """Test building basic A record."""
        line = build_a_record(
            cust_vendor="VENDOR",
            invoice_number="0000000001",
            invoice_date="012424",
            invoice_total="0000000123",
        )

        assert line.startswith("A")
        assert "VENDOR" in line
        assert "0000000001" in line
        assert line.endswith("\n")

    def test_build_a_record_with_append(self):
        """Test building A record with appended text."""
        line = build_a_record(
            cust_vendor="VENDOR",
            invoice_number="0000000001",
            invoice_date="012424",
            invoice_total="0000000123",
            append_text="EXTRA",
        )

        assert "EXTRA" in line

    def test_build_a_record_roundtrip(self):
        """Test building and parsing A record."""
        original = build_a_record(
            cust_vendor="VENDOR",
            invoice_number="0000000001",
            invoice_date="012424",
            invoice_total="0000000123",
        )
        parsed = parse_a_record(original)

        assert parsed.cust_vendor == "VENDOR"
        assert parsed.invoice_number == "0000000001"
        assert parsed.invoice_date == "012424"
        assert parsed.invoice_total == "0000000123"


class TestBuildBRecord:
    """Tests for build_b_record function."""

    def test_build_b_record_basic(self):
        """Test building basic B record."""
        line = build_b_record(
            upc_number="00123456789",
            description="Test Item Description    ",
            vendor_item="123456",
            unit_cost="001234",
            combo_code="01",
            unit_multiplier="000001",
            qty_of_units="00005",
            suggested_retail_price="00123",
        )

        assert line.startswith("B")
        assert "00123456789" in line
        assert line.endswith("\n")

    def test_build_b_record_with_defaults(self):
        """Test building B record with default values."""
        line = build_b_record(
            upc_number="00123456789",
            description="Test Item                 ",
            vendor_item="123456",
            unit_cost="001234",
            combo_code="01",
            unit_multiplier="000001",
            qty_of_units="00005",
            suggested_retail_price="00123",
        )

        # Should have default spaces for price_multi_pack and parent_item_number
        assert len(line) > 70  # B record should be ~76 chars + newline

    def test_build_b_record_roundtrip(self):
        """Test building and parsing B record."""
        original = build_b_record(
            upc_number="00123456789",
            description="Test Item Description    ",
            vendor_item="123456",
            unit_cost="001234",
            combo_code="01",
            unit_multiplier="000001",
            qty_of_units="00005",
            suggested_retail_price="00123",
            price_multi_pack="   ",
            parent_item_number="      ",
        )
        parsed = parse_b_record(original)

        assert parsed.upc_number == "00123456789"
        assert parsed.vendor_item == "123456"


class TestBuildCRecord:
    """Tests for build_c_record function."""

    def test_build_c_record_basic(self):
        """Test building basic C record."""
        line = build_c_record(
            charge_type="FRT",
            description="Freight Charge           ",
            amount="000001234",
        )

        assert line.startswith("C")
        assert "FRT" in line
        assert line.endswith("\n")

    def test_build_c_record_roundtrip(self):
        """Test building and parsing C record."""
        original = build_c_record(
            charge_type="FRT",
            description="Freight Charge           ",
            amount="000001234",
        )
        parsed = parse_c_record(original)

        assert parsed.charge_type == "FRT"
        assert parsed.amount == "000001234"


class TestRecordIntegration:
    """Integration tests for record parsing and building."""

    def test_full_invoice_roundtrip(self):
        """Test parsing and building a complete invoice."""
        # Build records
        a_line = build_a_record(
            cust_vendor="VENDOR",
            invoice_number="0000000001",
            invoice_date="012424",
            invoice_total="0000000123",
        )
        b_line = build_b_record(
            upc_number="00123456789",
            description="Test Item Description    ",  # 25 chars
            vendor_item="123456",
            unit_cost="001234",
            combo_code="01",
            unit_multiplier="000001",
            qty_of_units="00005",
            suggested_retail_price="00123",
        )
        c_line = build_c_record(
            charge_type="FRT",
            description="Freight Charge           ",  # 25 chars
            amount="000001234",
        )

        # Parse them back
        a_record = parse_a_record(a_line)
        b_record = parse_b_record(b_line)
        c_record = parse_c_record(c_line)

        # Verify
        assert a_record.invoice_number == "0000000001"
        assert b_record.vendor_item == "123456"
        assert c_record.charge_type == "FRT"

    def test_capture_records_handles_various_lengths(self):
        """Test capture_records handles lines of various lengths."""
        # A record with minimum valid length (33 chars before newline)
        # record_type(1) + cust_vendor(6) + invoice_number(10) + invoice_date(6) + invoice_total(10)
        min_valid_line = "AVENDOR00000000011234567890123456\n"
        result = capture_records(min_valid_line)

        # Should parse successfully
        assert result is not None
        assert result["record_type"] == "A"

    def test_capture_records_truncated_a_record_returns_none(self):
        """Regression: truncated A record should return None with debug log, not corrupted data."""
        # A record needs >=33 chars, this is only 25
        short_line = "AVENDOR00000000010101\n"
        result = capture_records(short_line)

        # Should return None for truncated record, not corrupted data
        assert result is None

    def test_capture_records_truncated_b_record_returns_none(self):
        """Regression: truncated B record should return None with debug log, not corrupted data."""
        # B record needs >=70 chars, this is only 32
        short_line = "B00123456789Test Item Descrip\n"
        result = capture_records(short_line)

        # Should return None for truncated record, not corrupted data
        assert result is None

    def test_capture_records_truncated_b_record_with_partial_parent(self):
        """Regression: B record with parent but less than 76 chars should return partial parent."""
        # 70-75 chars: has all required fields but parent is truncated
        line_75 = (
            "B00123456789Test Item Description    123456001234010000010000500123     \n"
        )
        result = capture_records(line_75)

        assert result is not None
        assert result["record_type"] == "B"
        assert result["parent_item_number"] == ""  # Truncated, not corrupted

    def test_capture_records_truncated_c_record_returns_none(self):
        """Regression: truncated C record should return None with debug log, not corrupted data."""
        # C record needs >=38 chars, this is only 20
        short_line = "CFRTFreight Charg\n"
        result = capture_records(short_line)

        # Should return None for truncated record, not corrupted data
        assert result is None

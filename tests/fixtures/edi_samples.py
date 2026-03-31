"""Shared EDI fixtures for converter tests.

This module provides common fixtures used across multiple converter test classes,
eliminating duplication and ensuring consistency.

Usage:
    from tests.fixtures.edi_samples import (
        sample_edi_content,
        sample_settings_dict,
        sample_parameters_dict,
        sample_upc_dict,
    )

Or in conftest.py:
    pytest_plugins = ["tests.fixtures.edi_samples"]
"""

import pytest


@pytest.fixture
def sample_edi_content():
    """Create sample EDI content with accurate field widths.

    A Record (33 chars): A + cust_vendor(6) + invoice_number(10) + invoice_date(6) + invoice_total(10)
    B Record (76 chars): B + upc(11) + description(25) + vendor_item(6) + unit_cost(6) + combo_code(2) +
                         unit_multiplier(6) + qty(5) + retail(5) + multi_pack(3) + parent_item(6)
    C Record (38 chars): C + charge_type(3) + description(25) + amount(9)

    Returns:
        String containing sample EDI content with one of each record type

    """
    # A record: A + VENDOR(6) + 0000000001(10) + 010125(6) + 0000100000(10) = 33 chars
    a_record = "AVENDOR00000000010101250000100000"
    # B record: B(1) + upc(11) + description(25) + vendor_item(6) + unit_cost(6) + combo_code(2) +
    #           unit_multiplier(6) + qty(5) + retail(5) + multi_pack(3) + parent_item(6) = 76 chars
    # vendor_item = "123456" which matches the upc_dict key
    # Description is exactly 25 chars: "Test Item Description    " (21 chars + 4 spaces)
    b_record = (
        "B01234567890Test Item Description    1234560001000100000100010991001000000"
    )
    # C record: C(1) + charge_type(3) + description(25) + amount(9) = 38 chars
    c_record = "CTABSales Tax                      000010000"
    return f"{a_record}\n{b_record}\n{c_record}\n"


@pytest.fixture
def sample_settings_dict():
    """Create sample settings dictionary.

    Returns:
        Dictionary with minimal AS400 connection settings

    """
    return {
        "as400_username": "testuser",
        "as400_password": "testpass",
        "as400_address": "test.as400.local",
    }


@pytest.fixture
def sample_parameters_dict():
    """Create sample parameters dictionary.

    Returns:
        Empty dictionary (can be extended by specific tests)

    """
    return {}


@pytest.fixture
def sample_upc_dict():
    """Create sample UPC lookup dictionary.

    Key is vendor_item (int), value is list of UPCs at different levels:
    - [0]: Category
    - [1]: UPC pack (11 digits)
    - [2]: UPC case (12 digits with check digit)
    - [3]: Additional UPC level
    - [4]: Additional UPC level

    Returns:
        Dictionary mapping item numbers to UPC lists

    """
    return {
        123456: [
            "1",
            "01234567890",
            "012345678901",
            "012345678902",
            "012345678903",
        ],
    }


@pytest.fixture
def sample_fintech_parameters():
    """Create sample parameters for Fintech converter.

    Returns:
        Dictionary with Fintech-specific parameters

    """
    return {
        "fintech_division_id": "123",
    }


@pytest.fixture
def edi_sample_factory():
    """Factory for creating custom EDI content.

    Returns:
        Factory function that creates EDI content with custom values

    Example:
        edi_content = edi_sample_factory(
            invoice_number="0000000002",
            vendor_item="654321",
            description="Custom Item"
        )

    """

    def _create_edi(
        vendor: str = "VENDOR",
        invoice_number: str = "0000000001",
        invoice_date: str = "010125",
        invoice_total: str = "0000100000",
        upc: str = "01234567890",
        description: str = "Test Item Description    ",
        vendor_item: str = "123456",
        unit_cost: str = "000100",
        combo_code: str = "01",
        unit_multiplier: str = "000001",
        qty: str = "00001",
        retail: str = "00991",
        multi_pack: str = "001",
        parent_item: str = "000000",
        charge_type: str = "TAB",
        charge_description: str = "Sales Tax                      ",
        charge_amount: str = "000010000",
    ):
        """Create custom EDI content.

        Args:
            vendor: 6-character vendor code
            invoice_number: 10-character invoice number
            invoice_date: 6-character date (MMDDYY)
            invoice_total: 10-character total amount
            upc: 11-character UPC
            description: 25-character description
            vendor_item: 6-character item number
            unit_cost: 6-character unit cost
            combo_code: 2-character combo code
            unit_multiplier: 6-character multiplier
            qty: 5-character quantity
            retail: 5-character retail price
            multi_pack: 3-character multi-pack
            parent_item: 6-character parent item
            charge_type: 3-character charge type
            charge_description: 25-character charge description
            charge_amount: 9-character charge amount

        Returns:
            EDI content string

        """
        a_record = f"A{vendor}{invoice_number}{invoice_date}{invoice_total}"
        b_record = (
            f"B{upc}{description}{vendor_item}{unit_cost}{combo_code}"
            f"{unit_multiplier}{qty}{retail}{multi_pack}{parent_item}"
        )
        c_record = f"C{charge_type}{charge_description}{charge_amount}"
        return f"{a_record}\n{b_record}\n{c_record}\n"

    return _create_edi

"""Tests for dispatch.converters.registry module."""

from dispatch.converters.registry import (
    ConverterMetadata,
    format_exists,
    get_all_converters,
    get_converter_by_name,
    get_display_name,
    get_format_names,
    get_module_name,
)


class TestConverterRegistry:
    """Tests for the central converter registry."""

    def test_get_all_converters_returns_list(self):
        """Test that get_all_converters returns a non-empty list."""
        converters = get_all_converters()
        assert isinstance(converters, list)
        assert len(converters) > 0

    def test_all_converters_are_metadata_objects(self):
        """Test that all returned items are ConverterMetadata instances."""
        converters = get_all_converters()
        for conv in converters:
            assert isinstance(conv, ConverterMetadata)

    def test_converter_metadata_has_required_fields(self):
        """Test that ConverterMetadata has all required fields."""
        converters = get_all_converters()
        for conv in converters:
            assert hasattr(conv, "format_name")
            assert hasattr(conv, "display_name")
            assert hasattr(conv, "module_name")
            assert conv.format_name
            assert conv.display_name
            assert conv.module_name

    def test_get_format_names_returns_strings(self):
        """Test that get_format_names returns format name strings."""
        names = get_format_names()
        assert isinstance(names, list)
        assert len(names) > 0
        for name in names:
            assert isinstance(name, str)

    def test_format_exists_for_known_formats(self):
        """Test that format_exists returns True for known formats."""
        # CSV should always exist
        assert format_exists("csv") is True
        # ScannerWare should exist
        assert format_exists("scannerware") is True

    def test_format_exists_for_unknown_format(self):
        """Test that format_exists returns False for unknown formats."""
        assert format_exists("nonexistent_format_xyz") is False

    def test_get_converter_by_name_valid(self):
        """Test get_converter_by_name with valid format."""
        conv = get_converter_by_name("csv")
        assert conv is not None
        assert conv.format_name == "csv"

    def test_get_converter_by_name_invalid(self):
        """Test get_converter_by_name with invalid format."""
        conv = get_converter_by_name("nonexistent_format_xyz")
        assert conv is None

    def test_get_display_name_valid(self):
        """Test get_display_name with valid format."""
        display = get_display_name("csv")
        # Display name matches what was defined in metadata
        assert display == "CSV"

    def test_get_display_name_invalid(self):
        """Test get_display_name with invalid format returns original."""
        display = get_display_name("nonexistent")
        assert display == "nonexistent"

    def test_get_module_name_valid(self):
        """Test get_module_name with valid format."""
        module = get_module_name("csv")
        assert module == "dispatch.converters.convert_to_csv"

    def test_get_module_name_invalid(self):
        """Test get_module_name with invalid format returns None."""
        module = get_module_name("nonexistent_format_xyz")
        assert module is None

    def test_converters_sorted_by_display_name(self):
        """Test that converters are sorted alphabetically by display_name."""
        converters = get_all_converters()
        display_names = [c.display_name for c in converters]
        assert display_names == sorted(display_names)

    def test_all_known_formats_present(self):
        """Test that all expected formats are present in registry."""
        converters = get_all_converters()
        format_names = {c.format_name for c in converters}

        # These formats should always be present
        expected = {
            "csv",
            "scannerware",
            "simplified_csv",
            "fintech",
            "jolley_custom",
            "stewarts_custom",
            "scansheet_type_a",
            "yellowdog_csv",
            "estore_einvoice",
            "estore_einvoice_generic",
            "tweaks",
        }

        for fmt in expected:
            assert fmt in format_names, f"Format {fmt} not found in registry"

    def test_metadata_consistency(self):
        """Test that metadata is consistent across all converters."""
        converters = get_all_converters()
        format_names = get_format_names()

        for conv in converters:
            # format_name should be in format_names
            assert conv.format_name in format_names

            # module_name should contain format_name
            assert conv.format_name in conv.module_name

            # display_name should be non-empty
            assert len(conv.display_name) > 0


class TestConverterRegistryIntegration:
    """Integration tests for registry with other modules.

    Phase 7b: ``test_registry_compatible_with_convertformat``
    asserted the registry covered every format listed in
    ``interface.models.folder_configuration.ConvertFormat``. With
    ``interface/`` gone, the test's only meaningful assertion
    target is gone too — there's no value in porting ``ConvertFormat``
    to a test-only stub. The remaining integration test
    (``test_registry_compatible_with_pipeline_converter``) still
    validates a contract with ``dispatch.pipeline.converter`` and
    stays.
    """

    def test_registry_compatible_with_pipeline_converter(self):
        """Test that registry formats match pipeline SUPPORTED_FORMATS."""
        from dispatch.pipeline.converter import SUPPORTED_FORMATS

        reg_formats = set(get_format_names())

        # SUPPORTED_FORMATS should be subset of registry
        assert set(SUPPORTED_FORMATS).issubset(reg_formats)

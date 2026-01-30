"""EDI Format Parser - Configuration-based EDI file parsing.

This module provides a flexible, configuration-driven approach to parsing
various EDI file formats. Instead of hardcoding field positions, formats
are defined in JSON configuration files.

Example:
    # Load a format
    parser = EDIFormatParser('default')

    # Parse a line
    record = parser.parse_line('A000001INV00001011221251000012345')
    # Returns: {'record_type': 'A', 'cust_vendor': '000001', ...}

    # Add a custom format
    parser = EDIFormatParser.from_file('/path/to/custom_format.json')
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any


class EDIFormatError(Exception):
    """Raised when there's an error with EDI format configuration or parsing."""

    pass


class EDIFormatParser:
    """Parser for EDI files based on JSON format configurations.

    This class loads format definitions from JSON files and provides
    methods to parse EDI records according to those definitions.

    Attributes:
        format_id: Unique identifier for this format
        format_name: Human-readable name
        format_version: Version string
        description: Format description
        encoding: File encoding (default: utf-8)
        record_types: Dictionary of record type definitions
        validation_rules: Optional validation rules
    """

    # Class-level registry of loaded formats
    _format_registry: Dict[str, "EDIFormatParser"] = {}

    def __init__(self, format_config: Dict[str, Any]) -> None:
        """Initialize parser with format configuration.

        Args:
            format_config: Dictionary containing format definition

        Raises:
            EDIFormatError: If configuration is invalid
        """
        self._validate_config(format_config)

        self.format_id = format_config["format_id"]
        self.format_name = format_config["format_name"]
        self.format_version = format_config["format_version"]
        self.description = format_config.get("description", "")
        self.encoding = format_config.get("encoding", "utf-8")
        self.record_types = format_config["record_types"]
        self.validation_rules = format_config.get("validation_rules", {})

        # Build quick lookup for record type identification
        self._record_type_map = {}
        for record_type, config in self.record_types.items():
            identifier = config["identifier"]
            pos = identifier["position"]
            length = identifier["length"]
            value = identifier["value"]
            self._record_type_map[value] = {
                "type": record_type,
                "position": pos,
                "length": length,
            }

    @classmethod
    def from_file(cls, filepath: str) -> "EDIFormatParser":
        """Load format definition from JSON file.

        Args:
            filepath: Path to JSON format definition file

        Returns:
            EDIFormatParser instance

        Raises:
            EDIFormatError: If file cannot be loaded or parsed
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                config = json.load(f)
            return cls(config)
        except FileNotFoundError:
            raise EDIFormatError(f"Format file not found: {filepath}")
        except json.JSONDecodeError as e:
            raise EDIFormatError(f"Invalid JSON in format file {filepath}: {e}")
        except Exception as e:
            raise EDIFormatError(f"Error loading format file {filepath}: {e}")

    @classmethod
    def load_format(
        cls, format_id: str, formats_dir: Optional[str] = None
    ) -> "EDIFormatParser":
        """Load format by ID from the formats directory.

        Args:
            format_id: Format identifier (e.g., 'default', 'custom')
            formats_dir: Optional custom formats directory path.
                        If None, uses ./edi_formats/

        Returns:
            EDIFormatParser instance

        Raises:
            EDIFormatError: If format cannot be found or loaded
        """
        # Check registry first
        if format_id in cls._format_registry:
            return cls._format_registry[format_id]

        # Determine formats directory
        if formats_dir is None:
            # Try to find edi_formats directory relative to this file
            module_dir = Path(__file__).parent
            formats_dir = module_dir / "edi_formats"

            # If not found, try current working directory
            if not formats_dir.exists():
                formats_dir = Path.cwd() / "edi_formats"
        else:
            formats_dir = Path(formats_dir)

        if not formats_dir.exists():
            raise EDIFormatError(f"Formats directory not found: {formats_dir}")

        # Try to find format file
        format_file = formats_dir / f"{format_id}_format.json"
        if not format_file.exists():
            # Try without _format suffix
            format_file = formats_dir / f"{format_id}.json"

        if not format_file.exists():
            raise EDIFormatError(
                f"Format '{format_id}' not found in {formats_dir}. "
                f"Expected {format_id}_format.json or {format_id}.json"
            )

        # Load and cache
        parser = cls.from_file(str(format_file))
        cls._format_registry[format_id] = parser
        return parser

    @classmethod
    def get_default_parser(cls) -> "EDIFormatParser":
        """Get the default format parser.

        Returns:
            EDIFormatParser for the default format
        """
        return cls.load_format("default")

    @classmethod
    def list_available_formats(
        cls, formats_dir: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """List all available format definitions.

        Args:
            formats_dir: Optional custom formats directory path

        Returns:
            List of dictionaries with format metadata:
            [{'id': 'default', 'name': 'Default Format', 'version': '1.0'}, ...]
        """
        if formats_dir is None:
            module_dir = Path(__file__).parent
            formats_dir = module_dir / "edi_formats"
            if not formats_dir.exists():
                formats_dir = Path.cwd() / "edi_formats"
        else:
            formats_dir = Path(formats_dir)

        if not formats_dir.exists():
            return []

        formats = []
        for file_path in formats_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                formats.append(
                    {
                        "id": config.get("format_id", file_path.stem),
                        "name": config.get("format_name", "Unknown"),
                        "version": config.get("format_version", "Unknown"),
                        "description": config.get("description", ""),
                    }
                )
            except Exception:
                # Skip invalid files
                continue

        return formats

    def _validate_config(self, config: Dict[str, Any]) -> None:
        """Validate format configuration structure.

        Args:
            config: Format configuration dictionary

        Raises:
            EDIFormatError: If configuration is invalid
        """
        required_fields = ["format_id", "format_name", "format_version", "record_types"]
        for field in required_fields:
            if field not in config:
                raise EDIFormatError(f"Missing required field: {field}")

        if not isinstance(config["record_types"], dict):
            raise EDIFormatError("record_types must be a dictionary")

        if not config["record_types"]:
            raise EDIFormatError("At least one record type must be defined")

        # Validate each record type
        for record_type, record_config in config["record_types"].items():
            if "identifier" not in record_config:
                raise EDIFormatError(f"Record type {record_type} missing identifier")
            if "fields" not in record_config:
                raise EDIFormatError(f"Record type {record_type} missing fields")

    def identify_record_type(self, line: str) -> Optional[str]:
        """Identify the record type from a line.

        Args:
            line: EDI record line

        Returns:
            Record type identifier (e.g., 'A', 'B', 'C') or None if not recognized
        """
        if not line:
            return None

        # Try to identify based on first character (most common case)
        first_char = line[0]
        if first_char in self._record_type_map:
            return self._record_type_map[first_char]["type"]

        return None

    def parse_line(self, line: str) -> Optional[Dict[str, str]]:
        """Parse an EDI record line into a dictionary of fields.

        Args:
            line: EDI record line to parse

        Returns:
            Dictionary with field names as keys and extracted values,
            or None if line is empty or record type not recognized

        Example:
            >>> parser.parse_line('A000001INV00001011221251000012345')
            {'record_type': 'A', 'cust_vendor': '000001',
             'invoice_number': 'INV0000101', ...}
        """
        if not line or line.strip() == "":
            return None

        # Identify record type
        record_type = self.identify_record_type(line)
        if record_type is None:
            return None

        # Get field definitions for this record type
        record_config = self.record_types[record_type]
        fields = record_config["fields"]

        # Extract each field
        result = {}
        for field_def in fields:
            field_name = field_def["name"]
            position = field_def["position"]
            length = field_def["length"]

            # Extract substring (handle lines that might be shorter than expected)
            end_pos = position + length
            if end_pos <= len(line):
                value = line[position:end_pos]
            else:
                # Line is shorter than expected, pad with spaces
                available = line[position:] if position < len(line) else ""
                value = available.ljust(length)

            result[field_name] = value

        return result

    def get_record_type_config(self, record_type: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific record type.

        Args:
            record_type: Record type identifier (e.g., 'A', 'B', 'C')

        Returns:
            Record type configuration dictionary or None if not found
        """
        return self.record_types.get(record_type)

    def get_field_definition(
        self, record_type: str, field_name: str
    ) -> Optional[Dict[str, Any]]:
        """Get definition for a specific field in a record type.

        Args:
            record_type: Record type identifier
            field_name: Name of the field

        Returns:
            Field definition dictionary or None if not found
        """
        record_config = self.get_record_type_config(record_type)
        if not record_config:
            return None

        for field_def in record_config["fields"]:
            if field_def["name"] == field_name:
                return field_def

        return None

    def validate_file_start(self, first_line: str) -> bool:
        """Validate that file starts with expected record type.

        Args:
            first_line: First line of the file

        Returns:
            True if file starts correctly, False otherwise
        """
        if "file_must_start_with" not in self.validation_rules:
            return True

        expected_start = self.validation_rules["file_must_start_with"]
        return first_line.startswith(expected_start)

    def get_allowed_record_types(self) -> List[str]:
        """Get list of allowed record type identifiers.

        Returns:
            List of record type identifiers (e.g., ['A', 'B', 'C'])
        """
        if "allowed_record_types" in self.validation_rules:
            return self.validation_rules["allowed_record_types"]
        return list(self._record_type_map.keys())


# Convenience function for backward compatibility
def capture_records_with_format(
    line: str, parser: Optional[EDIFormatParser] = None
) -> Optional[Dict[str, str]]:
    """Parse an EDI line using specified format parser.

    This is a convenience function that maintains compatibility with
    the original utils.capture_records() signature.

    Args:
        line: EDI record line to parse
        parser: EDIFormatParser instance. If None, uses default format.

    Returns:
        Dictionary with parsed fields or None
    """
    if parser is None:
        parser = EDIFormatParser.get_default_parser()

    return parser.parse_line(line)

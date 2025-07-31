# mtc_edi_validator.py

## Overview
Validates EDI files to ensure they conform to expected formats and record lengths.

## Key Components
- `check(input_file)`: Checks if the input file is a valid EDI file, returning False and the line number if invalid. Handles retries on file open errors and validates record types and lengths.

## Usage
Call `check` with the path to an EDI file. Returns a tuple (is_valid, line_number).

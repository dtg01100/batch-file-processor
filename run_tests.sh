#!/bin/bash
# Quick reference commands for running tests
# Copy these commands to quickly run different test suites

# Run all tests
pytest tests/ -v

# Run only smoke tests (fastest, ~0.06s)
pytest tests/ -v -m smoke

# Run only unit tests
pytest tests/ -v -m unit

# Run only integration tests
pytest tests/ -v -m integration

# Run tests with coverage report
pytest tests/ -v --cov=. --cov-report=html --cov-report=term

# Run specific test file
pytest tests/unit/test_utils.py -v

# Run specific test class
pytest tests/unit/test_utils.py::TestConvertToPrice -v

# Run specific test
pytest tests/unit/test_utils.py::TestConvertToPrice::test_basic_price_conversion -v

# Show all available tests without running them
pytest tests/ --collect-only

# Run with minimal output (quiet mode)
pytest tests/ -q

# Run and stop on first failure
pytest tests/ -x

# Run and show local variables on failure
pytest tests/ -l

# Run with detailed traceback
pytest tests/ --tb=long

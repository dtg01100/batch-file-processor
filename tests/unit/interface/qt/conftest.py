"""Shared fixtures and markers for Qt UI tests in the interface layer."""

import pytest

# Apply the `qt` marker to every test in this directory. Some test classes
# already declare it explicitly; the marker is additive.
pytestmark = pytest.mark.qt

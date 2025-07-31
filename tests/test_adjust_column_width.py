import pytest
from openpyxl import Workbook
from convert_to_scansheet_type_a import adjust_column_width
def test_adjust_column_width():
    # Create a workbook and add a worksheet
    wb = Workbook()
    ws = wb.active
    ws.title = "TestSheet"

    # Add data to the worksheet
    data = [
        ["Short", "A bit longer", "The longest string in this column"],
        ["123", "4567", "890123"],
        [None, "", "Test"]
    ]

    for row in data:
        ws.append(row)

    # Call the function to adjust column width
    adjust_column_width(ws)

    # Assert that column widths are adjusted (not default value)
    for col in ws.columns:
        column_letter = col[0].column_letter
        adjusted_width = ws.column_dimensions[column_letter].width
        assert adjusted_width > 0, f"Column {column_letter} width was not adjusted"

    print("Column widths adjusted successfully.")

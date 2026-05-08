"""CSV utility functions."""


def add_row(csv_writer, rowdict: dict) -> None:
    """Write a dictionary row to a CSV file.

    Args:
        csv_writer: A csv.writer object to write to.
        rowdict: A dictionary whose values will be written as a row.

    """
    csv_writer.writerow(rowdict.values())

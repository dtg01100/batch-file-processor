import os
from typing import Any


def export_processed_report(
    folder_id: int, output_folder: str, database_obj: Any
) -> None:
    """Export a processed files report for a specific folder.

    Args:
        folder_id: ID of the folder to export report for
        output_folder: Directory to save the report
        database_obj: Database object for data access
    """

    def avoid_duplicate_export_file(file_name: str, file_extension: str) -> str:
        """Returns a file path that does not already exist."""
        if not os.path.exists(file_name + file_extension):
            return file_name + file_extension
        else:
            i = 1
            while True:
                potential_file_path = file_name + " (" + str(i) + ")" + file_extension
                if not os.path.exists(potential_file_path):
                    return potential_file_path
                i += 1

    folder_dict = database_obj.folders_table.find_one(id=folder_id)
    if folder_dict is None:
        raise ValueError(f"Folder with id {folder_id} not found")
    folder_alias = folder_dict["alias"]

    export_file_path = avoid_duplicate_export_file(
        os.path.join(output_folder, folder_alias + " processed report"), ".csv"
    )
    with open(export_file_path, "w", encoding="utf-8") as processed_log:
        processed_log.write("File,Invoice Numbers,Date,Sent To\n")
        rows = list(database_obj.processed_files.find(folder_id=folder_id))
        for line in rows:
            processed_log.write(
                f"{line.get('file_name', '')},"
                f"{line.get('invoice_numbers', '')},"
                f"{line.get('processed_at', '')},"
                f"{line.get('sent_to', '')}"
                "\n"
            )

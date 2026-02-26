import os
from typing import Any


def export_processed_report(
    folder_id: int, 
    output_folder: str,
    database_obj: Any
) -> None:
    """Export a processed files report for a specific folder.

    Args:
        folder_id: ID of the folder to export report for
        output_folder: Directory to save the report
        database_obj: Database object for data access
    """

    def avoid_duplicate_export_file(file_name: str, file_extension: str) -> str:
        """Returns a file path that does not already exist.

        If the proposed file path exists, appends a number to the file name
        until an available file path is found.
        """
        print(f"Checking if {file_name + file_extension} exists")
        if not os.path.exists(file_name + file_extension):
            print(f"{file_name + file_extension} does not exist")
            return file_name + file_extension
        else:
            print(f"{file_name + file_extension} exists")
            i = 1
            while True:
                potential_file_path = (
                    file_name + " (" + str(i) + ")" + file_extension
                )
                print(f"Checking if {potential_file_path} exists")
                if not os.path.exists(potential_file_path):
                    print(f"{potential_file_path} does not exist")
                    return potential_file_path
                i += 1
                print(f"{potential_file_path} exists")

    folder_alias = database_obj.folders_table.find_one(id=folder_id)[
        "alias"
    ]

    export_file_path = avoid_duplicate_export_file(
        os.path.join(output_folder, folder_alias + " processed report"), ".csv"
    )
    print(f"Export file path will be: {export_file_path}")
    with open(export_file_path, "w", encoding="utf-8") as processed_log:
        processed_log.write(
            "File,Date,Copy Destination,FTP Destination,Email Destination\n"
        )
        for line in database_obj.processed_files.find(folder_id=folder_id):
            processed_log.write(
                f"{line['file_name']},"
                f"{line['sent_date_time'].strftime('%Y-%m-%d %H:%M:%S')},"
                f"{line['copy_destination']},"
                f"{line['ftp_destination']},"
                f"{line['email_destination']}"
                "\n"
            )
        print(
            f"Wrote {len(list(database_obj.processed_files.find(folder_id=folder_id)))} lines to {export_file_path}"
        )

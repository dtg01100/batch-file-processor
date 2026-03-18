import os
import shutil
import time

import utils
from batch_file_processor.structured_logging import get_logger, log_file_operation

logger = get_logger(__name__)


def do_backup(input_file):
    counter = 1
    proposed_backup_folder_path = os.path.join(
        os.path.dirname(os.path.abspath(input_file)), "backups"
    )
    if os.path.isdir(proposed_backup_folder_path) or not os.path.exists(
        proposed_backup_folder_path
    ):
        backup_folder_path = proposed_backup_folder_path
    else:
        while os.path.isfile(proposed_backup_folder_path + str(counter)):
            counter += 1
        backup_folder_path = proposed_backup_folder_path + str(counter)
    if not os.path.exists(backup_folder_path):
        os.mkdir(backup_folder_path)
    backup_path = os.path.join(
        backup_folder_path,
        os.path.basename(input_file)
        + ".bak"
        + "-"
        + str(time.ctime()).replace(":", "-"),
    )

    log_file_operation(
        logger,
        "copy",
        input_file,
        file_size=os.path.getsize(input_file) if os.path.exists(input_file) else None,
        file_type="backup",
    )

    shutil.copy(input_file, backup_path)

    log_file_operation(
        logger,
        "write",
        backup_path,
        file_size=os.path.getsize(backup_path) if os.path.exists(backup_path) else None,
        file_type="backup",
        success=True,
    )

    utils.do_clear_old_files(os.path.dirname(backup_path), 50)
    return backup_path

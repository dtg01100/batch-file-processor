# backup_increment.py

## Purpose
Provides a function to create timestamped backup copies of a file in a `backups` subdirectory, keeping only the 50 most recent backups.

## Main Function
- `do_backup(input_file)`: Creates a backup of the given file, manages backup folder creation, and prunes old backups.

## Usage
Call `do_backup(input_file)` with the path to the file you want to back up. The backup will be placed in a `backups` folder next to the original file.

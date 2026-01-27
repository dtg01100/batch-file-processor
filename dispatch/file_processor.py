import hashlib
import os
import time
from typing import List, Tuple, Dict, Any, Set
import concurrent.futures


class FileDiscoverer:
    """Discover files in directories for processing."""

    @staticmethod
    def discover_files(folder_path: str) -> List[str]:
        """
        Discover all files in a directory.
        
        Args:
            folder_path: Path to the folder to scan
            
        Returns:
            List of absolute file paths
        """
        if not os.path.isdir(folder_path):
            return []
            
        files = []
        for file_name in os.listdir(path=os.path.abspath(folder_path)):
            file_path = os.path.join(os.path.abspath(folder_path), file_name)
            if os.path.isfile(file_path):
                files.append(file_path)
        return files


class HashGenerator:
    """Generate MD5 checksums for files with retry logic."""

    @staticmethod
    def generate_file_hash(file_path: str, max_retries: int = 5) -> str:
        """
        Generate MD5 checksum for a file with retry logic.
        
        Args:
            file_path: Path to the file to hash
            max_retries: Maximum number of retry attempts
            
        Returns:
            MD5 checksum as hex string
            
        Raises:
            Exception: If file cannot be read after all retries
        """
        file_name = os.path.abspath(file_path)
        generated_file_checksum = None
        checksum_attempt = 1
        
        while generated_file_checksum is None:
            try:
                with open(file_name, 'rb') as f:
                    generated_file_checksum = hashlib.md5(f.read()).hexdigest()
            except Exception as error:
                if checksum_attempt <= max_retries:
                    time.sleep(checksum_attempt * checksum_attempt)
                    checksum_attempt += 1
                    print(f"retrying open {file_name} for md5sum")
                else:
                    print(f"error opening file for md5sum {error}")
                    raise
        
        return generated_file_checksum


class FileFilter:
    """Determine which files need to be processed."""

    @staticmethod
    def generate_match_lists(folder_temp_processed_files_list: List[Dict[str, Any]]) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]], Set[str]]:
        """
        Generate match lists from processed files data.
        
        Args:
            folder_temp_processed_files_list: List of processed files entries
            
        Returns:
            Tuple of (file_name_to_hash, hash_to_file_name, resend_flags)
        """
        folder_hash_dict = []
        folder_name_dict = []
        resend_flag_set = []

        for folder_entry in folder_temp_processed_files_list:
            folder_hash_dict.append((folder_entry['file_name'], folder_entry['file_checksum']))
            folder_name_dict.append((folder_entry['file_checksum'], folder_entry['file_name']))
            if folder_entry['resend_flag'] is True:
                resend_flag_set.append(folder_entry['file_checksum'])

        return folder_hash_dict, folder_name_dict, set(resend_flag_set)

    @staticmethod
    def should_send_file(file_hash: str, folder_name_dict: Dict[str, str], resend_flag_set: Set[str]) -> bool:
        """
        Determine if a file should be sent.
        
        Args:
            file_hash: MD5 checksum of the file
            folder_name_dict: Mapping of hash to file name
            resend_flag_set: Set of hashes with resend flag
            
        Returns:
            True if file should be sent, False otherwise
        """
        match_found = file_hash in folder_name_dict
        if not match_found:
            return True
        if file_hash in resend_flag_set:
            return True
        return False

    @staticmethod
    def process_files_for_sending(files: List[str], folder_temp_processed_files_list: List[Dict[str, Any]]) -> List[Tuple[int, str, str]]:
        """
        Process files to determine which should be sent.
        
        Args:
            files: List of files to check
            folder_temp_processed_files_list: List of processed files entries
            
        Returns:
            List of (index, filename, hash) for files to send
        """
        _, folder_name_dict, resend_flag_set = FileFilter.generate_match_lists(folder_temp_processed_files_list)
        
        filtered_files = []
        with concurrent.futures.ProcessPoolExecutor() as executor:
            file_hashes = list(executor.map(HashGenerator.generate_file_hash, files))
            
            for i, (file_path, file_hash) in enumerate(zip(files, file_hashes)):
                if FileFilter.should_send_file(file_hash, dict(folder_name_dict), resend_flag_set):
                    filtered_files.append((i, os.path.basename(file_path), file_hash))
        
        return filtered_files


# Backward compatibility - standalone functions that wrap the class methods
def generate_match_lists(folder_temp_processed_files_list: List[Dict[str, Any]]) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]], Set[str]]:
    """
    Generate match lists from processed files data.
    
    Args:
        folder_temp_processed_files_list: List of processed files entries
        
    Returns:
        Tuple of (file_name_to_hash, hash_to_file_name, resend_flags)
    """
    return FileFilter.generate_match_lists(folder_temp_processed_files_list)


def generate_file_hash(source_file_struct: Tuple) -> Tuple[str, str, int, bool]:
    """
    Generate MD5 checksum for a file and determine if it should be sent.
    
    Args:
        source_file_struct: Tuple of (file_path, index, temp_processed_files_list, 
                                      folder_hash_dict, folder_name_dict, resend_flag_set)
        
    Returns:
        Tuple of (file_name, file_hash, index_number, send_file)
    """
    source_file_path, index_number, temp_processed_files_list, \
        folder_hash_dict, folder_name_dict, resend_flag_set = source_file_struct
    
    file_name = os.path.abspath(source_file_path)
    generated_file_checksum = HashGenerator.generate_file_hash(file_name)
    
    match_found = generated_file_checksum in folder_name_dict
    send_file = False
    if not match_found:
        send_file = True
    if generated_file_checksum in resend_flag_set:
        send_file = True
    
    return file_name, generated_file_checksum, index_number, send_file

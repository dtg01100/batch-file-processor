import os
import importlib
import tempfile
import shutil
import re
import datetime
import utils
import edi_tweaks
from typing import List, Tuple, Optional


class EDISplitter:
    """Handles EDI file splitting."""

    @staticmethod
    def split_edi(
        input_file: str, scratch_folder: str, parameters_dict: dict
    ) -> List[Tuple[str, str, str]]:
        """
        Split an EDI file into multiple files.

        Args:
            input_file: Path to the EDI file to split
            scratch_folder: Temporary folder for processing
            parameters_dict: Configuration parameters

        Returns:
            List of (file_path, filename_prefix, filename_suffix) for split files
        """
        try:
            split_edi_list = utils.do_split_edi(
                input_file, scratch_folder, parameters_dict
            )
            if len(split_edi_list) > 1:
                print(f"edi file split into {len(split_edi_list)} files")
            return split_edi_list
        except Exception as process_error:
            print(process_error)
            return [(input_file, "", "")]


class EDIConverter:
    """Manages EDI format conversion."""

    @staticmethod
    def convert_edi(
        input_file: str,
        output_file: str,
        settings: dict,
        parameters_dict: dict,
        upc_dict: dict,
    ) -> str:
        """
        Convert EDI file to specified format.

        Args:
            input_file: Path to the input EDI file
            output_file: Path to save the converted file
            settings: Application settings
            parameters_dict: Configuration parameters
            upc_dict: UPC dictionary for conversion

        Returns:
            Path to the converted file
        """
        module_name = "convert_to_" + parameters_dict[
            "convert_to_format"
        ].lower().replace(" ", "_").replace("-", "_")
        module = importlib.import_module(module_name)
        print(f"Converting {input_file} to {parameters_dict['convert_to_format']}")
        return module.edi_convert(
            input_file, output_file, settings, parameters_dict, upc_dict
        )


class EDITweaker:
    """Applies EDI tweaks."""

    @staticmethod
    def tweak_edi(
        input_file: str,
        output_file: str,
        settings: dict,
        parameters_dict: dict,
        upc_dict: dict,
    ) -> str:
        """
        Apply EDI tweaks to a file.

        Args:
            input_file: Path to the input EDI file
            output_file: Path to save the tweaked file
            settings: Application settings
            parameters_dict: Configuration parameters
            upc_dict: UPC dictionary for tweaking

        Returns:
            Path to the tweaked file
        """
        print(f"Applying tweaks to {input_file}")
        return edi_tweaks.edi_tweak(
            input_file, output_file, settings, parameters_dict, upc_dict
        )


class EDIProcessor:
    """Coordinates EDI processing operations."""

    @staticmethod
    def process_edi(
        input_file: str,
        parameters_dict: dict,
        settings: dict,
        upc_dict: dict,
        scratch_folder: str,
    ) -> List[Tuple[str, str, str]]:
        """
        Process EDI file according to parameters.

        Args:
            input_file: Path to the EDI file
            parameters_dict: Configuration parameters
            settings: Application settings
            upc_dict: UPC dictionary for processing
            scratch_folder: Temporary folder for processing

        Returns:
            List of (file_path, filename_prefix, filename_suffix) for processed files
        """
        processed_files = [(input_file, "", "")]

        # Split EDI file if configured
        if parameters_dict["split_edi"]:
            processed_files = EDISplitter.split_edi(
                input_file, scratch_folder, parameters_dict
            )

        # Process each split file
        final_files = []
        for file_path, prefix, suffix in processed_files:
            temp_file = EDIProcessor._process_single_file(
                file_path, parameters_dict, settings, upc_dict, scratch_folder
            )
            final_files.append((temp_file, prefix, suffix))

        return final_files

    @staticmethod
    def _process_single_file(
        input_file: str,
        parameters_dict: dict,
        settings: dict,
        upc_dict: dict,
        scratch_folder: str,
    ) -> str:
        """
        Process a single EDI file.

        Args:
            input_file: Path to the EDI file
            parameters_dict: Configuration parameters
            settings: Application settings
            upc_dict: UPC dictionary for processing
            scratch_folder: Temporary folder for processing

        Returns:
            Path to the processed file
        """
        temp_file = os.path.join(scratch_folder, os.path.basename(input_file))
        if os.path.normpath(input_file) != os.path.normpath(temp_file):
            shutil.copyfile(input_file, temp_file)

        # Convert EDI if configured
        if parameters_dict["process_edi"] == "True":
            converted_file = os.path.join(
                scratch_folder, f"converted_{os.path.basename(temp_file)}"
            )
            temp_file = EDIConverter.convert_edi(
                temp_file, converted_file, settings, parameters_dict, upc_dict
            )

        # Apply tweaks if configured
        if parameters_dict["tweak_edi"] is True:
            tweaked_file = os.path.join(
                scratch_folder, f"tweaked_{os.path.basename(temp_file)}"
            )
            temp_file = EDITweaker.tweak_edi(
                temp_file, tweaked_file, settings, parameters_dict, upc_dict
            )

        return temp_file


class FileNamer:
    """Handles file renaming according to parameters."""

    @staticmethod
    def generate_output_filename(
        input_filename: str,
        parameters_dict: dict,
        filename_prefix: str = "",
        filename_suffix: str = "",
    ) -> str:
        """
        Generate output filename based on parameters.

        Args:
            input_filename: Original filename
            parameters_dict: Configuration parameters
            filename_prefix: Prefix to add to filename
            filename_suffix: Suffix to add to filename

        Returns:
            Generated filename
        """
        rename_file = os.path.basename(input_filename)
        date_time = datetime.datetime.strftime(datetime.datetime.now(), "%Y%m%d")

        if parameters_dict["rename_file"].strip() != "":
            rename_file = "".join(
                [
                    filename_prefix,
                    parameters_dict["rename_file"]
                    .strip()
                    .replace("%datetime%", date_time),
                    ".",
                    os.path.basename(input_filename).split(".")[-1],
                    filename_suffix,
                ]
            )

        stripped_filename = re.sub("[^A-Za-z0-9.\\-_ ]+", "", rename_file)
        return stripped_filename

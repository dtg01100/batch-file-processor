"""EDI Splitter Step for the dispatch pipeline.

This module provides a pipeline step for EDI file splitting,
wrapping the existing EDISplitter with pipeline integration.
"""

import os
from dataclasses import dataclass, field
from typing import Optional, Protocol, runtime_checkable, Any

from core.edi.edi_splitter import EDISplitter, SplitConfig, SplitResult, FilesystemProtocol
from dispatch.interfaces import FileSystemInterface


@dataclass
class SplitterResult:
    """Result of EDI split operation.
    
    Attributes:
        files: List of tuples (output_path, prefix, suffix)
        was_split: True if file was split into multiple files
        was_filtered: True if category filtering was applied
        skipped_invoices: Number of invoices skipped due to filtering
        errors: List of error messages
    """
    files: list[tuple[str, str, str]] = field(default_factory=list)
    was_split: bool = False
    was_filtered: bool = False
    skipped_invoices: int = 0
    errors: list[str] = field(default_factory=list)


@runtime_checkable
class SplitterInterface(Protocol):
    """Protocol for splitter step implementations."""
    
    def split(self, input_path: str, output_dir: str, params: dict, upc_dict: dict) -> SplitterResult:
        """Split an EDI file.
        
        Args:
            input_path: Path to the input EDI file
            output_dir: Directory for output files
            params: Folder parameters dictionary
            upc_dict: UPC dictionary for category filtering
            
        Returns:
            SplitterResult with split outcome
        """
        ...


@runtime_checkable
class CreditDetectorProtocol(Protocol):
    """Protocol for credit memo detection."""
    
    def detect(self, file_path: str) -> bool:
        """Detect if a file is a credit memo.
        
        Args:
            file_path: Path to the EDI file
            
        Returns:
            True if the file is a credit memo
        """
        ...


class DefaultCreditDetector:
    """Default credit detector using utils.detect_invoice_is_credit."""
    
    def detect(self, file_path: str) -> bool:
        """Detect if a file is a credit memo.
        
        Args:
            file_path: Path to the EDI file
            
        Returns:
            True if the file is a credit memo
        """
        import utils
        return utils.detect_invoice_is_credit(file_path)


class MockSplitter:
    """Mock splitter for testing purposes.
    
    This splitter can be configured to return specific results
    and allows inspection of split calls.
    
    Attributes:
        result: The result to return from split()
        call_count: Number of times split was called
        last_input_path: Last input path passed to split
        last_output_dir: Last output directory passed to split
        last_params: Last params dict passed to split
        last_upc_dict: Last upc_dict passed to split
    """
    
    def __init__(
        self,
        result: Optional[SplitterResult] = None,
        files: Optional[list[tuple[str, str, str]]] = None,
        was_split: bool = False,
        was_filtered: bool = False,
        skipped_invoices: int = 0,
        errors: Optional[list[str]] = None
    ):
        """Initialize the mock splitter.
        
        Args:
            result: Complete result to return (overrides other params)
            files: List of file tuples to return
            was_split: Whether to report splitting occurred
            was_filtered: Whether to report filtering occurred
            skipped_invoices: Number of skipped invoices to report
            errors: List of error messages
        """
        if result is not None:
            self._result = result
        else:
            self._result = SplitterResult(
                files=files or [],
                was_split=was_split,
                was_filtered=was_filtered,
                skipped_invoices=skipped_invoices,
                errors=errors or []
            )
        self.call_count: int = 0
        self.last_input_path: Optional[str] = None
        self.last_output_dir: Optional[str] = None
        self.last_params: Optional[dict] = None
        self.last_upc_dict: Optional[dict] = None
    
    def split(self, input_path: str, output_dir: str, params: dict, upc_dict: dict) -> SplitterResult:
        """Mock split method.
        
        Args:
            input_path: Path to the input EDI file
            output_dir: Directory for output files
            params: Folder parameters dictionary
            upc_dict: UPC dictionary for category filtering
            
        Returns:
            The configured SplitterResult
        """
        self.call_count += 1
        self.last_input_path = input_path
        self.last_output_dir = output_dir
        self.last_params = params
        self.last_upc_dict = upc_dict
        return self._result
    
    def reset(self) -> None:
        """Reset the mock state."""
        self.call_count = 0
        self.last_input_path = None
        self.last_output_dir = None
        self.last_params = None
        self.last_upc_dict = None
    
    def set_result(self, result: SplitterResult) -> None:
        """Set the result to return.
        
        Args:
            result: The SplitterResult to return
        """
        self._result = result


class FilesystemAdapter:
    """Adapts FileSystemInterface to FilesystemProtocol."""
    
    def __init__(self, fs: FileSystemInterface):
        """Initialize adapter with file system interface.
        
        Args:
            fs: FileSystemInterface implementation
        """
        self._fs = fs
    
    def read_file(self, path: str, encoding: str = "utf-8") -> str:
        """Read file contents."""
        return self._fs.read_file_text(path, encoding)
    
    def write_file(self, path: str, content: str, encoding: str = "utf-8") -> None:
        """Write content to file."""
        self._fs.write_file_text(path, content, encoding)
    
    def write_binary(self, path: str, content: bytes) -> None:
        """Write binary content to file."""
        self._fs.write_file(path, content)
    
    def file_exists(self, path: str) -> bool:
        """Check if file exists."""
        return self._fs.file_exists(path)
    
    def directory_exists(self, path: str) -> bool:
        """Check if directory exists."""
        return self._fs.dir_exists(path)
    
    def create_directory(self, path: str) -> None:
        """Create directory if it doesn't exist."""
        self._fs.makedirs(path)
    
    def remove_file(self, path: str) -> None:
        """Remove a file."""
        self._fs.remove_file(path)
    
    def list_files(self, path: str) -> list[str]:
        """List files in directory."""
        return self._fs.list_files(path)


class EDISplitterStep:
    """EDI splitter step for the dispatch pipeline.
    
    This class wraps the EDISplitter and integrates with the error handler
    for pipeline-based processing.
    
    Attributes:
        splitter: EDI splitter instance
        error_handler: Optional error handler for recording errors
        file_system: Optional file system interface
        credit_detector: Credit memo detector
    """
    
    def __init__(
        self,
        splitter: Optional[EDISplitter] = None,
        error_handler: Optional[Any] = None,
        file_system: Optional[FileSystemInterface] = None,
        credit_detector: Optional[CreditDetectorProtocol] = None
    ):
        """Initialize the splitter step.
        
        Args:
            splitter: EDI splitter instance (creates new one if None)
            error_handler: Optional error handler for recording errors
            file_system: Optional file system interface
            credit_detector: Optional credit memo detector
        """
        self._file_system = file_system
        self._error_handler = error_handler
        self._credit_detector = credit_detector or DefaultCreditDetector()
        
        if splitter is not None:
            self._splitter = splitter
        elif file_system is not None:
            adapted_fs = FilesystemAdapter(file_system)
            self._splitter = EDISplitter(adapted_fs)
        else:
            from core.edi.edi_splitter import RealFilesystem
            self._splitter = EDISplitter(RealFilesystem())
    
    def split(self, input_path: str, output_dir: str, params: dict, upc_dict: dict) -> SplitterResult:
        """Split an EDI file based on parameters.
        
        Args:
            input_path: Path to the input EDI file
            output_dir: Directory for output files
            params: Folder parameters dictionary with settings:
                - split_edi: bool to enable splitting
                - split_edi_include_invoices: include regular invoices
                - split_edi_include_credits: include credit memos
                - split_edi_filter_categories: categories to filter
                - split_edi_filter_mode: "include" or "exclude"
                - prepend_date_files: prepend date to filenames
            upc_dict: UPC dictionary for category filtering
            
        Returns:
            SplitterResult with split outcome
        """
        errors: list[str] = []
        
        split_edi = params.get('split_edi', False)
        if isinstance(split_edi, str):
            split_edi = split_edi.lower() == 'true'
        
        filter_categories = params.get('split_edi_filter_categories', 'ALL')
        filter_mode = params.get('split_edi_filter_mode', 'include')
        prepend_date = params.get('prepend_date_files', False)
        if isinstance(prepend_date, str):
            prepend_date = prepend_date.lower() == 'true'
        
        include_invoices = params.get('split_edi_include_invoices', True)
        if isinstance(include_invoices, int):
            include_invoices = include_invoices != 0
        elif isinstance(include_invoices, str):
            include_invoices = include_invoices.lower() not in ('0', 'false')
        
        include_credits = params.get('split_edi_include_credits', True)
        if isinstance(include_credits, int):
            include_credits = include_credits != 0
        elif isinstance(include_credits, str):
            include_credits = include_credits.lower() not in ('0', 'false')
        
        if split_edi:
            return self._do_split(
                input_path, output_dir, params, upc_dict,
                filter_categories, filter_mode, prepend_date,
                include_invoices, include_credits, errors
            )
        else:
            return self._filter_without_split(
                input_path, output_dir, upc_dict,
                filter_categories, filter_mode, errors
            )
    
    def _do_split(
        self,
        input_path: str,
        output_dir: str,
        params: dict,
        upc_dict: dict,
        filter_categories: str,
        filter_mode: str,
        prepend_date: bool,
        include_invoices: bool,
        include_credits: bool,
        errors: list[str]
    ) -> SplitterResult:
        """Perform EDI splitting.
        
        Args:
            input_path: Path to input file
            output_dir: Output directory
            params: Parameters dict
            upc_dict: UPC dictionary
            filter_categories: Categories to filter
            filter_mode: Filter mode
            prepend_date: Whether to prepend date
            include_invoices: Include invoice files
            include_credits: Include credit memo files
            errors: Error list to append to
            
        Returns:
            SplitterResult
        """
        try:
            config = SplitConfig(
                output_directory=output_dir,
                prepend_date=prepend_date
            )
            
            split_result = self._splitter.do_split_edi(
                input_path,
                config,
                upc_dict=upc_dict,
                filter_categories=filter_categories,
                filter_mode=filter_mode
            )
            
            was_filtered = filter_categories != 'ALL'
            
            if len(split_result.output_files) > 1:
                filtered_files = self._filter_by_credit_invoice(
                    split_result.output_files,
                    include_invoices,
                    include_credits
                )
                
                return SplitterResult(
                    files=filtered_files,
                    was_split=True,
                    was_filtered=was_filtered,
                    skipped_invoices=split_result.skipped_invoices,
                    errors=errors
                )
            else:
                return SplitterResult(
                    files=[(input_path, "", "")],
                    was_split=False,
                    was_filtered=was_filtered,
                    skipped_invoices=split_result.skipped_invoices,
                    errors=errors
                )
                
        except ValueError as e:
            error_msg = f"No valid invoices after filtering: {e}"
            errors.append(error_msg)
            self._record_error(input_path, error_msg)
            return SplitterResult(
                files=[(input_path, "", "")],
                was_split=False,
                was_filtered=False,
                skipped_invoices=0,
                errors=errors
            )
        except Exception as e:
            error_msg = f"Split failed: {e}"
            errors.append(error_msg)
            self._record_error(input_path, error_msg)
            return SplitterResult(
                files=[(input_path, "", "")],
                was_split=False,
                was_filtered=False,
                skipped_invoices=0,
                errors=errors
            )
    
    def _filter_without_split(
        self,
        input_path: str,
        output_dir: str,
        upc_dict: dict,
        filter_categories: str,
        filter_mode: str,
        errors: list[str]
    ) -> SplitterResult:
        """Apply category filtering without splitting.
        
        Args:
            input_path: Path to input file
            output_dir: Output directory
            upc_dict: UPC dictionary
            filter_categories: Categories to filter
            filter_mode: Filter mode
            errors: Error list to append to
            
        Returns:
            SplitterResult
        """
        was_filtered = False
        output_path = input_path
        
        if filter_categories != 'ALL':
            try:
                import utils
                filtered_output = os.path.join(output_dir, "filtered_" + os.path.basename(input_path))
                was_filtered = utils.filter_edi_file_by_category(
                    input_path, filtered_output, upc_dict, filter_categories, filter_mode
                )
                if was_filtered:
                    output_path = filtered_output
            except Exception as e:
                error_msg = f"Category filtering failed: {e}"
                errors.append(error_msg)
                self._record_error(input_path, error_msg)
        
        return SplitterResult(
            files=[(output_path, "", "")],
            was_split=False,
            was_filtered=was_filtered,
            skipped_invoices=0,
            errors=errors
        )
    
    def _filter_by_credit_invoice(
        self,
        files: list[tuple[str, str, str]],
        include_invoices: bool,
        include_credits: bool
    ) -> list[tuple[str, str, str]]:
        """Filter files based on whether they are invoices or credits.
        
        Args:
            files: List of (path, prefix, suffix) tuples
            include_invoices: Whether to include invoices
            include_credits: Whether to include credits
            
        Returns:
            Filtered list of file tuples
        """
        if include_invoices and include_credits:
            return files
        
        filtered_files = []
        for file_path, prefix, suffix in files:
            try:
                is_credit = self._credit_detector.detect(file_path)
                
                if is_credit and include_credits:
                    filtered_files.append((file_path, prefix, suffix))
                elif not is_credit and include_invoices:
                    filtered_files.append((file_path, prefix, suffix))
            except Exception:
                filtered_files.append((file_path, prefix, suffix))
        
        return filtered_files
    
    def _record_error(self, filename: str, error_msg: str) -> None:
        """Record an error to the error handler.
        
        Args:
            filename: Filename being processed
            error_msg: Error message
        """
        if self._error_handler is None:
            return
        
        self._error_handler.record_error(
            folder="",
            filename=filename,
            error=Exception(error_msg),
            context={'source': 'EDISplitterStep'},
            error_source="EDISplitter"
        )
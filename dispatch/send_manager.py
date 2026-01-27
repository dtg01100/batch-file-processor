import importlib
from typing import List, Dict, Any, Tuple, Optional


class BackendFactory:
    """Factory for creating backend instances."""
    
    @staticmethod
    def get_backend(backend_name: str):
        """
        Get a backend module by name.
        
        Args:
            backend_name: Name of the backend (copy, ftp, email)
            
        Returns:
            Backend module
            
        Raises:
            ImportError: If backend module not found
        """
        module_name = f"{backend_name}_backend"
        try:
            return importlib.import_module(module_name)
        except ImportError as e:
            raise ImportError(f"Backend '{backend_name}' not found: {e}")


class SendResult:
    """Encapsulates the result of a file sending operation."""
    
    def __init__(self, 
                 success: bool, 
                 backend_name: str, 
                 destination: str,
                 error_message: str = "",
                 details: Dict[str, Any] = None):
        self.success = success
        self.backend_name = backend_name
        self.destination = destination
        self.error_message = error_message
        self.details = details or {}


class SendManager:
    """Manages file sending through configured backends."""
    
    BACKEND_CONFIG = {
        'copy': ('copy_backend', 'copy_to_directory', 'Copy Backend'),
        'ftp': ('ftp_backend', 'ftp_server', 'FTP Backend'),
        'email': ('email_backend', 'email_to', 'Email Backend')
    }
    
    def __init__(self):
        self.results = []
    
    def send_file(self, file_path: str, parameters_dict: dict, settings: dict) -> List[SendResult]:
        """
        Send a file through all configured backends.
        
        Args:
            file_path: Path to the file to send
            parameters_dict: Configuration parameters
            settings: Application settings
            
        Returns:
            List of SendResult objects for each backend
        """
        results = []
        
        for backend_type, (backend_name, dir_setting, backend_name_print) in self.BACKEND_CONFIG.items():
            if parameters_dict[f'process_backend_{backend_type}'] is True:
                try:
                    destination = parameters_dict[dir_setting]
                    print(f"sending {file_path} to {destination} with {backend_name_print}")
                    
                    # Get and call the backend
                    backend = BackendFactory.get_backend(backend_type)
                    backend.do(parameters_dict, settings, file_path)
                    
                    results.append(SendResult(
                        success=True,
                        backend_name=backend_name_print,
                        destination=destination
                    ))
                except Exception as process_error:
                    print(str(process_error))
                    results.append(SendResult(
                        success=False,
                        backend_name=backend_name_print,
                        destination=parameters_dict.get(dir_setting, 'Unknown'),
                        error_message=str(process_error)
                    ))
        
        return results
    
    @staticmethod
    def has_successful_sends(results: List[SendResult]) -> bool:
        """
        Check if any send operations were successful.
        
        Args:
            results: List of SendResult objects
            
        Returns:
            True if any send was successful, False otherwise
        """
        return any(result.success for result in results)
    
    @staticmethod
    def get_error_messages(results: List[SendResult]) -> List[str]:
        """
        Get all error messages from failed send operations.
        
        Args:
            results: List of SendResult objects
            
        Returns:
            List of error messages
        """
        return [result.error_message for result in results if not result.success]

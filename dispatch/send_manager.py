"""Send Manager component for dispatch processing.

This module manages sending files to multiple backends,
using dependency injection for testability.
"""

import importlib
from typing import Optional, Protocol, runtime_checkable

from dispatch.interfaces import BackendInterface


class SendManager:
    """Manages sending files to multiple backends.
    
    This class coordinates file sending across multiple backends,
    handling errors and tracking results.
    
    Attributes:
        backends: Dictionary mapping backend names to backend instances
        results: Dictionary tracking send results per backend
    """
    
    # Default backend configuration mapping
    DEFAULT_BACKENDS = {
        'copy': {
            'module': 'copy_backend',
            'setting': 'copy_to_directory',
            'display_name': 'Copy Backend',
            'enabled_key': 'process_backend_copy'
        },
        'ftp': {
            'module': 'ftp_backend',
            'setting': 'ftp_server',
            'display_name': 'FTP Backend',
            'enabled_key': 'process_backend_ftp'
        },
        'email': {
            'module': 'email_backend',
            'setting': 'email_to',
            'display_name': 'Email Backend',
            'enabled_key': 'process_backend_email'
        }
    }
    
    def __init__(
        self,
        backends: Optional[dict[str, BackendInterface]] = None,
        use_default_backends: bool = True
    ):
        """Initialize the send manager.
        
        Args:
            backends: Optional dictionary of backend instances
            use_default_backends: If True, use default backend modules when
                no backend instance is provided for a name
        """
        self.backends = backends or {}
        self.use_default_backends = use_default_backends
        self.results: dict[str, bool] = {}
    
    def send_all(
        self,
        enabled_backends: set[str],
        file_path: str,
        params: dict,
        settings: dict
    ) -> dict[str, bool]:
        """Send a file to all enabled backends.
        
        Args:
            enabled_backends: Set of backend names to send to
            file_path: Path to the file to send
            params: Folder-specific parameters
            settings: Global application settings
            
        Returns:
            Dictionary mapping backend names to success status
        """
        self.results = {}
        
        for backend_name in enabled_backends:
            try:
                success = self._send_to_backend(
                    backend_name, file_path, params, settings
                )
                self.results[backend_name] = success
            except Exception as e:
                self.results[backend_name] = False
                # Re-raise to let caller handle
                raise
        
        return self.results
    
    def _send_to_backend(
        self,
        backend_name: str,
        file_path: str,
        params: dict,
        settings: dict
    ) -> bool:
        """Send a file to a specific backend.
        
        Args:
            backend_name: Name of the backend to use
            file_path: Path to the file to send
            params: Folder-specific parameters
            settings: Global application settings
            
        Returns:
            True if send was successful
            
        Raises:
            Exception: If backend is not found or send fails
        """
        # Check if we have an injected backend instance
        if backend_name in self.backends:
            backend = self.backends[backend_name]
            backend.send(params, settings, file_path)
            return True
        
        # Fall back to default module-based backend
        if self.use_default_backends and backend_name in self.DEFAULT_BACKENDS:
            return self._send_via_module(backend_name, file_path, params, settings)
        
        raise ValueError(f"Unknown backend: {backend_name}")
    
    def _send_via_module(
        self,
        backend_name: str,
        file_path: str,
        params: dict,
        settings: dict
    ) -> bool:
        """Send a file using a module-based backend.
        
        This method provides backward compatibility with the existing
        backend modules (copy_backend, ftp_backend, email_backend).
        
        Args:
            backend_name: Name of the backend (copy, ftp, email)
            file_path: Path to the file to send
            params: Folder-specific parameters
            settings: Global application settings
            
        Returns:
            True if send was successful
        """
        config = self.DEFAULT_BACKENDS.get(backend_name)
        if not config:
            raise ValueError(f"Unknown backend: {backend_name}")
        
        # Check if backend is enabled in params
        if not params.get(config['enabled_key'], False):
            return False
        
        # Import and call the backend module
        module = importlib.import_module(config['module'])
        module.do(params, settings, file_path)
        
        return True
    
    def get_enabled_backends(self, params: dict) -> set[str]:
        """Get the set of enabled backends from parameters.
        
        Args:
            params: Folder-specific parameters
            
        Returns:
            Set of enabled backend names
        """
        enabled = set()
        
        for backend_name, config in self.DEFAULT_BACKENDS.items():
            if params.get(config['enabled_key'], False):
                enabled.add(backend_name)
        
        return enabled
    
    def validate_backend_config(self, params: dict) -> list[str]:
        """Validate backend configuration.
        
        Args:
            params: Folder-specific parameters
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        for backend_name, config in self.DEFAULT_BACKENDS.items():
            if params.get(config['enabled_key'], False):
                # Check if required setting is present
                setting_value = params.get(config['setting'])
                if not setting_value:
                    errors.append(
                        f"{config['display_name']} is enabled but "
                        f"{config['setting']} is not configured"
                    )
        
        return errors
    
    def get_results(self) -> dict[str, bool]:
        """Get the results of the last send operation.
        
        Returns:
            Dictionary mapping backend names to success status
        """
        return self.results.copy()
    
    def clear_results(self) -> None:
        """Clear the results of the last send operation."""
        self.results = {}


class MockBackend:
    """Mock backend for testing purposes.
    
    This backend records all send calls for verification in tests.
    """
    
    def __init__(self, should_succeed: bool = True):
        """Initialize the mock backend.
        
        Args:
            should_succeed: If True, send() will succeed; if False, it will raise
        """
        self.should_succeed = should_succeed
        self.send_calls: list[tuple[dict, dict, str]] = []
        self.validate_calls: list[dict] = []
    
    def send(self, params: dict, settings: dict, filename: str) -> None:
        """Record the send call and optionally raise an error.
        
        Args:
            params: Folder-specific parameters
            settings: Global application settings
            filename: Path to the file to send
            
        Raises:
            Exception: If should_succeed is False
        """
        self.send_calls.append((params.copy(), settings.copy(), filename))
        
        if not self.should_succeed:
            raise Exception("Mock backend failure")
    
    def validate(self, params: dict) -> list[str]:
        """Validate backend configuration.
        
        Args:
            params: Folder-specific parameters
            
        Returns:
            Empty list if should_succeed, otherwise list with error
        """
        self.validate_calls.append(params.copy())
        
        if not self.should_succeed:
            return ["Mock backend validation error"]
        return []
    
    def get_name(self) -> str:
        """Get the backend name."""
        return "Mock Backend"
    
    def reset(self) -> None:
        """Reset the recorded calls."""
        self.send_calls = []
        self.validate_calls = []

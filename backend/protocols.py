"""Protocol interfaces for backend abstractions.

This module defines Protocol interfaces for external client dependencies,
enabling dependency injection and testability for send backends.
"""

from typing import Protocol, runtime_checkable, Optional, Any


@runtime_checkable
class FTPClientProtocol(Protocol):
    """Protocol for FTP client abstraction.
    
    Implementations should wrap ftplib.FTP or ftplib.FTP_TLS
    to enable testing without actual FTP connections.
    """
    
    def connect(self, host: str, port: int, timeout: Optional[float] = None) -> None:
        """Connect to FTP server.
        
        Args:
            host: Server hostname or IP address
            port: Server port number
            timeout: Optional connection timeout in seconds
        """
        ...
    
    def login(self, user: str, password: str) -> None:
        """Authenticate with FTP server.
        
        Args:
            user: Username for authentication
            password: Password for authentication
        """
        ...
    
    def cwd(self, directory: str) -> None:
        """Change working directory on FTP server.
        
        Args:
            directory: Directory path to change to
        """
        ...
    
    def storbinary(self, cmd: str, fp: Any, blocksize: int = 8192) -> None:
        """Store a file in binary mode.
        
        Args:
            cmd: FTP command (e.g., "STOR filename")
            fp: File-like object to read data from
            blocksize: Block size for transfer
        """
        ...
    
    def quit(self) -> None:
        """Send QUIT command and close connection gracefully."""
        ...
    
    def close(self) -> None:
        """Close connection unconditionally."""
        ...
    
    def set_pasv(self, passive: bool) -> None:
        """Set passive mode for data transfers.
        
        Args:
            passive: True for passive mode, False for active
        """
        ...


@runtime_checkable
class SMTPClientProtocol(Protocol):
    """Protocol for SMTP client abstraction.
    
    Implementations should wrap smtplib.SMTP
    to enable testing without actual SMTP connections.
    """
    
    def connect(self, host: str, port: int) -> None:
        """Connect to SMTP server.
        
        Args:
            host: Server hostname or IP address
            port: Server port number
        """
        ...
    
    def starttls(self) -> None:
        """Upgrade connection to TLS."""
        ...
    
    def login(self, user: str, password: str) -> None:
        """Authenticate with SMTP server.
        
        Args:
            user: Username for authentication
            password: Password for authentication
        """
        ...
    
    def sendmail(self, from_addr: str, to_addrs: list, msg: str) -> dict:
        """Send email message.
        
        Args:
            from_addr: Sender email address
            to_addrs: List of recipient email addresses
            msg: Email message content
            
        Returns:
            Dictionary of rejected recipients (empty if all accepted)
        """
        ...
    
    def send_message(self, msg: Any) -> dict:
        """Send EmailMessage object.
        
        Args:
            msg: EmailMessage object to send
            
        Returns:
            Dictionary of rejected recipients (empty if all accepted)
        """
        ...
    
    def quit(self) -> None:
        """Send QUIT command and close connection gracefully."""
        ...
    
    def close(self) -> None:
        """Close connection unconditionally."""
        ...
    
    def ehlo(self) -> None:
        """Send EHLO command to server."""
        ...
    
    def set_debuglevel(self, level: int) -> None:
        """Set debug output level.
        
        Args:
            level: Debug level (0 = no output, 1 = commands, 2 = commands + data)
        """
        ...


@runtime_checkable
class FileOperationsProtocol(Protocol):
    """Protocol for file operations abstraction.
    
    Implementations should wrap shutil and os operations
    to enable testing without actual filesystem changes.
    """
    
    def copy(self, src: str, dst: str) -> None:
        """Copy a file.
        
        Args:
            src: Source file path
            dst: Destination file path
        """
        ...
    
    def exists(self, path: str) -> bool:
        """Check if path exists.
        
        Args:
            path: Path to check
            
        Returns:
            True if path exists, False otherwise
        """
        ...
    
    def makedirs(self, path: str, exist_ok: bool = False) -> None:
        """Create directory and all parent directories.
        
        Args:
            path: Directory path to create
            exist_ok: If True, don't raise error if directory exists
        """
        ...
    
    def remove(self, path: str) -> None:
        """Remove a file.
        
        Args:
            path: File path to remove
        """
        ...
    
    def rmtree(self, path: str) -> None:
        """Remove directory and all contents.
        
        Args:
            path: Directory path to remove
        """
        ...
    
    def basename(self, path: str) -> str:
        """Get base name of path.
        
        Args:
            path: File path
            
        Returns:
            Base name (final component) of path
        """
        ...
    
    def dirname(self, path: str) -> str:
        """Get directory name of path.
        
        Args:
            path: File path
            
        Returns:
            Directory name of path
        """
        ...
    
    def join(self, *paths: str) -> str:
        """Join path components.
        
        Args:
            *paths: Path components to join
            
        Returns:
            Joined path
        """
        ...

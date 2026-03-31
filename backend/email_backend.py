"""Email backend for sending files via email.

This module sends files as email attachments with
injectable client support for testing.
"""

import errno
import mimetypes
import os
import re
import time
from email.message import EmailMessage

from backend.backend_base import BackendBase
from backend.protocols import SMTPClientProtocol
from backend.smtp_client import create_smtp_client
from core.structured_logging import get_logger

logger = get_logger(__name__)


def _is_network_unreachable(error: Exception) -> bool:
    """Return True when error indicates a network-unreachable condition.

    Traverses wrapped exceptions to catch nested socket errors.
    """
    visited: set[int] = set()
    current: BaseException | None = error

    while current is not None and id(current) not in visited:
        visited.add(id(current))

        if isinstance(current, OSError) and current.errno == errno.ENETUNREACH:
            return True

        smtp_code = getattr(current, "smtp_code", None)
        if smtp_code == errno.ENETUNREACH:
            return True

        current = current.__cause__ or current.__context__

    return False


def do(
    process_parameters: dict,
    settings: dict,
    filename: str,
    smtp_client: SMTPClientProtocol | None = None,
    disable_retry: bool = False,
) -> bool:
    """Send a file via email.

    Args:
        process_parameters: Dictionary containing email parameters
        settings: Settings dictionary containing SMTP configuration
        filename: Local file path to send
        smtp_client: Optional injectable SMTP client for testing
        disable_retry: If True, skip retry logic (for faster tests)

    Returns:
        True if email was sent successfully

    Raises:
        Exception: If email cannot be sent after 10 retries

    """
    backend = EmailBackend(smtp_client=smtp_client, disable_retry=disable_retry)
    return backend.send(process_parameters, settings, filename)


class EmailBackend(BackendBase):
    """Email backend class for object-oriented usage.

    Provides an object-oriented interface to the email backend
    with injectable client support.
    """

    def __init__(self, smtp_client: SMTPClientProtocol | None = None, disable_retry: bool = False) -> None:
        """Initialize email backend.

        Args:
            smtp_client: Optional injectable SMTP client for testing.
            disable_retry: If True, skip retry logic (for testing)

        """
        super().__init__(disable_retry=disable_retry)
        self.smtp_client = smtp_client
        self._server = None
        self._file_content = None
        self._maintype = None
        self._subtype = None

    def _execute(
        self,
        process_parameters: dict,
        settings: dict,
        filename: str,
        **kwargs,
    ) -> bool:
        """Send email with file attachment.

        Args:
            process_parameters: Email parameters
            settings: SMTP settings
            filename: File to send

        Returns:
            True if email was sent successfully

        """
        # Read file and determine content type (done once, before retry loop)
        if self._file_content is None:
            with open(filename, "rb") as fp:
                self._file_content = fp.read()

            ctype, encoding = mimetypes.guess_type(filename)
            if ctype is None or encoding is not None:
                ctype = "application/octet-stream"
            self._maintype, self._subtype = ctype.split("/", 1)

        # Create or use provided SMTP client
        if self.smtp_client is not None:
            self._server = self.smtp_client
        else:
            self._server = create_smtp_client()

        try:
            filename_no_path = os.path.basename(filename)
            filename_no_path_str = str(filename_no_path)

            # Build subject line
            if process_parameters["email_subject_line"] != "":
                date_time = str(time.ctime())
                subject_line_constructor = process_parameters["email_subject_line"]
                subject_line = subject_line_constructor.replace(
                    "%datetime%", date_time
                ).replace("%filename%", filename_no_path)
            else:
                subject_line = str(filename_no_path) + " Attached"

            subject_line = re.sub(r"[\r\n]", "", subject_line)
            filename_no_path_str = re.sub(r"[\r\n]", "", filename_no_path_str)

            # Parse recipient addresses
            to_address = process_parameters["email_to"]
            to_address_list = [a.strip() for a in to_address.split(",")]

            # Build email message
            message = EmailMessage()
            message["Subject"] = subject_line
            message["From"] = settings["email_address"]
            message["To"] = to_address_list
            message.set_content(filename_no_path_str + " Attached")

            # Attach file
            message.add_attachment(
                self._file_content,
                maintype=self._maintype,
                subtype=self._subtype,
                filename=filename_no_path_str,
            )

            # Connect and send
            self._server.connect(
                str(settings["email_smtp_server"]), int(settings["smtp_port"])
            )
            self._server.ehlo()
            self._server.starttls()

            if (
                settings.get("email_username", "") != ""
                and settings.get("email_password", "") != ""
            ):
                self._server.login(settings["email_username"], settings["email_password"])

            self._server.send_message(message)
            return True

        except Exception as email_error:
            if _is_network_unreachable(email_error):
                raise RuntimeError(
                    "Network is unreachable (Errno 101) while connecting to SMTP "
                    f"server {settings.get('email_smtp_server', '')}:"
                    f"{settings.get('smtp_port', '')}. "
                    "Check internet/VPN connectivity and SMTP server settings."
                ) from email_error
            raise

    def _get_backend_name(self) -> str:
        """Get backend name for logging."""
        return "smtp"

    def _get_endpoint(
        self, process_parameters: dict, settings: dict
    ) -> str:
        """Get SMTP endpoint for logging."""
        return f"{settings.get('email_smtp_server', '')}:{settings.get('smtp_port', '')}"

    def _cleanup(self) -> None:
        """Close SMTP connection."""
        if self._server is not None:
            try:
                self._server.close()
            except Exception as close_err:
                logger.debug("Failed to close SMTP connection: %s", close_err)

    def _prepare_for_retry(
        self,
        process_parameters: dict,
        settings: dict,
        filename: str,
        **kwargs,
    ) -> None:
        """Prepare for retry by resetting state."""
        self._server = None

    def send(
        self, process_parameters: dict, settings: dict, filename: str
    ) -> bool:
        """Send a file via email.

        Args:
            process_parameters: Email parameters
            settings: Settings dictionary
            filename: File to send

        Returns:
            True if successful

        """
        try:
            return self.execute(process_parameters, settings, filename)
        finally:
            self._cleanup()
            # Reset file content for potential reuse
            self._file_content = None

    @staticmethod
    def create_client(config: dict | None = None) -> SMTPClientProtocol:
        """Create an SMTP client.

        Args:
            config: Optional configuration dictionary

        Returns:
            SMTP client instance

        """
        return create_smtp_client(config=config)

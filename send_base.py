import abc
import time


class BaseSendBackend(abc.ABC):
    """
    Abstract base class for send backends.
    Defines the template method for sending files with retry logic.
    """

    def __init__(self, process_parameters, settings_dict, filename):
        """
        Initialize the send backend with common parameters.
        
        Args:
            process_parameters: Dict of parameters from the database row
            settings_dict: Dict of application settings
            filename: Path to the file to send
        """
        self.process_parameters = process_parameters
        self.settings_dict = settings_dict
        self.filename = filename

    def send(self):
        """
        Orchestrate the sending process with retry logic.
        Template method that calls _send() implemented by subclasses.
        """
        file_pass = False
        counter = 0
        while not file_pass:
            try:
                self._send()
                file_pass = True
            except Exception as error:
                if counter == 10:
                    print("Retried 10 times, passing exception to dispatch")
                    raise
                counter += 1
                self._handle_retry(counter, error)

    @abc.abstractmethod
    def _send(self):
        """
        Abstract method to be implemented by subclasses.
        Contains the backend-specific sending logic.
        """
        pass

    def _handle_retry(self, counter, error):
        """
        Handle retry logic.
        
        Args:
            counter: Current retry count
            error: Exception that occurred
        """
        print("Encountered an error. Retry number " + str(counter))
        print("Error is :" + str(error))
        # Exponential backoff for email backend, simple retry for others
        # This mimics the existing behavior in email_backend.py
        if hasattr(self, 'exponential_backoff') and self.exponential_backoff:
            time.sleep(counter * counter)


def create_send_wrapper(backend_class):
    """
    Create a backward-compatible do() function wrapper for a backend class.
    
    Args:
        backend_class: The backend class to wrap
        
    Returns:
        function: A do() function that instantiates the backend and calls send()
    """
    def do(process_parameters, settings_dict, filename):
        backend = backend_class(process_parameters, settings_dict, filename)
        backend.send()
    return do

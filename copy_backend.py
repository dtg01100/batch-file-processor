import shutil

from send_base import BaseSendBackend, create_send_wrapper


class CopySendBackend(BaseSendBackend):
    """
    Copy send backend implementation.
    Copies files to a local directory (for testing purposes).
    """
    
    def _send(self):
        shutil.copy(self.filename, self.process_parameters['copy_to_directory'])


do = create_send_wrapper(CopySendBackend)

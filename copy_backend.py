import shutil

from send_base import BaseSendBackend, create_send_wrapper


class CopySendBackend(BaseSendBackend):
    """Copy send backend implementation."""

    PLUGIN_ID = "copy"
    PLUGIN_NAME = "Copy to Directory"
    PLUGIN_DESCRIPTION = "Copy files to a local directory"

    CONFIG_FIELDS = [
        {
            "key": "copy_to_directory",
            "label": "Destination Directory",
            "type": "string",
            "default": "",
            "required": True,
            "placeholder": "/path/to/destination",
            "help": "Local directory path to copy files to",
        }
    ]

    def _send(self):
        dest_dir = self.get_config_value("copy_to_directory", "")
        shutil.copy(self.filename, dest_dir)


do = create_send_wrapper(CopySendBackend)

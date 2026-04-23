# tests/unit/interface/models/test_folder_config_alert.py

from interface.models.folder_configuration import FolderConfiguration


class TestFolderConfigAlertOnFailure:
    def test_alert_on_failure_default_true(self):
        config = FolderConfiguration()
        assert config.alert_on_failure is True

    def test_alert_on_failure_can_be_set_false(self):
        config = FolderConfiguration(alert_on_failure=False)
        assert config.alert_on_failure is False

    def test_alert_on_failure_from_dict(self):
        data = {
            "folder_name": "/test",
            "alert_on_failure": False,
        }
        config = FolderConfiguration.from_dict(data)
        assert config.alert_on_failure is False

    def test_alert_on_failure_from_dict_default_true(self):
        data = {
            "folder_name": "/test",
        }
        config = FolderConfiguration.from_dict(data)
        assert config.alert_on_failure is True

    def test_alert_on_failure_to_dict(self):
        config = FolderConfiguration(folder_name="/test", alert_on_failure=False)
        data = config.to_dict()
        assert data["alert_on_failure"] is False

import unittest
import json
import ast

import dataset

from interface.models.folder_configuration import FolderConfiguration
import schema
from interface.operations.plugin_configuration_mapper import ExtractedPluginConfig, PluginConfigurationMapper


def _normalize_plugin_configs(value):
    """Normalize stored plugin_configurations (may be dict, JSON string, or Python dict repr)."""
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        # Try JSON first
        try:
            return json.loads(value)
        except Exception:
            try:
                # Fallback to Python literal eval for dict repr
                return ast.literal_eval(value)
            except Exception:
                # Last-resort: empty dict
                return {}
    return {}


class TestFolderDatabaseRoundTrip(unittest.TestCase):
    def setUp(self):
        # in-memory DB
        self.db = dataset.connect('sqlite:///')
        schema.ensure_schema(self.db)

    def tearDown(self):
        try:
            self.db.close()
        except Exception:
            pass

    def test_insert_and_read_folder_with_plugin_configs(self):
        fc = FolderConfiguration(folder_name='rt-test', folder_is_active='True')
        fc.set_plugin_configuration('csv', {'include_headers': True, 'filter_ampersand': False})

        folders = self.db['folders']
        new_id = folders.insert(fc.to_dict())

        row = folders.find_one(id=new_id)
        self.assertIsNotNone(row)

        stored = _normalize_plugin_configs(row.get('plugin_configurations'))
        self.assertIn('csv', stored)
        self.assertEqual(stored['csv']['include_headers'], True)

    def test_update_folder_plugin_configurations_via_mapper(self):
        # create basic folder w/ empty plugin configs
        fc = FolderConfiguration(folder_name='update-test')
        folders = self.db['folders']
        rowid = folders.insert(fc.to_dict())

        # prepare extracted plugin configs (as mapper would produce)
        extracted = [ExtractedPluginConfig(format_name='csv', config={'include_headers': False}, validation_errors=[])]

        # load existing dict, apply update
        folder_dict = folders.find_one(id=rowid)
        mapper = PluginConfigurationMapper()
        updated = mapper.update_folder_configuration_from_dict(folder_dict, extracted)

        # perform DB update
        folders.update(updated, ['id'])

        row_after = folders.find_one(id=rowid)
        stored = _normalize_plugin_configs(row_after.get('plugin_configurations'))
        self.assertIn('csv', stored)
        self.assertEqual(stored['csv']['include_headers'], False)


if __name__ == '__main__':
    unittest.main()

import unittest
import importlib

class TestInterface(unittest.TestCase):
    def setUp(self):
        self.module = importlib.import_module('interface')

    def test_import(self):
        # Just test that the module imports without error
        try:
            importlib.reload(self.module)
        except Exception as e:
            self.fail(f"interface import failed: {e}")

if __name__ == '__main__':
    unittest.main()

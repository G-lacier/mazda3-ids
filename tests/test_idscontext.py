import os
import tempfile
import unittest

from ids import IDSContext


class DummyArgs:
    def __init__(self, root, lang='ENG'):
        self.root = root
        self.lang = lang


class TestIDSContext(unittest.TestCase):
    def test_missing_datatypes(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = os.path.join(tmp, 'Data')
            os.makedirs(data_dir)
            ctx = IDSContext(DummyArgs(tmp))
            with self.assertRaises(ValueError):
                ctx.datatypes()


if __name__ == '__main__':
    unittest.main()

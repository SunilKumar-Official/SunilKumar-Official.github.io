"""Guards the real, committed data: it must always pass tools/check.py."""
import unittest

from helpers import common
from tools import check


class RepoDataTests(unittest.TestCase):
    def test_committed_public_data_is_clean(self):
        errors, _warnings = check.run_checks(common.Paths())
        self.assertEqual(errors, [])

    def test_there_are_five_projects(self):
        self.assertEqual(len(common.load_json(common.Paths().projects, [])), 5)


if __name__ == "__main__":
    unittest.main()

"""Guards the real, committed data: it must always pass tools/check.py."""
import unittest

from helpers import common
from tools import check


class RepoDataTests(unittest.TestCase):
    def test_committed_public_data_is_clean(self):
        errors, _warnings = check.run_checks(common.Paths())
        self.assertEqual(errors, [])

    def test_there_are_two_projects(self):
        # Was 5 until the Conversation Intelligence Platform round: "AI Quality-Review
        # Evaluation" was an earlier, thinner description of that same work and was
        # removed once the full case study replaced it, to avoid the two pages
        # contradicting each other (one said the model wasn't rolled out, the other
        # says it went to production).
        # Daily KPI Email Report and Call Volume Forecasting were hidden on 2026-10-16
        # until they get case studies; restore them from git history (data/projects.json).
        self.assertEqual(len(common.load_json(common.Paths().projects, [])), 2)


if __name__ == "__main__":
    unittest.main()

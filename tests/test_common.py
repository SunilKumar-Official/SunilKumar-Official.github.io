import json
import unittest

from helpers import common, make_paths, sample_career_stage, sample_post, sample_project


class StorageTests(unittest.TestCase):
    def test_paths_layout(self):
        paths, tmp = make_paths()
        self.addCleanup(tmp.cleanup)
        self.assertEqual(paths.posts, paths.data / "posts.json")
        self.assertEqual(paths.drafts, paths.private / "drafts.json")
        self.assertEqual(paths.data_js, paths.data / "data.js")
        self.assertEqual(paths.discarded, paths.private / "discarded.json")
        self.assertEqual(paths.career, paths.data / "career.json")

    def test_load_json_default_when_missing(self):
        paths, tmp = make_paths()
        self.addCleanup(tmp.cleanup)
        self.assertEqual(common.load_json(paths.posts, []), [])

    def test_save_then_load_round_trip_keeps_unicode(self):
        paths, tmp = make_paths()
        self.addCleanup(tmp.cleanup)
        common.save_json(paths.posts, [{"title": "Café – data"}])
        self.assertIn("Café", paths.posts.read_text(encoding="utf-8"))
        self.assertEqual(common.load_json(paths.posts, []), [{"title": "Café – data"}])

    def test_backup_copies_existing_file_and_ignores_missing(self):
        paths, tmp = make_paths()
        self.addCleanup(tmp.cleanup)
        self.assertIsNone(common.backup(paths, paths.posts))
        common.save_json(paths.posts, [1])
        copy = common.backup(paths, paths.posts)
        self.assertTrue(copy.exists())
        self.assertEqual(copy.parent, paths.backups)
        self.assertTrue(copy.name.startswith("posts.json."))

    def test_make_id_is_ten_hex_characters_and_stable(self):
        a = common.make_id("https://example.com/x")
        self.assertRegex(a, r"^[0-9a-f]{10}$")
        self.assertEqual(a, common.make_id("https://example.com/x"))
        self.assertNotEqual(common.make_id("a", "b"), common.make_id("ab"))


class DataJsTests(unittest.TestCase):
    def test_write_data_js_matches_json_files(self):
        paths, tmp = make_paths()
        self.addCleanup(tmp.cleanup)
        common.save_json(paths.posts, [sample_post()])
        common.save_json(paths.projects, [sample_project()])
        common.write_data_js(paths)
        text = paths.data_js.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("window.SITE_DATA = "))
        payload = json.loads(text[len("window.SITE_DATA = "):].rstrip().rstrip(";"))
        self.assertEqual(payload["posts"], [sample_post()])
        self.assertEqual(payload["projects"], [sample_project()])
        self.assertEqual(payload["testimonials"], [])
        self.assertEqual(text, common.render_data_js(common.load_public(paths)))

    def test_career_flows_through_write_data_js(self):
        paths, tmp = make_paths()
        self.addCleanup(tmp.cleanup)
        common.save_json(paths.career, [sample_career_stage()])
        common.write_data_js(paths)
        text = paths.data_js.read_text(encoding="utf-8")
        payload = json.loads(text[len("window.SITE_DATA = "):].rstrip().rstrip(";"))
        self.assertEqual(payload["career"], [sample_career_stage()])


class DraftsTests(unittest.TestCase):
    def setUp(self):
        self.paths, self.tmp = make_paths()
        self.addCleanup(self.tmp.cleanup)

    def test_drafts_round_trip_and_backup(self):
        self.assertEqual(common.load_drafts(self.paths), [])
        common.save_drafts(self.paths, [{"kind": "post", "id": "a"}])
        common.save_drafts(self.paths, [])
        self.assertEqual(common.load_drafts(self.paths), [])
        self.assertTrue(list(self.paths.backups.glob("drafts.json.*")))


class DiscardedTests(unittest.TestCase):
    def setUp(self):
        self.paths, self.tmp = make_paths()
        self.addCleanup(self.tmp.cleanup)

    def test_missing_file_means_no_discarded_ids(self):
        self.assertEqual(common.load_discarded(self.paths), [])

    def test_remember_merges_and_removes_duplicates(self):
        common.remember_discarded(self.paths, ["aaaaaaaaaa", "bbbbbbbbbb"])
        common.remember_discarded(self.paths, ["bbbbbbbbbb", "cccccccccc", "cccccccccc"])
        self.assertEqual(common.load_discarded(self.paths), ["aaaaaaaaaa", "bbbbbbbbbb", "cccccccccc"])
        self.assertTrue(list(self.paths.backups.glob("discarded.json.*")))

    def test_remembering_nothing_writes_nothing(self):
        common.remember_discarded(self.paths, [])
        self.assertFalse(self.paths.discarded.exists())


if __name__ == "__main__":
    unittest.main()

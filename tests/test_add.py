import unittest

from helpers import common, make_paths, scripted
from tools import add


POST_ANSWERS = [
    "https://community.example/posts/42", "Cleaning data before modelling",
    "Notes on the three checks I run before any model.", "2026-10-01", "data-community", "Data Community", "data, quality",
]
TESTIMONIAL_ANSWERS = [
    "Asha Rao", "Operations Manager", "Example Co", "Sunil built a report we trust every morning.", "2026-08-15", "1", "",
]


class AddTests(unittest.TestCase):
    def setUp(self):
        self.paths, self.tmp = make_paths()
        self.addCleanup(self.tmp.cleanup)
        self.lines = []

    def run_add(self, kind, answers, draft=False):
        return add.add(kind, self.paths, scripted(*answers), self.lines.append, draft=draft, today="2026-10-10")

    def test_post_is_published_after_confirmation(self):
        code = self.run_add("post", POST_ANSWERS + ["y"])
        self.assertEqual(code, 0)
        post = common.load_json(self.paths.posts, [])[0]
        self.assertEqual((post["source"], post["sourceLabel"], post["tags"]), ("data-community", "Data Community", ["data", "quality"]))
        self.assertEqual(post["id"], common.make_id("https://community.example/posts/42"))
        self.assertIn(post["id"], self.paths.data_js.read_text(encoding="utf-8"))

    def test_defaults_for_date_source_and_label(self):
        answers = ["https://www.linkedin.com/feed/update/1", "A title", "An excerpt", "", "", "", "ai", "y"]
        self.assertEqual(self.run_add("post", answers), 0)
        post = common.load_json(self.paths.posts, [])[0]
        self.assertEqual((post["date"], post["source"], post["sourceLabel"]), ("2026-10-10", "linkedin", "LinkedIn"))

    def test_declining_saves_nothing(self):
        self.assertEqual(self.run_add("post", POST_ANSWERS + ["n"]), 1)
        self.assertFalse(self.paths.posts.exists())
        self.assertIn("Not saved.", self.lines)

    def test_invalid_input_is_explained_and_not_saved(self):
        bad = list(POST_ANSWERS)
        bad[1] = "x"                                           # title too short
        self.assertEqual(self.run_add("post", bad + ["y"]), 1)
        self.assertIn("title: must be 3-90 characters (is 1)", "\n".join(self.lines))
        self.assertFalse(self.paths.posts.exists())

    def test_duplicate_post_is_refused(self):
        self.run_add("post", POST_ANSWERS + ["y"])
        self.assertEqual(self.run_add("post", POST_ANSWERS + ["y"]), 1)
        self.assertIn("id: already published", "\n".join(self.lines))
        self.assertEqual(len(common.load_json(self.paths.posts, [])), 1)

    def test_draft_goes_to_private_not_public(self):
        self.assertEqual(self.run_add("post", POST_ANSWERS + ["y"], draft=True), 0)
        self.assertFalse(self.paths.posts.exists())
        drafts = common.load_drafts(self.paths)
        self.assertEqual((drafts[0]["kind"], drafts[0]["status"]), ("post", "draft"))

    def test_testimonial_with_consent_is_published(self):
        self.assertEqual(self.run_add("testimonial", TESTIMONIAL_ANSWERS + ["y"]), 0)
        t = common.load_json(self.paths.testimonials, [])[0]
        self.assertEqual((t["name"], t["consent"]), ("Asha Rao", "written"))
        self.assertNotIn("sourceUrl", t)

    def test_unrecognised_consent_answer_is_explained_and_asked_again(self):
        answers = TESTIMONIAL_ANSWERS[:-2] + ["3", "1", "", "y"]
        self.assertEqual(self.run_add("testimonial", answers), 0)
        self.assertIn("Please answer 1, 2 or leave blank.", self.lines)
        self.assertEqual(common.load_json(self.paths.testimonials, [])[0]["consent"], "written")

    def test_consent_question_gives_up_after_three_tries(self):
        answers = TESTIMONIAL_ANSWERS[:-2] + ["x", "y", "z", "", "y"]
        self.assertEqual(self.run_add("testimonial", answers, draft=True), 0)
        self.assertEqual(self.lines.count("Please answer 1, 2 or leave blank."), 3)
        self.assertEqual(common.load_drafts(self.paths)[0]["consent"], "")

    def test_testimonial_source_link_is_kept(self):
        answers = TESTIMONIAL_ANSWERS[:-2] + ["2", "https://www.linkedin.com/in/sunilkumar-BI/details/recommendations/", "y"]
        self.assertEqual(self.run_add("testimonial", answers), 0)
        t = common.load_json(self.paths.testimonials, [])[0]
        self.assertEqual((t["consent"], t["sourceUrl"]), ("public-linkedin", "https://www.linkedin.com/in/sunilkumar-BI/details/recommendations/"))

    def test_testimonial_without_consent_is_refused_with_a_hint(self):
        answers = TESTIMONIAL_ANSWERS[:-2] + ["", "", "y"]
        self.assertEqual(self.run_add("testimonial", answers), 1)
        text = "\n".join(self.lines)
        self.assertIn("consent: must be one of", text)
        self.assertIn("--draft", text)
        self.assertFalse(self.paths.testimonials.exists())

    def test_testimonial_without_consent_can_be_saved_as_draft(self):
        answers = TESTIMONIAL_ANSWERS[:-2] + ["", "", "y"]
        self.assertEqual(self.run_add("testimonial", answers, draft=True), 0)
        self.assertEqual(common.load_drafts(self.paths)[0]["consent"], "")
        self.assertFalse(self.paths.testimonials.exists())

    def test_main_parses_arguments(self):
        code = add.main(["post", "--draft"], paths=self.paths, inp=scripted(*POST_ANSWERS, "y"), out=self.lines.append, today="2026-10-10")
        self.assertEqual(code, 0)
        self.assertEqual(len(common.load_drafts(self.paths)), 1)


if __name__ == "__main__":
    unittest.main()

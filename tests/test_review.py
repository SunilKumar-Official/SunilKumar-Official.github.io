import unittest

from helpers import common, make_paths, sample_post, sample_testimonial, scripted
from tools import review


def post_draft(n=1, **over):
    url = f"https://www.linkedin.com/feed/update/urn:li:share:{n}"
    d = sample_post(url=url, id=common.make_id(url), tags=[], kind="post", status="draft")
    d.update(over)
    return d


def testimonial_draft(**over):
    d = sample_testimonial(kind="testimonial", status="draft", consent="", sourceUrl="")
    d.update(over)
    return d


def interrupting(*answers):
    """An input() replacement that returns the answers in order, then raises KeyboardInterrupt (Ctrl-C)."""
    it = iter(answers)

    def inp(prompt=""):
        try:
            return next(it)
        except StopIteration:
            raise KeyboardInterrupt
    return inp


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.paths, self.tmp = make_paths()
        self.addCleanup(self.tmp.cleanup)
        self.lines = []

    def run_review(self, *answers):
        return review.review(self.paths, scripted(*answers), self.lines.append)

    def test_parse_value(self):
        self.assertEqual(review.parse_value("tags", " Data, BI ,, ai "), ["data", "bi", "ai"])
        self.assertEqual(review.parse_value("consent", "w"), "written")
        self.assertEqual(review.parse_value("consent", "l"), "public-linkedin")
        self.assertEqual(review.parse_value("title", "  Hello "), "Hello")

    def test_no_drafts(self):
        summary = self.run_review()
        self.assertEqual((summary.published, summary.remaining), (0, 0))
        self.assertIn("No drafts to review.", self.lines)

    def test_edit_then_publish_a_post(self):
        common.save_drafts(self.paths, [post_draft()])
        summary = self.run_review("e", "tags", "data, bi", "p")
        self.assertEqual(summary.published, 1)
        published = common.load_json(self.paths.posts, [])
        self.assertEqual(published[0]["tags"], ["data", "bi"])
        self.assertNotIn("status", published[0])
        self.assertEqual(common.load_drafts(self.paths), [])
        self.assertIn(published[0]["id"], self.paths.data_js.read_text(encoding="utf-8"))

    def test_publish_fails_until_the_draft_is_valid(self):
        common.save_drafts(self.paths, [post_draft()])      # tags are empty, so publishing must fail
        summary = self.run_review("p", "e", "tags", "ai", "p")
        text = "\n".join(self.lines)
        self.assertIn("Cannot publish yet:", text)
        self.assertIn("tags: need 1 to 4 tags", text)
        self.assertEqual(summary.published, 1)

    def test_testimonial_cannot_be_published_without_consent(self):
        common.save_drafts(self.paths, [testimonial_draft()])
        summary = self.run_review("p", "q")
        self.assertIn("consent: must be one of written, public-linkedin", "\n".join(self.lines))
        self.assertEqual(summary.published, 0)
        self.assertFalse(self.paths.testimonials.exists())
        self.assertEqual(len(common.load_drafts(self.paths)), 1)

    def test_testimonial_published_after_consent_is_set(self):
        common.save_drafts(self.paths, [testimonial_draft()])
        summary = self.run_review("e", "consent", "w", "p")
        self.assertEqual(summary.published, 1)
        self.assertEqual(common.load_json(self.paths.testimonials, [])[0]["consent"], "written")

    def test_skip_keeps_discard_removes_quit_keeps_the_rest(self):
        common.save_drafts(self.paths, [post_draft(1), post_draft(2), post_draft(3), post_draft(4)])
        summary = self.run_review("s", "d", "q")
        self.assertEqual((summary.skipped, summary.discarded, summary.published), (1, 1, 0))
        remaining = common.load_drafts(self.paths)
        self.assertEqual(len(remaining), 3)
        self.assertEqual(summary.remaining, 3)

    def test_end_of_input_acts_like_quit_and_keeps_edits(self):
        common.save_drafts(self.paths, [post_draft()])
        self.run_review("e", "title", "A better title")
        self.assertEqual(common.load_drafts(self.paths)[0]["title"], "A better title")

    def test_unknown_field_and_unknown_choice_are_explained(self):
        common.save_drafts(self.paths, [post_draft()])
        self.run_review("x", "e", "colour", "q")
        text = "\n".join(self.lines)
        self.assertIn("Choose p, e, s, d or q.", text)
        self.assertIn("'colour' cannot be edited", text)

    def test_note_is_shown(self):
        common.save_drafts(self.paths, [post_draft(note="date could not be read ('x')")])
        self.run_review("q")
        self.assertTrue(any("NOTE" in line and "date could not be read" in line for line in self.lines))

    def test_interrupt_keeps_unfinished_drafts_and_their_edits(self):
        drafts = [post_draft(1, tags=["data"]), post_draft(2, tags=["data"]), post_draft(3, tags=["data"])]
        common.save_drafts(self.paths, drafts)
        summary = review.review(self.paths, interrupting("p", "e", "title", "A new title"), self.lines.append)
        self.assertIn("Interrupted: unfinished drafts are kept.", "\n".join(self.lines))
        published = common.load_json(self.paths.posts, [])
        self.assertEqual([p["id"] for p in published], [drafts[0]["id"]])
        remaining = common.load_drafts(self.paths)
        self.assertEqual([d["id"] for d in remaining], [drafts[1]["id"], drafts[2]["id"]])
        self.assertEqual(remaining[0]["title"], "A new title")
        self.assertEqual((summary.published, summary.remaining), (1, 2))

    def test_quit_without_changes_does_not_write_a_backup(self):
        common.save_drafts(self.paths, [post_draft()])
        self.run_review("q")
        self.assertFalse(self.paths.backups.exists() and any(self.paths.backups.glob("drafts.json.*")))

    def test_unknown_kind_is_explained_and_can_be_discarded(self):
        common.save_drafts(self.paths, [post_draft(kind="weird")])
        self.run_review("p", "d")
        text = "\n".join(self.lines)
        self.assertIn("Cannot publish yet:", text)
        self.assertIn("kind: cannot publish 'weird'", text)
        self.assertEqual(common.load_drafts(self.paths), [])

    def test_discard_is_remembered_in_private_discarded_json(self):
        a, b = post_draft(1), post_draft(2)
        common.save_drafts(self.paths, [a, b])
        self.run_review("d", "s")
        self.assertEqual(common.load_json(self.paths.discarded, None), [a["id"]])

    def test_nothing_discarded_writes_no_discarded_file(self):
        common.save_drafts(self.paths, [post_draft(1)])
        self.run_review("s")
        self.assertFalse(self.paths.discarded.exists())

    def test_interrupt_after_a_discard_still_remembers_it(self):
        a, b = post_draft(1), post_draft(2)
        common.save_drafts(self.paths, [a, b])
        review.review(self.paths, interrupting("d"), self.lines.append)
        self.assertEqual(common.load_discarded(self.paths), [a["id"]])
        self.assertEqual([d["id"] for d in common.load_drafts(self.paths)], [b["id"]])

    def test_field_prompt_lists_the_editable_fields_for_the_kind(self):
        prompts = []

        def inp(prompt=""):
            prompts.append(prompt)
            return "q" if len(prompts) > 2 else ["e", "colour"][len(prompts) - 1]
        for draft, expected in ((post_draft(), "field (title, excerpt, date, source, sourceLabel, tags) > "),
                                (testimonial_draft(), "field (name, role, company, quote, date, consent, sourceUrl) > ")):
            prompts.clear()
            common.save_drafts(self.paths, [draft])
            review.review(self.paths, inp, self.lines.append)
            self.assertIn(expected, prompts)

    def test_consent_value_prompt_explains_the_shortcuts(self):
        prompts = []
        answers = iter(["e", "consent", "w", "q"])

        def inp(prompt=""):
            prompts.append(prompt)
            return next(answers)
        common.save_drafts(self.paths, [testimonial_draft()])
        review.review(self.paths, inp, self.lines.append)
        self.assertIn("new consent (w = written, l = public-linkedin) > ", prompts)

    def test_testimonial_consent_failure_says_how_to_fix_it(self):
        common.save_drafts(self.paths, [testimonial_draft()])
        self.run_review("p", "q")
        lines = self.lines
        hint = "Set it with: e, then consent, then w or l."
        self.assertIn(hint, lines)
        self.assertEqual(lines[lines.index(hint) - 1], "  - consent: must be one of written, public-linkedin")

    def test_hint_is_not_shown_for_other_errors(self):
        common.save_drafts(self.paths, [post_draft()])
        self.run_review("p", "q")
        self.assertNotIn("Set it with: e, then consent, then w or l.", self.lines)


if __name__ == "__main__":
    unittest.main()

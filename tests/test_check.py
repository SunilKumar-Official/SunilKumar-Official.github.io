import io
import unittest
from contextlib import redirect_stdout

from helpers import common, make_paths, sample_career_stage, sample_post, sample_project, sample_testimonial
from tools import check


def seed(paths, posts=(), testimonials=(), projects=(), career=()):
    common.save_json(paths.posts, list(posts))
    common.save_json(paths.testimonials, list(testimonials))
    common.save_json(paths.projects, list(projects))
    common.save_json(paths.career, list(career))
    common.write_data_js(paths)


def post_n(n, **over):
    url = f"https://www.linkedin.com/posts/x-{n}"
    return sample_post(url=url, id=common.make_id(url), **over)


class CheckTests(unittest.TestCase):
    def setUp(self):
        self.paths, self.tmp = make_paths()
        self.addCleanup(self.tmp.cleanup)

    def test_clean_data_has_no_errors_or_warnings(self):
        seed(self.paths, [post_n(1)], [sample_testimonial()], [sample_project()])
        self.assertEqual(check.run_checks(self.paths), ([], []))

    def test_empty_site_is_clean(self):
        seed(self.paths)
        self.assertEqual(check.run_checks(self.paths), ([], []))

    def test_invalid_records_are_reported_with_their_position_and_name(self):
        seed(self.paths, [post_n(1, title="x")], [sample_testimonial(consent="")], [sample_project(stack=[])],
             [sample_career_stage(summary="")])
        errors, _ = check.run_checks(self.paths)
        text = "\n".join(errors)
        self.assertIn("posts[0] 'x': title", text)
        self.assertIn("testimonials[0] 'Asha Rao': consent", text)
        self.assertIn("projects[0] 'KPI Scoring Pipeline': stack", text)
        self.assertIn("career[0] 'Customer Experience': summary", text)

    def test_hand_added_unconsented_testimonial_is_caught(self):
        seed(self.paths)
        common.save_json(self.paths.testimonials, [sample_testimonial(consent="pending")])
        common.write_data_js(self.paths)
        errors, _ = check.run_checks(self.paths)
        self.assertTrue(any("consent" in e for e in errors))

    def test_duplicates(self):
        a = post_n(1)
        seed(self.paths, [a, dict(a)], [sample_testimonial(), sample_testimonial()], [sample_project(), sample_project()])
        errors, _ = check.run_checks(self.paths)
        text = "\n".join(errors)
        self.assertIn("duplicate id", text)
        self.assertIn("duplicate url", text)
        self.assertIn("testimonials: duplicate id", text)
        self.assertIn("projects: duplicate title", text)

    def test_single_use_tags_warn_only_once_there_are_five_posts(self):
        seed(self.paths, [post_n(i, tags=["data"]) for i in range(4)] + [post_n(9, tags=["data", "dtaa"])])
        errors, warnings = check.run_checks(self.paths)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, ["posts: tag 'dtaa' is used once (typo?)"])
        seed(self.paths, [post_n(1, tags=["dtaa"])])
        self.assertEqual(check.run_checks(self.paths)[1], [])

    def test_email_and_phone_numbers_are_errors_but_dates_and_urls_are_not(self):
        seed(self.paths, [post_n(1, excerpt="Write to me at someone@example.com", title="Call +1 555 010 4477 now"),
                          sample_post(url="https://www.linkedin.com/posts/x-activity-7123456789012345678",
                                      id=common.make_id("https://www.linkedin.com/posts/x-activity-7123456789012345678"),
                                      excerpt="Posted on 2026-09-30 about dashboards.")])
        errors, _ = check.run_checks(self.paths)
        text = "\n".join(errors)
        self.assertIn("email address", text)
        self.assertIn("phone number", text)
        self.assertEqual(len([e for e in errors if "posts[1]" in e]), 0, errors)

    def test_stale_or_missing_data_js_is_an_error(self):
        seed(self.paths, [post_n(1)])
        common.save_json(self.paths.posts, [post_n(1), post_n(2)])
        errors, _ = check.run_checks(self.paths)
        self.assertTrue(any("data.js is out of date" in e for e in errors))
        self.paths.data_js.unlink()
        errors, _ = check.run_checks(self.paths)
        self.assertTrue(any("data.js is out of date" in e for e in errors))

    def test_main_exit_codes(self):
        seed(self.paths, [post_n(1)])
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(check.main(paths=self.paths), 0)
        self.assertIn("OK", out.getvalue())
        common.save_json(self.paths.posts, [post_n(1, title="x")])
        common.write_data_js(self.paths)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(check.main(paths=self.paths), 1)

    def test_career_json_is_included_in_the_data_js_freshness_check(self):
        seed(self.paths, career=[sample_career_stage()])
        self.assertEqual(check.run_checks(self.paths), ([], []))
        common.save_json(self.paths.career, [sample_career_stage(title="Edited after build")])
        errors, _ = check.run_checks(self.paths)
        self.assertIn("data/data.js is out of date: run python3 tools/build_data.py", errors)

    def test_career_fields_are_still_scanned_for_email_and_phone(self):
        seed(self.paths, career=[sample_career_stage(summary="Reach me at someone@example.com")])
        errors, _ = check.run_checks(self.paths)
        self.assertTrue(any("email address" in e for e in errors))


class HandEditedDataTests(unittest.TestCase):
    def setUp(self):
        self.paths, self.tmp = make_paths()
        self.addCleanup(self.tmp.cleanup)
        seed(self.paths, [post_n(1)], [sample_testimonial()], [sample_project()])

    def test_invalid_json_is_one_readable_error_and_other_files_are_still_checked(self):
        self.paths.posts.write_text('[{"id": "x",}]', encoding="utf-8")
        common.save_json(self.paths.testimonials, [sample_testimonial(consent="")])
        errors, _ = check.run_checks(self.paths)
        self.assertEqual(len([e for e in errors if e.startswith("data/posts.json is not valid JSON: ")]), 1, errors)
        self.assertTrue(any("testimonials[0]" in e and "consent" in e for e in errors), errors)
        self.assertFalse(any("data.js" in e for e in errors), errors)

    def test_each_public_file_can_have_invalid_json(self):
        for name in ("posts", "testimonials", "projects"):
            with self.subTest(file=name):
                getattr(self.paths, name).write_text("not json", encoding="utf-8")
                errors, _ = check.run_checks(self.paths)
                self.assertTrue(any(e.startswith(f"data/{name}.json is not valid JSON: ") for e in errors), errors)
                seed(self.paths, [post_n(1)], [sample_testimonial()], [sample_project()])

    def test_top_level_that_is_not_a_list_is_reported(self):
        self.paths.posts.write_text('{"id": "x"}', encoding="utf-8")
        errors, _ = check.run_checks(self.paths)
        self.assertIn("data/posts.json must contain a list", errors)
        self.assertFalse(any("data.js" in e for e in errors), errors)

    def test_entry_that_is_not_an_object_is_reported_and_skipped(self):
        posts = [post_n(1), post_n(2), post_n(3), "oops"]
        common.save_json(self.paths.posts, posts)
        common.write_data_js(self.paths)
        errors, warnings = check.run_checks(self.paths)
        self.assertEqual(errors, ["posts[3] is not an object"])
        self.assertEqual(warnings, [])

    def test_unreadable_file_does_not_raise_from_main(self):
        self.paths.projects.write_text("[", encoding="utf-8")
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(check.main(paths=self.paths), 1)
        self.assertIn("data/projects.json is not valid JSON", out.getvalue())

    def test_clean_data_set_still_returns_nothing(self):
        self.assertEqual(check.run_checks(self.paths), ([], []))


if __name__ == "__main__":
    unittest.main()

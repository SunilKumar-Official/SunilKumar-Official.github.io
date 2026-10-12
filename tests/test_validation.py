import unittest

from helpers import common, make_paths, sample_post, sample_project, sample_testimonial


class PostValidationTests(unittest.TestCase):
    def test_valid_post_has_no_errors(self):
        self.assertEqual(common.validate_post(sample_post()), [])

    def test_each_rule_reports_its_field(self):
        cases = {
            "id": {"id": "nothex"},
            "source": {"source": "Linked In"},
            "sourceLabel": {"sourceLabel": ""},
            "title": {"title": "ab"},
            "excerpt": {"excerpt": "x" * 161},
            "date": {"date": "2026-02-30"},
            "url": {"url": "http://example.com/post"},
            "tags": {"tags": []},
        }
        for field, change in cases.items():
            with self.subTest(field=field):
                errors = common.validate_post(sample_post(**change))
                self.assertTrue(any(e.startswith(field) for e in errors), errors)

    def test_title_limit_is_ninety(self):
        self.assertEqual(common.validate_post(sample_post(title="t" * 90)), [])
        self.assertTrue(common.validate_post(sample_post(title="t" * 91)))

    def test_tag_rules(self):
        self.assertTrue(common.validate_post(sample_post(tags=["a", "b", "c", "d", "e"])))
        self.assertTrue(common.validate_post(sample_post(tags=["Data"])))
        self.assertTrue(common.validate_post(sample_post(tags=["data", "data"])))
        self.assertEqual(common.validate_post(sample_post(tags=["c++", "power-bi", "ai"])), [])

    def test_trailing_newline_is_rejected(self):
        for field, value in (("tags", ["data\n"]), ("source", "linkedin\n"), ("id", "abcdef0123\n"), ("date", "2026-09-30\n")):
            with self.subTest(field=field):
                errors = common.validate_post(sample_post(**{field: value}))
                self.assertTrue(any(e.startswith(field) for e in errors), errors)
        self.assertTrue(common.validate_testimonial(sample_testimonial(id="abcdef0123\n")))

    def test_tag_message_lists_the_allowed_characters(self):
        errors = common.validate_post(sample_post(tags=["Data"]))
        self.assertEqual(errors, ["tags: use lowercase letters, digits and - + # . (max 24 characters each)"])

    def test_all_is_reserved_for_tags_and_source(self):
        self.assertIn("tags: 'all' is reserved", common.validate_post(sample_post(tags=["all"])))
        self.assertIn("tags: 'all' is reserved", common.validate_post(sample_post(tags=["data", "all"])))
        self.assertIn("source: 'all' is reserved", common.validate_post(sample_post(source="all")))
        self.assertEqual(common.validate_post(sample_post(source="all-things", tags=["small"])), [])

    def test_unexpected_field_is_reported(self):
        errors = common.validate_post(sample_post(colour="red"))
        self.assertEqual(errors, ["colour: unexpected field"])


class TestimonialValidationTests(unittest.TestCase):
    def test_valid_testimonial_has_no_errors(self):
        self.assertEqual(common.validate_testimonial(sample_testimonial()), [])
        self.assertEqual(common.validate_testimonial(sample_testimonial(consent="public-linkedin", sourceUrl="https://www.linkedin.com/in/x/details/recommendations/")), [])

    def test_consent_is_mandatory_and_limited(self):
        for bad in ("", "pending", "yes", None):
            with self.subTest(consent=bad):
                errors = common.validate_testimonial(sample_testimonial(consent=bad))
                self.assertTrue(any(e.startswith("consent") for e in errors), errors)

    def test_quote_limit_is_four_hundred(self):
        self.assertEqual(common.validate_testimonial(sample_testimonial(quote="q" * 400)), [])
        self.assertTrue(common.validate_testimonial(sample_testimonial(quote="q" * 401)))

    def test_required_text_fields(self):
        for field in ("name", "role", "company"):
            with self.subTest(field=field):
                errors = common.validate_testimonial(sample_testimonial(**{field: " "}))
                self.assertTrue(any(e.startswith(field) for e in errors), errors)

    def test_source_url_must_be_https_when_present(self):
        self.assertTrue(common.validate_testimonial(sample_testimonial(sourceUrl="http://x.example/r")))


class ProjectValidationTests(unittest.TestCase):
    def test_valid_project_has_no_errors(self):
        self.assertEqual(common.validate_project(sample_project()), [])
        self.assertEqual(common.validate_project(sample_project(link="https://github.com/SunilKumar-Official/x")), [])

    def test_rules(self):
        self.assertTrue(common.validate_project(sample_project(short="s" * 101)))
        self.assertTrue(common.validate_project(sample_project(stack=[])))
        self.assertTrue(common.validate_project(sample_project(title="")))
        self.assertTrue(common.validate_project(sample_project(link="http://insecure.example")))


class PublishTests(unittest.TestCase):
    def setUp(self):
        self.paths, self.tmp = make_paths()
        self.addCleanup(self.tmp.cleanup)

    def test_to_public_drops_draft_fields_and_empty_optionals(self):
        draft = sample_testimonial(kind="testimonial", status="draft", note="x", sourceUrl="")
        public = common.to_public(draft)
        for key in ("kind", "status", "note", "sourceUrl"):
            self.assertNotIn(key, public)

    def test_publish_post_writes_file_data_js_and_backup(self):
        common.publish(self.paths, "post", sample_post(url="https://a.example/1", id=common.make_id("https://a.example/1")))
        self.assertEqual(common.publish(self.paths, "post", sample_post()), [])
        self.assertEqual(len(common.load_json(self.paths.posts, [])), 2)
        self.assertIn(sample_post()["id"], self.paths.data_js.read_text(encoding="utf-8"))
        self.assertTrue(list(self.paths.backups.glob("posts.json.*")))

    def test_publish_removes_draft_only_fields(self):
        draft = sample_post(kind="post", status="draft", note="check the date")
        self.assertEqual(common.publish(self.paths, "post", draft), [])
        saved = common.load_json(self.paths.posts, [])[0]
        for key in ("kind", "status", "note"):
            self.assertNotIn(key, saved)

    def test_publish_sorts_newest_first(self):
        common.publish(self.paths, "post", sample_post(url="https://a.example/old", date="2026-01-01", id=common.make_id("https://a.example/old")))
        common.publish(self.paths, "post", sample_post(url="https://a.example/new", date="2026-06-01", id=common.make_id("https://a.example/new")))
        self.assertEqual([p["date"] for p in common.load_json(self.paths.posts, [])], ["2026-06-01", "2026-01-01"])

    def test_publish_refuses_invalid_entry_and_changes_nothing(self):
        errors = common.publish(self.paths, "post", sample_post(title="x"))
        self.assertTrue(any(e.startswith("title") for e in errors))
        self.assertFalse(self.paths.posts.exists())
        self.assertFalse(self.paths.data_js.exists())

    def test_publish_refuses_duplicate_id(self):
        self.assertEqual(common.publish(self.paths, "post", sample_post()), [])
        self.assertEqual(common.publish(self.paths, "post", sample_post()), ["id: already published"])
        self.assertEqual(len(common.load_json(self.paths.posts, [])), 1)

    def test_publish_testimonial_requires_consent(self):
        errors = common.publish(self.paths, "testimonial", sample_testimonial(consent=""))
        self.assertTrue(any(e.startswith("consent") for e in errors))
        self.assertFalse(self.paths.testimonials.exists())
        self.assertEqual(common.publish(self.paths, "testimonial", sample_testimonial()), [])
        self.assertEqual(len(common.load_json(self.paths.testimonials, [])), 1)

    def test_publish_rejects_unknown_kind(self):
        self.assertEqual(common.publish(self.paths, "project", sample_project()), ["kind: cannot publish 'project'"])


if __name__ == "__main__":
    unittest.main()

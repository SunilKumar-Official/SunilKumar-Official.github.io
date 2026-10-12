import csv
import io
import unittest
import zipfile
from contextlib import redirect_stdout
from pathlib import Path

from helpers import FIXTURES, common, make_paths, sample_post
from tools import import_linkedin as imp

FIXTURE_EXPORT = FIXTURES / "linkedin_export"


def write_export(folder, shares=None, recs=None):
    """Write small CSV files. shares/recs are (headers, rows) tuples."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    for name, spec in (("Shares.csv", shares), ("Recommendations_Received.csv", recs)):
        if spec is None:
            continue
        headers, rows = spec
        with open(folder / name, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(headers)
            w.writerows(rows)


JUNK = b"\x00\x05\x16\x07\xff\xfe not a csv \x80"
SHARE_HEADERS = ["Date", "ShareLink", "ShareCommentary"]
REC_HEADERS = ["First Name", "Last Name", "Company", "Job Title", "Text", "Creation Date", "Status"]


class HelperTests(unittest.TestCase):
    def test_parse_date_formats(self):
        self.assertEqual(imp.parse_date("2026-09-30 10:15:00"), "2026-09-30")
        self.assertEqual(imp.parse_date("2026-09-30 10:15:00 UTC"), "2026-09-30")
        self.assertEqual(imp.parse_date("2026-09-30"), "2026-09-30")
        self.assertEqual(imp.parse_date("08/15/26, 10:20 AM"), "2026-08-15")
        self.assertEqual(imp.parse_date("08/15/2026 10:20 AM"), "2026-08-15")
        self.assertEqual(imp.parse_date("Aug 15, 2026"), "2026-08-15")
        self.assertEqual(imp.parse_date("not a date"), "")
        self.assertEqual(imp.parse_date(""), "")

    def test_shorten_cuts_at_a_word_and_adds_ellipsis(self):
        self.assertEqual(imp.shorten("short text", 90), "short text")
        out = imp.shorten("word " * 40, 30)
        self.assertLessEqual(len(out), 30)
        self.assertTrue(out.endswith("…"))
        self.assertNotIn("  ", out)

    def test_collapse_whitespace(self):
        self.assertEqual(imp.collapse("  a \n\n b\tc "), "a b c")


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.paths, self.tmp = make_paths()
        self.addCleanup(self.tmp.cleanup)

    def run_import(self, source):
        return imp.import_export(source, self.paths)

    def test_imports_posts_and_recommendations_as_drafts(self):
        result = self.run_import(FIXTURE_EXPORT)
        self.assertEqual((result.new_posts, result.new_testimonials), (3, 1))
        self.assertEqual(result.skipped_status, 1)
        drafts = common.load_drafts(self.paths)
        posts = [d for d in drafts if d["kind"] == "post"]
        self.assertEqual(len(posts), 3)
        first = next(p for p in posts if p["date"] == "2026-09-30")
        self.assertEqual(first["title"], "Why dashboards fail")
        self.assertTrue(first["excerpt"].startswith("Why dashboards fail Most dashboards"))
        self.assertLessEqual(len(first["excerpt"]), 160)
        self.assertEqual((first["source"], first["sourceLabel"], first["tags"], first["status"]), ("linkedin", "LinkedIn", [], "draft"))
        self.assertEqual(first["id"], common.make_id(first["url"]))

    def test_long_single_line_post_gets_a_shortened_title(self):
        self.run_import(FIXTURE_EXPORT)
        post = next(d for d in common.load_drafts(self.paths) if d.get("date") == "2026-08-12")
        self.assertLessEqual(len(post["title"]), 90)
        self.assertTrue(post["title"].endswith("…"))

    def test_post_without_text_gets_placeholder_title_and_a_note(self):
        self.run_import(FIXTURE_EXPORT)
        post = next(d for d in common.load_drafts(self.paths) if d.get("date") == "2026-07-01")
        self.assertEqual(post["title"], "LinkedIn post")
        self.assertEqual(post["excerpt"], "")
        self.assertIn("no text", post["note"])

    def test_recommendation_becomes_testimonial_draft_without_consent(self):
        self.run_import(FIXTURE_EXPORT)
        t = next(d for d in common.load_drafts(self.paths) if d["kind"] == "testimonial")
        self.assertEqual((t["name"], t["role"], t["company"], t["date"]), ("Asha Rao", "Operations Manager", "Example Co", "2026-08-15"))
        self.assertEqual((t["consent"], t["sourceUrl"]), ("", ""))
        self.assertEqual(t["id"], common.make_id(t["name"], t["date"], t["quote"]))

    def test_hidden_recommendations_are_skipped(self):
        self.run_import(FIXTURE_EXPORT)
        names = [d["name"] for d in common.load_drafts(self.paths) if d["kind"] == "testimonial"]
        self.assertNotIn("Ben Lee", names)

    def test_second_run_adds_nothing(self):
        self.run_import(FIXTURE_EXPORT)
        again = self.run_import(FIXTURE_EXPORT)
        self.assertEqual((again.new_posts, again.new_testimonials), (0, 0))
        self.assertEqual(again.skipped_existing, 4)
        self.assertEqual(len(common.load_drafts(self.paths)), 4)

    def test_discarded_items_are_not_imported_again(self):
        self.run_import(FIXTURE_EXPORT)
        drafts = common.load_drafts(self.paths)
        common.save_drafts(self.paths, drafts[1:])
        common.remember_discarded(self.paths, [drafts[0]["id"]])
        again = self.run_import(FIXTURE_EXPORT)
        self.assertEqual((again.new_posts, again.new_testimonials), (0, 0))
        self.assertEqual(again.skipped_existing, 4)
        self.assertEqual([d["id"] for d in common.load_drafts(self.paths)], [d["id"] for d in drafts[1:]])

    def test_already_published_items_are_skipped(self):
        url = "https://www.linkedin.com/feed/update/urn:li:share:7000000000000000001"
        common.save_json(self.paths.posts, [sample_post(url=url, id=common.make_id(url))])
        result = self.run_import(FIXTURE_EXPORT)
        self.assertEqual(result.new_posts, 2)

    def test_never_writes_to_the_public_data_folder(self):
        self.run_import(FIXTURE_EXPORT)
        self.assertEqual(sorted(p.name for p in self.paths.data.iterdir()), [])

    def test_unreadable_date_is_noted(self):
        write_export(self.paths.root / "exp", shares=(SHARE_HEADERS, [["sometime", "https://l.example/1", "Hello there world"]]))
        self.run_import(self.paths.root / "exp")
        draft = common.load_drafts(self.paths)[0]
        self.assertEqual(draft["date"], "")
        self.assertIn("date could not be read", draft["note"])

    def test_over_long_quote_is_kept_and_noted(self):
        write_export(self.paths.root / "exp", recs=(REC_HEADERS, [["Cara", "Dev", "Co", "Lead", "q" * 450, "01/02/26, 09:00 AM", "VISIBLE"]]))
        self.run_import(self.paths.root / "exp")
        draft = common.load_drafts(self.paths)[0]
        self.assertEqual(len(draft["quote"]), 450)
        self.assertIn("450 characters", draft["note"])

    def test_column_names_match_loosely(self):
        write_export(self.paths.root / "exp", shares=(["date", "sharelink", "sharecommentary"], [["2026-01-02", "https://l.example/2", "Loose headers still work"]]))
        self.assertEqual(self.run_import(self.paths.root / "exp").new_posts, 1)

    def test_missing_required_column_stops_and_changes_nothing(self):
        write_export(self.paths.root / "exp", shares=(["When", "Text"], [["2026-01-02", "no link column"]]))
        with self.assertRaises(imp.ExportFormatError) as ctx:
            self.run_import(self.paths.root / "exp")
        self.assertIn("url", str(ctx.exception))
        self.assertIn("When, Text", str(ctx.exception))
        self.assertFalse(self.paths.drafts.exists())

    def test_one_bad_file_prevents_importing_the_good_one(self):
        write_export(self.paths.root / "exp", shares=(["When"], [["x"]]), recs=(REC_HEADERS, [["A", "B", "C", "D", "Nice work", "01/02/26, 09:00 AM", "VISIBLE"]]))
        with self.assertRaises(imp.ExportFormatError):
            self.run_import(self.paths.root / "exp")
        self.assertFalse(self.paths.drafts.exists())

    def test_zip_input_and_macos_junk_entries(self):
        archive = self.paths.root / "export.zip"
        with zipfile.ZipFile(archive, "w") as z:
            z.writestr("__MACOSX/Basic_LinkedInDataExport/._Recommendations_Received.csv", JUNK)
            z.writestr("__MACOSX/Basic_LinkedInDataExport/._Shares.csv", JUNK)
            z.write(FIXTURE_EXPORT / "Shares.csv", "Basic_LinkedInDataExport/Shares.csv")
            z.write(FIXTURE_EXPORT / "Recommendations_Received.csv", "Basic_LinkedInDataExport/Recommendations_Received.csv")
        result = self.run_import(archive)
        self.assertEqual((result.new_posts, result.new_testimonials), (3, 1))

    def test_zip_junk_listed_first_is_ignored_even_without_a_macosx_folder(self):
        archive = self.paths.root / "export.zip"
        with zipfile.ZipFile(archive, "w") as z:
            z.writestr("Basic_LinkedInDataExport/._Recommendations_Received.csv", JUNK)
            z.write(FIXTURE_EXPORT / "Shares.csv", "Basic_LinkedInDataExport/Shares.csv")
            z.write(FIXTURE_EXPORT / "Recommendations_Received.csv", "Basic_LinkedInDataExport/Recommendations_Received.csv")
        result = self.run_import(archive)
        self.assertEqual((result.new_posts, result.new_testimonials), (3, 1))

    def test_folder_junk_that_sorts_first_is_ignored(self):
        folder = self.paths.root / "exp"
        folder.mkdir()
        (folder / "._Recommendations_Received.csv").write_bytes(JUNK)
        (folder / "._Shares.csv").write_bytes(JUNK)
        macosx = folder / "__MACOSX"
        macosx.mkdir()
        (macosx / "Recommendations_Received.csv").write_bytes(JUNK)
        for name in ("Shares.csv", "Recommendations_Received.csv"):
            (folder / name).write_bytes((FIXTURE_EXPORT / name).read_bytes())
        result = self.run_import(folder)
        self.assertEqual((result.new_posts, result.new_testimonials), (3, 1))

    def test_file_that_is_not_a_zip_gives_a_plain_message(self):
        bad = self.paths.root / "export.zip"
        bad.write_text("this is not a zip file", encoding="utf-8")
        out = io.StringIO()
        with redirect_stdout(out):
            code = imp.main([str(bad)], paths=self.paths)
        self.assertEqual(code, 2)
        self.assertIn("could not read export.zip", out.getvalue())
        self.assertIn("Nothing was changed.", out.getvalue())
        self.assertFalse(self.paths.drafts.exists())

    def test_csv_that_is_not_text_gives_a_plain_message(self):
        folder = self.paths.root / "exp"
        folder.mkdir()
        (folder / "Shares.csv").write_bytes(JUNK)
        out = io.StringIO()
        with redirect_stdout(out):
            code = imp.main([str(folder)], paths=self.paths)
        self.assertEqual(code, 2)
        self.assertIn("could not read Shares.csv", out.getvalue())
        self.assertIn("Nothing was changed.", out.getvalue())

    def test_folder_with_neither_file_is_an_error(self):
        empty = self.paths.root / "empty"
        empty.mkdir()
        with self.assertRaises(imp.ExportFormatError):
            self.run_import(empty)

    def test_main_prints_summary_and_returns_codes(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = imp.main([str(FIXTURE_EXPORT)], paths=self.paths)
        self.assertEqual(code, 0)
        self.assertIn("3 new post draft(s)", out.getvalue())
        self.assertIn("tools/review.py", out.getvalue())
        out = io.StringIO()
        with redirect_stdout(out):
            code = imp.main([str(self.paths.root / "missing")], paths=self.paths)
        self.assertEqual(code, 2)
        self.assertIn("Nothing was changed", out.getvalue())

    def test_main_shows_mapped_headers_for_each_file(self):
        out = io.StringIO()
        with redirect_stdout(out):
            imp.main([str(FIXTURE_EXPORT)], paths=self.paths)
        text = out.getvalue()
        self.assertIn("Shares.csv headers:", text)
        self.assertIn("url <- ShareLink", text)
        self.assertIn("status <- Status", text)

    def test_export_without_status_column_imports_all_recommendations(self):
        write_export(self.paths.root / "exp", recs=(REC_HEADERS[:-1], [
            ["Ann", "Lee", "Co", "Lead", "Solid partner to work with.", "01/02/26, 09:00 AM"],
            ["Bob", "Ray", "Co", "Lead", "Reliable and thorough.", "01/03/26, 09:00 AM"],
        ]))
        out = io.StringIO()
        with redirect_stdout(out):
            code = imp.main([str(self.paths.root / "exp")], paths=self.paths)
        self.assertEqual(code, 0)
        self.assertIn("status <- (not found)", out.getvalue())
        self.assertEqual(len([d for d in common.load_drafts(self.paths) if d["kind"] == "testimonial"]), 2)

    def test_only_visible_statuses_are_imported(self):
        write_export(self.paths.root / "exp", recs=(REC_HEADERS, [
            ["Ann", "Lee", "Co", "Lead", "Visible in lower case.", "01/02/26, 09:00 AM", "visible"],
            ["Bob", "Ray", "Co", "Lead", "This one is archived.", "01/03/26, 09:00 AM", "ARCHIVED"],
            ["Cy", "Fox", "Co", "Lead", "This one has no status.", "01/04/26, 09:00 AM", ""],
        ]))
        result = self.run_import(self.paths.root / "exp")
        self.assertEqual((result.new_testimonials, result.skipped_status), (1, 2))
        self.assertEqual(result.skipped_statuses, ["(blank)", "ARCHIVED"])
        names = [d["name"] for d in common.load_drafts(self.paths)]
        self.assertEqual(names, ["Ann Lee"])

    def test_main_names_skipped_statuses(self):
        write_export(self.paths.root / "exp", recs=(REC_HEADERS, [
            ["Bob", "Ray", "Co", "Lead", "This one is archived.", "01/03/26, 09:00 AM", "ARCHIVED"],
        ]))
        out = io.StringIO()
        with redirect_stdout(out):
            imp.main([str(self.paths.root / "exp")], paths=self.paths)
        self.assertIn("(seen: ARCHIVED)", out.getvalue())


if __name__ == "__main__":
    unittest.main()

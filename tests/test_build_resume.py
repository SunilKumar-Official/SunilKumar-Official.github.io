import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import build_resume

DETAILS = {"email": "someone@example.com", "phone": "+00 00000 00000", "city": "Town", "region": "State", "country": "Land"}


class BuildResumeTests(unittest.TestCase):
    def test_render_template_fills_every_placeholder(self):
        template = build_resume.TEMPLATE.read_text(encoding="utf-8")
        page = build_resume.render_template(template, DETAILS, "<svg></svg>")
        self.assertIn("someone@example.com", page)
        self.assertIn("+00 00000 00000", page)
        self.assertIn("Town, State, Land", page)
        self.assertNotIn("{{", page)

    def test_render_template_rejects_an_unknown_placeholder(self):
        with self.assertRaises(ValueError):
            build_resume.render_template("{{EMAIL}} {{NOPE}}", DETAILS, "")

    def test_location_text_skips_a_missing_region(self):
        self.assertEqual(build_resume.location_text({"city": "A", "country": "B"}), "A, B")

    def test_the_committed_template_holds_no_personal_contact_details(self):
        template = build_resume.TEMPLATE.read_text(encoding="utf-8")
        for placeholder in ("{{EMAIL}}", "{{PHONE}}", "{{LOCATION}}", "{{QR_SITE_SVG}}"):
            self.assertIn(placeholder, template)
        self.assertNotIn("@gmail.com", template)

    def test_count_pdf_pages_counts_page_objects_not_the_pages_tree(self):
        data = b"%PDF-1.4 /Type /Pages /Type /Page\n/Type /Page\n"
        self.assertEqual(build_resume.count_pdf_pages(data), 2)

    def test_the_committed_resume_pdf_is_a_single_page(self):
        data = build_resume.PDF_OUT.read_bytes()
        self.assertTrue(data.startswith(b"%PDF"))
        self.assertEqual(build_resume.count_pdf_pages(data), 1)

    def test_the_resume_qr_code_is_a_real_svg_for_the_pdf_address(self):
        svg = build_resume.QR_OUT.read_text(encoding="utf-8")
        self.assertIn("<svg", svg)
        self.assertIn("Sunil-Kumar-Resume.pdf", build_resume.PDF_URL)


if __name__ == "__main__":
    unittest.main()

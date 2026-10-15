import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import generate_pages


class GeneratePagesTests(unittest.TestCase):
    """Generates the whole site into a fresh temp directory once per test (setUp),
    never into the real repo paths — generate_pages.main() defaults to writing
    the real site, which later tasks' tests must not do as a side effect of
    running the suite. self.out is the generated site's root for this test run.
    Each task appends its own route-reading test method to this class; read
    pages via self.page("<route>") rather than touching ROOT directly."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.out = Path(self._tmp.name)
        generate_pages.main(output_root=self.out)

    def page(self, route):
        """Read a generated page's HTML by route ("" for Home, "about" for /about/, etc.)."""
        out_dir = self.out / route if route else self.out
        return (out_dir / "index.html").read_text(encoding="utf-8")

    def test_home_page_is_written_with_shared_chrome_and_content(self):
        home = self.page("")
        self.assertIn('<link rel="stylesheet" href="/assets/site.css">', home)
        self.assertIn('href="/about/"', home)         # nav link present
        self.assertIn('<body class="home">', home)    # Home gets the full-bleed hero layout
        self.assertIn("I turn<br>data into<br>decisions.", home)  # content fragment included
        self.assertIn("Business Analysis &middot; BI &middot; Data Engineering", home)
        self.assertIn("Explore projects", home)
        self.assertIn("Insight, engineered.", home)
        self.assertIn("Sunil Kumar", home)             # wordmark present
        # Home is reached through the wordmark, so no primary nav item is marked active.
        nav = home.split('<nav class="site-nav"')[1].split("</nav>")[0]
        self.assertNotIn('class="on"', nav)

    def test_about_page_has_content_and_active_nav(self):
        about = self.page("about")
        self.assertIn('href="/about/" class="on"', about)
        # Checking the distinctive opening words, not the full sentence with its
        # apostrophe, since that character may or may not be HTML-escaped depending
        # on how the fragment is authored — this assertion is robust to either.
        self.assertIn("I didn", about)
        self.assertIn("large-scale data management", about)

    def test_nav_marks_contact_active_on_the_contact_page(self):
        contact = self.page("contact")
        self.assertIn('href="/contact/" class="on"', contact)
        self.assertIn("linkedin.com/in/sunilkumar-kannan", contact)
        self.assertIn("github.com/SunilKumar-Official", contact)


    def test_experience_page_renders_career_data(self):
        experience = self.page("experience")
        self.assertIn('href="/experience/" class="on"', experience)
        self.assertIn('id="careerTimeline"', experience)
        self.assertIn("<script src=\"/data/data.js\">", experience)

    def test_testimonials_page_has_rendering_target_and_data_script(self):
        testimonials = self.page("testimonials")
        self.assertIn('id="tsGrid"', testimonials)
        self.assertIn('src="/data/data.js"', testimonials)

    def test_posts_page_has_rendering_target_and_data_script(self):
        posts = self.page("posts")
        self.assertIn('id="poList"', posts)
        self.assertIn('id="poFilters"', posts)
        self.assertIn('src="/data/data.js"', posts)

    def test_projects_index_links_to_all_three_case_studies(self):
        index = self.page("projects")
        self.assertIn('href="/projects/kpi-scoring-pipeline/"', index)
        self.assertIn('href="/projects/customer-support-data-platform/"', index)
        self.assertIn('href="/projects/conversation-intelligence-platform/"', index)
        self.assertIn('id="pjTiles"', index)  # the two lighter projects still render from data.js

    def test_each_case_study_page_covers_all_eight_template_sections(self):
        for slug in ("kpi-scoring-pipeline", "customer-support-data-platform", "conversation-intelligence-platform"):
            page = self.page(f"projects/{slug}")
            for heading in ("<h2>Business problem</h2>", "<h2>My contribution</h2>",
                             "<h2>Data &amp; tools</h2>", "<h2>Scope &amp; scale</h2>",
                             "<h2>Approach</h2>", "<h2>Outcome</h2>", "<h2>Evidence</h2>",
                             "<h2>Limitations &amp; what's next</h2>"):
                self.assertIn(heading, page, f"{slug} is missing the '{heading}' section")

    def test_each_case_study_page_links_back_to_all_projects(self):
        for slug in ("kpi-scoring-pipeline", "customer-support-data-platform", "conversation-intelligence-platform"):
            page = self.page(f"projects/{slug}")
            self.assertIn('href="/projects/"', page)

    def test_every_planned_route_has_no_console_breaking_absolute_links(self):
        for route, _fragment, _title, _desc in generate_pages.PAGES:
            page = self.page(route)
            self.assertIn('href="/assets/site.css"', page)
            # no leftover single-page hash links (the skip link's #main is the one allowed anchor)
            self.assertEqual([h for h in __import__("re").findall(r'href="(#[^"]*)"', page) if h != "#main"], [])

    def test_ten_routes_are_defined(self):
        self.assertEqual(len(generate_pages.PAGES), 10)

    def test_og_tags_are_present_and_url_is_per_route(self):
        home = self.page("")
        about = self.page("about")
        self.assertIn('property="og:title" content="Sunil Kumar | Business Intelligence & Data Solutions Specialist"', home)
        self.assertIn('property="og:title" content="About | Sunil Kumar"', about)
        self.assertIn('property="og:url" content="https://sunilkumar-official.github.io/"', home)
        self.assertIn('property="og:url" content="https://sunilkumar-official.github.io/about/"', about)
        home_url_line = [l for l in home.splitlines() if 'property="og:url"' in l][0]
        about_url_line = [l for l in about.splitlines() if 'property="og:url"' in l][0]
        self.assertNotEqual(home_url_line, about_url_line)

    def test_primary_nav_has_exactly_four_items_and_excludes_testimonials_and_posts(self):
        self.assertEqual(len(generate_pages.NAV_ITEMS), 4)
        nav_routes = [route for route, _label in generate_pages.NAV_ITEMS]
        self.assertEqual(nav_routes, ["about", "experience", "projects", "contact"])
        self.assertNotIn("testimonials", nav_routes)
        self.assertNotIn("posts", nav_routes)

    def test_every_page_has_skip_link_and_an_accessible_menu_button(self):
        for route, _fragment, _title, _desc in generate_pages.PAGES:
            page = self.page(route)
            self.assertIn('<a class="skip" href="#main">', page)
            self.assertIn('<main class="page" id="main">', page)
            self.assertIn('aria-controls="menu"', page)
            self.assertIn('aria-expanded="false"', page)

    def test_phone_menu_lists_home_nav_and_the_extra_links(self):
        menu = self.page("about").split('id="menu"')[1].split("</div>\n</div>")[0]
        for href in ('href="/"', 'href="/about/"', 'href="/experience/"', 'href="/projects/"', 'href="/contact/"',
                     "linkedin.com/in/sunilkumar-kannan", "github.com/SunilKumar-Official",
                     'href="/assets/Sunil-Kumar-Resume.pdf"'):
            self.assertIn(href, menu)

    def test_body_class_marks_home_and_each_section(self):
        self.assertEqual(generate_pages.body_class(""), "home")
        self.assertEqual(generate_pages.body_class("about"), "page-about")
        self.assertEqual(generate_pages.body_class("projects/kpi-scoring-pipeline"), "page-projects")

    def test_contact_page_offers_the_resume_download_and_qr(self):
        contact = self.page("contact")
        self.assertIn('href="/assets/Sunil-Kumar-Resume.pdf" download', contact)
        self.assertIn('src="/assets/qr-resume.svg"', contact)
        self.assertIn("Scan to download", contact)

    def test_every_page_uses_the_new_icon_set_and_a_current_link_preview_image(self):
        for route, _fragment, _title, _desc in generate_pages.PAGES:
            page = self.page(route)
            self.assertIn('href="/assets/favicon.svg?v=3"', page)
            self.assertIn('href="/assets/apple-touch-icon.png?v=3"', page)
            self.assertIn("assets/og-image.png?v=6", page)
            self.assertNotIn("data:image/svg+xml", page)  # the old inline red "SK" icon is gone

    def test_every_page_links_to_the_resume_pdf(self):
        for route, _fragment, _title, _desc in generate_pages.PAGES:
            self.assertIn('href="/assets/Sunil-Kumar-Resume.pdf" download', self.page(route),
                          f"{route or '(root)'} has no resume link")

    def test_rail_dots_are_one_per_main_page_and_ring_the_current_one(self):
        import re
        expected = {"": "Home", "about": "About", "experience": "Experience", "projects": "Projects", "contact": "Contact"}
        for route, section in [("", ""), ("about", "about"), ("experience", "experience"), ("projects", "projects"),
                               ("projects/kpi-scoring-pipeline", "projects"), ("contact", "contact")]:
            rail = self.page(route).split('<nav class="rail"')[1].split("</nav>")[0]
            labels = re.findall(r'data-label="([^"]+)"', rail)
            self.assertEqual(labels, list(expected.values()))
            on = re.findall(r'<a href="[^"]*" class="on" data-label="([^"]+)"', rail)
            self.assertEqual(on, [expected[section]], f"{route or '(root)'} rings the wrong dot")
        for route in ("testimonials", "posts"):
            rail = self.page(route).split('<nav class="rail"')[1].split("</nav>")[0]
            self.assertNotIn('class="on"', rail)

    def test_every_page_loads_the_swipe_script_and_it_exists(self):
        for route, _fragment, _title, _desc in generate_pages.PAGES:
            self.assertIn('<script src="/assets/swipe.js" defer></script>', self.page(route),
                          f"{route or '(root)'} does not load swipe.js")
        self.assertTrue((generate_pages.ROOT / "assets" / "swipe.js").is_file())

    def test_every_local_asset_a_page_or_the_stylesheet_points_to_exists(self):
        import re
        refs = set()
        for route, _fragment, _title, _desc in generate_pages.PAGES:
            refs.update(re.findall(r'(?:href|src)="(/(?:assets|data)/[^"?#]+)', self.page(route)))
        css = (generate_pages.ROOT / "assets" / "site.css").read_text(encoding="utf-8")
        refs.update(re.findall(r"url\((/assets/[^)?#]+)", css))
        self.assertTrue(refs)
        for ref in sorted(refs):
            self.assertTrue((generate_pages.ROOT / ref.lstrip("/")).is_file(), f"{ref} is referenced but missing")

    def test_no_generated_page_exposes_an_email_address_or_phone_number(self):
        import re
        email = re.compile(r"[\w.+-]+@[\w-]+\.[a-z]{2,}", re.I)
        phone = re.compile(r"(?<!\d)\+?\d[\d\s().-]{8,}\d(?!\d)")
        for route, _fragment, _title, _desc in generate_pages.PAGES:
            page = self.page(route)
            self.assertIsNone(email.search(page), f"email-like text on {route or '(root)'}")
            self.assertIsNone(phone.search(re.sub(r"<svg.*?</svg>|(?:href|src)=\"data:[^\"]*\"", "", page, flags=re.S)), f"phone-like text on {route or '(root)'}")

    def test_every_page_has_a_non_empty_title_tag(self):
        for route, _fragment, title, _desc in generate_pages.PAGES:
            self.assertIn(f"<title>{title}</title>", self.page(route))

    def test_committed_site_matches_fresh_generator_output(self):
        for route, _fragment, _title, _desc in generate_pages.PAGES:
            committed_dir = generate_pages.ROOT / route if route else generate_pages.ROOT
            committed = (committed_dir / "index.html").read_text(encoding="utf-8")
            generated = self.page(route)
            self.assertEqual(committed, generated,
                              f"committed {route or '(root)'} differs from fresh generator output — "
                              f"re-run python3 tools/generate_pages.py")


if __name__ == "__main__":
    unittest.main()

"""Loads the real index.html in headless Chrome with sample data and checks what it renders.

Skipped automatically when Chrome or Chromium is not installed.
"""
import html
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from helpers import ROOT, common, sample_post, sample_project, sample_testimonial

CANDIDATES = ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              "/Applications/Chromium.app/Contents/MacOS/Chromium",
              "google-chrome", "chromium", "chromium-browser")


def find_chrome():
    for c in CANDIDATES:
        found = c if os.path.isabs(c) and os.path.exists(c) else shutil.which(c)
        if found:
            return found
    return None


PROBE = r"""
<script>
window.__errors = [];
window.addEventListener('error', function(e){ window.__errors.push(e.message); });
setTimeout(function(){
  var q = function(s){ return Array.prototype.slice.call(document.querySelectorAll(s)); };
  var txt = function(el){ return el.textContent.trim(); };
  var visible = function(){ return q('.po').filter(function(r){ return r.style.display !== 'none'; }).map(function(r){ return txt(r.querySelector('.mid b')); }); };
  var click = function(sel, i){ q(sel)[i].click(); };
  var r = {};
  r.errors = window.__errors;
  r.postTitles = q('.po .mid b').map(txt);
  r.postHrefs = q('a.po').map(function(a){ return a.getAttribute('href'); });
  r.postDates = q('.po .dt').map(txt);
  r.sub = txt(document.getElementById('poSub'));
  r.sourceChips = q('.chips[data-g=src] button').map(txt);
  r.tagChips = q('.chips[data-g=tag] button').map(txt);
  r.testimonialNames = q('.q .who b').map(txt);
  r.initials = q('.q .av').map(txt);
  r.verifiedLinks = q('.q .vs').map(function(a){ return a.getAttribute('href'); });
  r.tileTitles = q('#pjTiles .tile b').map(txt);
  r.projectSub = txt(document.getElementById('pjSub'));
  r.description = (document.querySelector('meta[name=description]') || {}).content || '';
  r.favicon = !!document.querySelector('link[rel=icon]');
  var tile = q('#pjTiles .tile')[0];
  if (tile) {
    var key = function(el, k){ el.dispatchEvent(new KeyboardEvent('keydown', {key: k, bubbles: true, cancelable: true})); };
    r.tileRole = tile.getAttribute('role'); r.tileTabindex = tile.getAttribute('tabindex');
    key(tile, 'Enter');
    r.openAfterEnter = document.getElementById('p-projects').classList.contains('open');
    key(document.getElementById('pdFwd'), 'Enter');
    r.countAfterArrow = txt(document.getElementById('pdCount'));
    key(document.getElementById('pback'), ' ');
    r.closedAfterSpace = !document.getElementById('p-projects').classList.contains('open');
  }
  r.injectedElements = q('.po .mid b *').length;
  if (r.postTitles.length) {
    click('.chips[data-g=src] button', 2); r.afterSource = visible();
    click('.chips[data-g=tag] button', 1); r.afterSourceAndTag = visible();
    click('.chips[data-g=src] button', 1); r.afterNoMatch = visible();
    r.emptyShownWhenNoMatch = document.getElementById('empty').style.display;
    r.emptyTextWhenNoMatch = txt(document.getElementById('empty'));
    click('.chips[data-g=src] button', 0); click('.chips[data-g=tag] button', 0); r.afterReset = visible();
    r.emptyHiddenAfterReset = document.getElementById('empty').style.display;
  }
  r.emptyText = txt(document.getElementById('empty') || document.body);
  r.tsEmpty = txt(document.getElementById('tsGrid'));
  var out = document.createElement('pre'); out.id = 'probe'; out.textContent = JSON.stringify(r);
  document.body.appendChild(out);
}, 600);
</script>
"""

SAMPLE_POSTS = [
    sample_post(url="https://www.linkedin.com/posts/a", id=common.make_id("https://www.linkedin.com/posts/a"),
                title="R&D <3 dashboards", date="2026-09-30", tags=["data", "bi"]),
    sample_post(url="https://community.example/p/1", id=common.make_id("https://community.example/p/1"),
                title="Window functions in practice", date="2026-10-05", source="data-community", sourceLabel="Data Community", tags=["sql"]),
    sample_post(url="https://www.linkedin.com/posts/b", id=common.make_id("https://www.linkedin.com/posts/b"),
                title="Forecasting basics", date="2026-08-12", tags=["ai", "data"]),
]
SAMPLE_TESTIMONIALS = [
    sample_testimonial(),
    sample_testimonial(name="Ben Lee", quote="Reliable and clear.", date="2026-09-01", consent="public-linkedin",
                       sourceUrl="https://www.linkedin.com/in/sunilkumar-BI/details/recommendations/"),
]


@unittest.skipUnless(find_chrome(), "Chrome or Chromium is not installed")
class PageTests(unittest.TestCase):
    def render(self, posts=(), testimonials=(), projects=(), hash_=""):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        site = Path(tmp.name)
        shutil.copy(ROOT / "index.html", site / "index.html")
        shutil.copytree(ROOT / "assets", site / "assets")
        paths = common.Paths(site)
        common.save_json(paths.posts, list(posts))
        common.save_json(paths.testimonials, list(testimonials))
        common.save_json(paths.projects, list(projects))
        common.write_data_js(paths)
        page = (site / "index.html").read_text(encoding="utf-8").replace("</body>", PROBE + "</body>")
        (site / "index.html").write_text(page, encoding="utf-8")
        result = subprocess.run([find_chrome(), "--headless=new", "--disable-gpu", "--virtual-time-budget=8000", "--dump-dom",
                                 f"file://{site}/index.html{hash_}"], capture_output=True, text=True, timeout=120)
        start = result.stdout.find('<pre id="probe">')
        self.assertNotEqual(start, -1, "page did not finish rendering:\n" + result.stdout[-500:])
        body = result.stdout[start + len('<pre id="probe">'):result.stdout.index("</pre>", start)]
        return json.loads(html.unescape(body))

    def test_posts_render_newest_first_with_filters_built_from_data(self):
        r = self.render(posts=SAMPLE_POSTS, hash_="#posts")
        self.assertEqual(r["errors"], [])
        self.assertEqual(r["postTitles"], ["Window functions in practice", "R&D <3 dashboards", "Forecasting basics"])
        self.assertEqual(r["postDates"], ["Oct 2026", "Sep 2026", "Aug 2026"])
        self.assertEqual(r["sub"], "3 posts · newest first")
        self.assertEqual(r["sourceChips"], ["All", "Data Community", "LinkedIn"])
        self.assertEqual(r["tagChips"], ["All", "ai", "bi", "data", "sql"])
        self.assertTrue(all(h.startswith("https://") for h in r["postHrefs"]))

    def test_post_text_is_escaped_not_interpreted_as_html(self):
        r = self.render(posts=SAMPLE_POSTS, hash_="#posts")
        self.assertEqual(r["injectedElements"], 0)

    def test_source_and_tag_filters_combine(self):
        r = self.render(posts=SAMPLE_POSTS, hash_="#posts")
        self.assertEqual(r["afterSource"], ["R&D <3 dashboards", "Forecasting basics"])        # source: LinkedIn
        self.assertEqual(r["afterSourceAndTag"], ["Forecasting basics"])                        # LinkedIn and tag "ai"
        self.assertEqual(r["afterNoMatch"], [])                                                 # Data Community and tag "ai"
        self.assertEqual(r["emptyShownWhenNoMatch"], "block")
        self.assertEqual(r["emptyTextWhenNoMatch"], "No posts match these filters.")
        self.assertEqual(r["afterReset"], ["Window functions in practice", "R&D <3 dashboards", "Forecasting basics"])
        self.assertEqual(r["emptyHiddenAfterReset"], "none")

    def test_testimonials_render_with_initials_and_verified_link_only_when_given(self):
        r = self.render(testimonials=SAMPLE_TESTIMONIALS, hash_="#testimonials")
        self.assertEqual(r["errors"], [])
        self.assertEqual(r["testimonialNames"], ["Ben Lee", "Asha Rao"])                        # newest first
        self.assertEqual(r["initials"], ["BL", "AR"])
        self.assertEqual(r["verifiedLinks"], ["https://www.linkedin.com/in/sunilkumar-BI/details/recommendations/"])

    def test_projects_render_from_data(self):
        r = self.render(projects=[sample_project(), sample_project(title="Daily KPI Email Report")], hash_="#projects")
        self.assertEqual(r["errors"], [])
        self.assertEqual(r["tileTitles"], ["KPI Scoring Pipeline", "Daily KPI Email Report"])
        self.assertEqual(r["projectSub"], "2 projects · pick one to open")

    def test_project_tiles_arrows_and_back_link_work_from_the_keyboard(self):
        r = self.render(projects=[sample_project(), sample_project(title="Daily KPI Email Report")], hash_="#projects")
        self.assertEqual(r["errors"], [])
        self.assertEqual((r["tileRole"], r["tileTabindex"]), ("button", "0"))
        self.assertTrue(r["openAfterEnter"])
        self.assertEqual(r["countAfterArrow"], "02 / 02")
        self.assertTrue(r["closedAfterSpace"])

    def test_page_has_a_description_and_an_icon(self):
        r = self.render()
        self.assertIn("Business Intelligence Specialist", r["description"])
        self.assertTrue(r["favicon"])

    def test_empty_site_shows_friendly_messages_and_no_errors(self):
        r = self.render()
        self.assertEqual(r["errors"], [])
        self.assertEqual(r["tsEmpty"], "Testimonials will appear here soon.")
        self.assertEqual(r["emptyText"], "No posts yet.")
        self.assertEqual(r["sub"], "Posts will appear here soon.")
        self.assertEqual(r["projectSub"], "Projects will appear here soon.")

    def test_real_repo_data_loads_without_errors(self):
        data = common.load_public(common.Paths())
        r = self.render(posts=data["posts"], testimonials=data["testimonials"], projects=data["projects"])
        self.assertEqual(r["errors"], [])
        self.assertEqual(len(r["tileTitles"]), len(data["projects"]))


if __name__ == "__main__":
    unittest.main()

"""Shared test helpers: a throwaway repo layout and valid sample records."""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import common  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def make_paths():
    """Return (Paths, TemporaryDirectory). Keep the directory object alive for the test's duration."""
    tmp = tempfile.TemporaryDirectory()
    paths = common.Paths(tmp.name)
    paths.data.mkdir(parents=True)
    return paths, tmp


def scripted(*answers):
    """An input() replacement that returns the answers in order, then behaves like end-of-input."""
    it = iter(answers)

    def inp(prompt=""):
        try:
            return next(it)
        except StopIteration:
            raise EOFError
    return inp


def sample_post(**over):
    url = over.pop("url", "https://www.linkedin.com/posts/sunilkumar-bi_example-activity-1")
    post = {
        "id": common.make_id(url),
        "source": "linkedin",
        "sourceLabel": "LinkedIn",
        "title": "Why dashboards fail",
        "excerpt": "Most dashboards fail because nobody asked what decision they support.",
        "date": "2026-09-30",
        "url": url,
        "tags": ["data", "bi"],
    }
    post.update(over)
    return post


def sample_testimonial(**over):
    t = {
        "name": "Asha Rao",
        "role": "Operations Manager",
        "company": "Example Co",
        "quote": "Sunil turned a messy manual process into a report we trust every morning.",
        "date": "2026-08-15",
        "consent": "written",
    }
    t.update(over)
    t.setdefault("id", common.make_id(t["name"], t["date"], t["quote"]))
    return t


def sample_project(**over):
    p = {
        "title": "KPI Scoring Pipeline",
        "type": "Automation",
        "short": "Automated monthly KPI scoring for 100+ employees.",
        "desc": "Automated monthly KPI scoring for 100+ employees, replacing a manual process.",
        "stack": ["SQL", "Python"],
        "role": "Built and automated",
        "outcome": "Replaced a manual monthly process",
    }
    p.update(over)
    return p

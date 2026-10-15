"""Generate the multi-page static site from _templates/ + _content/.

Usage: python3 tools/generate_pages.py
Run after editing _templates/, _content/, or the PAGES list below.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "_templates"
CONTENT = ROOT / "_content"

# (route, content fragment path relative to _content/, page title, meta description)
# route "" is the site root (writes to index.html, not a subfolder).
PAGES = [
    ("", "home.html",
     "Sunil Kumar | Business Intelligence & Data Solutions Specialist",
     "Sunil Kumar, Business Intelligence & Data Solutions Specialist. Operational understanding, analytics and data engineering for reliable data solutions."),
    ("about", "about.html",
     "About | Sunil Kumar",
     "How Sunil Kumar went from customer service and workforce management into Business Intelligence and data engineering."),
    ("contact", "contact.html",
     "Contact | Sunil Kumar",
     "Get in touch with Sunil Kumar on LinkedIn or GitHub."),
    ("experience", "experience.html",
     "Experience | Sunil Kumar",
     "Sunil Kumar's career progression from customer service through Business Intelligence."),
    ("testimonials", "testimonials.html",
     "Testimonials | Sunil Kumar",
     "What colleagues and managers say about working with Sunil Kumar."),
    ("posts", "posts.html",
     "Posts | Sunil Kumar",
     "Posts and articles by Sunil Kumar on BI, data analysis, and automation."),
    ("projects", "projects-index.html",
     "Projects | Sunil Kumar",
     "BI and data engineering case studies and projects by Sunil Kumar."),
    ("projects/kpi-scoring-pipeline", "case-studies/kpi-scoring-pipeline.html",
     "KPI Scoring Pipeline | Sunil Kumar",
     "Case study: standardizing a fragmented KPI methodology into one automated scoring pipeline."),
    ("projects/customer-support-data-platform", "case-studies/customer-support-data-platform.html",
     "Customer Support Data Platform | Sunil Kumar",
     "Case study: a three-stage Dagster data pipeline, a production incident, and a measured reliability fix."),
    ("projects/conversation-intelligence-platform", "case-studies/conversation-intelligence-platform.html",
     "Conversation Intelligence Platform | Sunil Kumar",
     "Case study: a deterministic conversation-analytics pipeline and a rigorously evaluated local LLM analysis layer."),
]

# Primary navigation. Home is reached through the wordmark, so it is not listed here.
NAV_ITEMS = [
    ("about", "About"),
    ("experience", "Experience"),
    ("projects", "Projects"),
    ("contact", "Contact"),
]


def read(path):
    return path.read_text(encoding="utf-8")


def nav_html(route, items=None, indent="    "):
    active_section = route.split("/")[0]
    links = []
    for item_route, label in (items if items is not None else NAV_ITEMS):
        item_section = item_route.split("/")[0]
        on = ' class="on" aria-current="page"' if (item_section and item_section == active_section) or (not item_route and not route) else ""
        href = "/" if item_route == "" else f"/{item_route}/"
        links.append(f'{indent}<a href="{href}"{on}>{label}</a>')
    return "\n".join(links)


def rail_html(route):
    """The dots on the left rail: one per main page (Home plus the primary nav), the current one ringed.
    Pages outside that set (testimonials, posts) ring none. The dots duplicate the primary nav for
    pointer users, so they are skipped by keyboard and screen readers."""
    section = route.split("/")[0]
    dots = []
    for item_route, label in [("", "Home")] + NAV_ITEMS:
        on = (item_route == "" and not route) or (item_route != "" and item_route == section)
        href = "/" if item_route == "" else f"/{item_route}/"
        cls = ' class="on"' if on else ""
        dots.append(f'  <a href="{href}"{cls} data-label="{label}" tabindex="-1" aria-hidden="true"><i></i></a>')
    return "\n".join(dots)


def body_class(route):
    return "home" if not route else "page-" + route.split("/")[0]


def main(output_root=None):
    """Generate every page in PAGES. output_root defaults to the repo root (real
    site files) — pass a temp directory in tests so they never write into the
    live, tracked site structure."""
    out_root = Path(output_root) if output_root else ROOT
    shell = read(TEMPLATES / "page_shell.html")
    footer = read(TEMPLATES / "footer.html")
    for route, fragment, title, description in PAGES:
        content = read(CONTENT / fragment)
        url = f"https://sunilkumar-official.github.io/{route}/" if route else "https://sunilkumar-official.github.io/"
        page = (
            shell
            .replace("{{TITLE}}", title)
            .replace("{{DESCRIPTION}}", description)
            .replace("{{URL}}", url)
            .replace("{{BODY_CLASS}}", body_class(route))
            .replace("{{RAIL_DOTS}}", rail_html(route))
            .replace("{{NAV_LINKS}}", nav_html(route))
            .replace("{{MENU_LINKS}}", nav_html(route, [("", "Home")] + NAV_ITEMS))
            .replace("{{CONTENT}}", content)
            .replace("{{FOOTER}}", footer)
        )
        out_dir = out_root / route if route else out_root
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "index.html"
        out_path.write_text(page, encoding="utf-8")
        print(f"wrote {out_path}")


if __name__ == "__main__":
    main()

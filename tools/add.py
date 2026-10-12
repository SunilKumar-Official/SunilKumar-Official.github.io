"""Add one post or testimonial without a LinkedIn export (other communities, single items).

Usage: python3 tools/add.py post [--draft]
       python3 tools/add.py testimonial [--draft]
Without --draft the entry is published straight to the public data files after validation.
With --draft it is saved to private/drafts.json instead (use python3 tools/review.py later).
A testimonial cannot be published without consent: 1 = written (a saved email or message), 2 = public on LinkedIn.
"""
import argparse
import sys
from datetime import date
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools import common  # noqa: E402
from tools.review import parse_value  # noqa: E402

CONSENT_CHOICES = {"1": "written", "2": "public-linkedin"}


def ask(inp, label, default=""):
    suffix = f" [{default}]" if default else ""
    return inp(f"{label}{suffix}: ").strip() or default


def default_label(source):
    return "LinkedIn" if source == "linkedin" else source.replace("-", " ").title()


def ask_consent(inp, out, tries=3):
    """Ask the consent question; an unrecognised answer is explained and asked again, then treated as blank."""
    for _ in range(tries):
        answer = ask(inp, "Consent: 1 = written, 2 = public on LinkedIn, blank = none")
        if answer == "":
            return ""
        if answer in CONSENT_CHOICES:
            return CONSENT_CHOICES[answer]
        out("Please answer 1, 2 or leave blank.")
    return ""


def collect_post(inp, out, today):
    url = ask(inp, "Post link (https://...)")
    title = ask(inp, "Title")
    excerpt = ask(inp, "Excerpt (one or two lines, up to 160 characters)")
    when = ask(inp, "Date (YYYY-MM-DD)", today)
    source = ask(inp, "Source slug, e.g. linkedin or data-community", "linkedin").lower()
    label = ask(inp, "Source label", default_label(source))
    tags = parse_value("tags", ask(inp, "Tags (comma separated, 1 to 4)"))
    return {"id": common.make_id(url), "source": source, "sourceLabel": label, "title": title,
            "excerpt": excerpt, "date": when, "url": url, "tags": tags}


def collect_testimonial(inp, out, today):
    name = ask(inp, "Name")
    role = ask(inp, "Role")
    company = ask(inp, "Company")
    quote = ask(inp, "Quote (their words, up to 400 characters)")
    when = ask(inp, "Date of the quote (YYYY-MM-DD)", today)
    consent = ask_consent(inp, out)
    source_url = ask(inp, "Source link (optional, https://...)")
    return {"id": common.make_id(name, when, quote), "name": name, "role": role, "company": company,
            "quote": quote, "date": when, "consent": consent, "sourceUrl": source_url}


COLLECTORS = {"post": collect_post, "testimonial": collect_testimonial}


def add(kind, paths, inp=input, out=print, draft=False, today=None):
    """Collect one entry, confirm, then publish or save as a draft. Returns 0 if saved, 1 otherwise."""
    entry = COLLECTORS[kind](inp, out, today or date.today().isoformat())
    public = common.to_public(entry)
    errors = [] if draft else common.validate(kind, public)
    if errors:
        out("Cannot publish:")
        for e in errors:
            out(f"  - {e}")
        if any(e.startswith("consent") for e in errors):
            out("Use --draft to keep it private until you have consent.")
        return 1
    out("")
    for key, value in public.items():
        out(f"  {key:12}: {', '.join(value) if isinstance(value, list) else value}")
    if ask(inp, "Save? (y/n)", "n").lower() != "y":
        out("Not saved.")
        return 1
    if draft:
        drafts = common.load_drafts(paths)
        known = {d.get("id") for d in drafts} | {i.get("id") for i in common.load_json(paths.posts if kind == "post" else paths.testimonials, [])}
        if entry["id"] in known:
            out("This item is already in your drafts or published.")
            return 1
        common.save_drafts(paths, drafts + [{"kind": kind, "status": "draft", **entry}])
        out("Saved to private/drafts.json. Run python3 tools/review.py to publish it.")
        return 0
    errors = common.publish(paths, kind, entry)
    if errors:
        out("Cannot publish:")
        for e in errors:
            out(f"  - {e}")
        return 1
    out("Published. Run python3 tools/check.py, then commit and push.")
    return 0


def main(argv=None, paths=None, inp=input, out=print, today=None):
    parser = argparse.ArgumentParser(prog="add.py", description="Add one post or testimonial.")
    parser.add_argument("kind", choices=sorted(COLLECTORS))
    parser.add_argument("--draft", action="store_true", help="save privately instead of publishing")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        return add(args.kind, paths or common.Paths(), inp, out, draft=args.draft, today=today)
    except EOFError:
        out("\nCancelled. Nothing was saved.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

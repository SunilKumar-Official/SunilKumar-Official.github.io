"""Check the public data before pushing.

Usage: python3 tools/check.py
Exit code 0 = no errors (warnings may still be printed); 1 = errors that should be fixed first.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools import common  # noqa: E402

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"\+?\d[\d\s().-]{7,}\d")
LINK_KEYS = {"url", "sourceUrl", "link", "id"}
SINGLE_USE_TAG_MIN_POSTS = 5


def _strings(value, key=""):
    if isinstance(value, dict):
        for k, v in value.items():
            yield from _strings(v, k)
    elif isinstance(value, list):
        for v in value:
            yield from _strings(v, key)
    elif isinstance(value, str):
        yield key, value


def _looks_like_phone(text):
    for match in PHONE_RE.finditer(text):
        chunk = match.group(0).strip()
        digits = re.sub(r"\D", "", chunk)
        if len(digits) >= 9 and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", chunk):
            return True
    return False


def _duplicates(values):
    return [v for v, n in Counter(values).items() if v and n > 1]


def _load_list(path, errors):
    """Read one public JSON file. Returns (list, readable). Problems become readable errors, never exceptions."""
    label = f"data/{path.name}"
    if not path.exists():
        return [], True
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        errors.append(f"{label} is not valid JSON: {e}")
        return [], False
    except (OSError, UnicodeDecodeError) as e:
        errors.append(f"{label} could not be read: {e}")
        return [], False
    if not isinstance(value, list):
        errors.append(f"{label} must contain a list")
        return [], False
    return value, True


def run_checks(paths):
    """Return (errors, warnings), both lists of readable strings."""
    errors, warnings = [], []
    raw, readable = {}, True
    for key, path in (("posts", paths.posts), ("testimonials", paths.testimonials), ("projects", paths.projects), ("career", paths.career)):
        raw[key], ok = _load_list(path, errors)
        readable = readable and ok
    # Entries that are not objects are reported and left out of every other check.
    data = {}
    for key, items in raw.items():
        data[key] = [item for item in items if isinstance(item, dict)]
        errors += [f"{key}[{i}] is not an object" for i, item in enumerate(items) if not isinstance(item, dict)]
    positions = {key: [i for i, item in enumerate(items) if isinstance(item, dict)] for key, items in raw.items()}

    for kind, key in (("post", "posts"), ("testimonial", "testimonials"), ("project", "projects"), ("career", "career")):
        for i, item in zip(positions[key], data[key]):
            name = item.get("title") or item.get("name") or "?"
            errors += [f"{key}[{i}] '{name}': {e}" for e in common.validate(kind, item)]

    errors += [f"posts: duplicate id {v}" for v in _duplicates([p.get("id") for p in data["posts"]])]
    errors += [f"posts: duplicate url {v}" for v in _duplicates([p.get("url") for p in data["posts"]])]
    errors += [f"testimonials: duplicate id {v}" for v in _duplicates([t.get("id") for t in data["testimonials"]])]
    errors += [f"projects: duplicate title {v}" for v in _duplicates([p.get("title") for p in data["projects"]])]

    if len(data["posts"]) >= SINGLE_USE_TAG_MIN_POSTS:
        counts = Counter(t for p in data["posts"] for t in p.get("tags", []) if isinstance(t, str))
        warnings += [f"posts: tag '{tag}' is used once (typo?)" for tag, n in sorted(counts.items()) if n == 1]

    for key in ("posts", "testimonials", "projects", "career"):
        for i, item in zip(positions[key], data[key]):
            for field, text in _strings(item):
                where = f"{key}[{i}].{field}"
                if EMAIL_RE.search(text):
                    errors.append(f"{where}: contains an email address; do not publish it")
                if field not in LINK_KEYS and _looks_like_phone(text):
                    errors.append(f"{where}: looks like a phone number; reword it if it is not one")

    if readable:
        expected = common.render_data_js({"projects": raw["projects"], "posts": raw["posts"], "testimonials": raw["testimonials"], "career": raw["career"]})
        if not paths.data_js.exists() or paths.data_js.read_text(encoding="utf-8") != expected:
            errors.append("data/data.js is out of date: run python3 tools/build_data.py")
    return errors, warnings


def main(argv=None, paths=None):
    paths = paths or common.Paths()
    errors, warnings = run_checks(paths)
    for w in warnings:
        print("warning:", w)
    for e in errors:
        print("error:  ", e)
    if errors:
        print(f"{len(errors)} error(s). Fix them before pushing.")
        return 1
    print("OK: public data is clean" + (f" ({len(warnings)} warning(s))" if warnings else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Shared helpers for the content tools: paths, JSON files, ids, backups, validation, publishing, data.js."""
import hashlib
import json
import re
import shutil
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CONSENT_VALUES = ("written", "public-linkedin")
POST_FIELDS = ("id", "source", "sourceLabel", "title", "excerpt", "date", "url", "tags")
TESTIMONIAL_FIELDS = ("id", "name", "role", "company", "quote", "date", "consent", "sourceUrl")
PROJECT_FIELDS = ("title", "type", "short", "desc", "stack", "role", "outcome", "link")
DRAFT_ONLY_FIELDS = ("kind", "status", "note")
OPTIONAL_URL_FIELDS = ("sourceUrl", "link")

ID_RE = re.compile(r"^[0-9a-f]{10}$")
SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
TAG_RE = re.compile(r"^[a-z0-9][a-z0-9+#.-]{0,23}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
RESERVED_FILTER = "all"  # the page's "show everything" filter button


class Paths:
    """Every file the tools read or write, relative to one repo root (tests pass a temp folder)."""

    def __init__(self, root=ROOT):
        self.root = Path(root)
        self.data = self.root / "data"
        self.private = self.root / "private"
        self.backups = self.private / "backups"
        self.drafts = self.private / "drafts.json"
        self.discarded = self.private / "discarded.json"
        self.posts = self.data / "posts.json"
        self.testimonials = self.data / "testimonials.json"
        self.projects = self.data / "projects.json"
        self.data_js = self.data / "data.js"


# ---------- JSON files, ids, backups ----------

def load_json(path, default):
    path = Path(path)
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def backup(paths, path):
    """Copy an existing file to private/backups/<name>.<timestamp>. Returns the copy, or None if there was nothing to copy."""
    path = Path(path)
    if not path.exists():
        return None
    paths.backups.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    target = paths.backups / f"{path.name}.{stamp}"
    shutil.copy2(path, target)
    return target


def make_id(*parts):
    """First 10 hex characters of the SHA-1 of the parts. Post: (url,). Testimonial: (name, date, quote)."""
    return hashlib.sha1("\x1f".join(parts).encode("utf-8")).hexdigest()[:10]


# ---------- drafts (private) ----------

def load_drafts(paths):
    return load_json(paths.drafts, [])


def save_drafts(paths, drafts):
    backup(paths, paths.drafts)
    save_json(paths.drafts, drafts)


def load_discarded(paths):
    """Ids of drafts you discarded, so the next import does not bring them back."""
    return load_json(paths.discarded, [])


def remember_discarded(paths, ids):
    ids = list(ids)
    if not ids:
        return
    merged = list(dict.fromkeys(load_discarded(paths) + ids))
    backup(paths, paths.discarded)
    save_json(paths.discarded, merged)


# ---------- data.js (the copy the page loads) ----------

def load_public(paths):
    return {
        "projects": load_json(paths.projects, []),
        "posts": load_json(paths.posts, []),
        "testimonials": load_json(paths.testimonials, []),
    }


def render_data_js(data):
    return "window.SITE_DATA = " + json.dumps(data, indent=2, ensure_ascii=False) + ";\n"


def write_data_js(paths):
    paths.data.mkdir(parents=True, exist_ok=True)
    paths.data_js.write_text(render_data_js(load_public(paths)), encoding="utf-8")


# ---------- validation ----------

def _is_real_date(value):
    if not isinstance(value, str) or not DATE_RE.fullmatch(value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _length(d, key, low, high, errors):
    value = d.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{key}: required")
    elif not low <= len(value.strip()) <= high:
        errors.append(f"{key}: must be {low}-{high} characters (is {len(value.strip())})")


def _required(d, key, errors):
    value = d.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{key}: required")


def _https(d, key, errors, optional=False):
    value = d.get(key)
    if value in (None, "") and optional:
        return
    if not isinstance(value, str) or not value.startswith("https://") or len(value) < 12:
        errors.append(f"{key}: must be an https:// link")


def _unexpected(d, allowed, errors):
    for key in d:
        if key not in allowed:
            errors.append(f"{key}: unexpected field")


def validate_post(d):
    errors = []
    if not isinstance(d.get("id"), str) or not ID_RE.fullmatch(d.get("id", "")):
        errors.append("id: must be 10 hex characters")
    if not isinstance(d.get("source"), str) or not SLUG_RE.fullmatch(d.get("source", "")):
        errors.append("source: must be a lowercase slug such as 'linkedin' or 'data-community'")
    elif d["source"] == RESERVED_FILTER:
        errors.append("source: 'all' is reserved")
    _required(d, "sourceLabel", errors)
    _length(d, "title", 3, 90, errors)
    _length(d, "excerpt", 1, 160, errors)
    if not _is_real_date(d.get("date")):
        errors.append("date: must be a real date as YYYY-MM-DD")
    _https(d, "url", errors)
    tags = d.get("tags")
    if not isinstance(tags, list) or not 1 <= len(tags) <= 4:
        errors.append("tags: need 1 to 4 tags")
    elif not all(isinstance(t, str) and TAG_RE.fullmatch(t) for t in tags):
        errors.append("tags: use lowercase letters, digits and - + # . (max 24 characters each)")
    elif RESERVED_FILTER in tags:
        errors.append("tags: 'all' is reserved")
    elif len(set(tags)) != len(tags):
        errors.append("tags: duplicates")
    _unexpected(d, POST_FIELDS, errors)
    return errors


def validate_testimonial(d):
    errors = []
    if not isinstance(d.get("id"), str) or not ID_RE.fullmatch(d.get("id", "")):
        errors.append("id: must be 10 hex characters")
    for key in ("name", "role", "company"):
        _required(d, key, errors)
    _length(d, "quote", 1, 400, errors)
    if not _is_real_date(d.get("date")):
        errors.append("date: must be a real date as YYYY-MM-DD")
    if d.get("consent") not in CONSENT_VALUES:
        errors.append("consent: must be one of " + ", ".join(CONSENT_VALUES))
    _https(d, "sourceUrl", errors, optional=True)
    _unexpected(d, TESTIMONIAL_FIELDS, errors)
    return errors


def validate_project(d):
    errors = []
    for key in ("title", "type", "desc", "role", "outcome"):
        _required(d, key, errors)
    _length(d, "short", 1, 100, errors)
    stack = d.get("stack")
    if not isinstance(stack, list) or not stack or not all(isinstance(s, str) and s.strip() for s in stack):
        errors.append("stack: need a non-empty list of names")
    _https(d, "link", errors, optional=True)
    _unexpected(d, PROJECT_FIELDS, errors)
    return errors


VALIDATORS = {"post": validate_post, "testimonial": validate_testimonial, "project": validate_project}


def validate(kind, entry):
    return VALIDATORS[kind](entry)


# ---------- publishing ----------

def to_public(draft):
    """Strip draft-only fields and empty optional links so the entry has exactly the public shape."""
    entry = {k: v for k, v in draft.items() if k not in DRAFT_ONLY_FIELDS}
    for key in OPTIONAL_URL_FIELDS:
        if entry.get(key) == "":
            del entry[key]
    return entry


def sort_items(items):
    """Posts and testimonials: newest first, ties broken by id so the order is stable."""
    return sorted(items, key=lambda i: (i.get("date", ""), i.get("id", "")), reverse=True)


def publish(paths, kind, entry):
    """Validate entry and add it to the public file for its kind. Returns a list of errors (empty = published)."""
    if kind not in ("post", "testimonial"):
        return [f"kind: cannot publish '{kind}'"]
    entry = to_public(entry)
    errors = validate(kind, entry)
    if errors:
        return errors
    target = paths.posts if kind == "post" else paths.testimonials
    items = load_json(target, [])
    if any(i.get("id") == entry["id"] for i in items):
        return ["id: already published"]
    items.append(entry)
    backup(paths, target)
    save_json(target, sort_items(items))
    write_data_js(paths)
    return []

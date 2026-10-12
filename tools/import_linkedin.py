"""Import a LinkedIn data export into private drafts.

Usage: python3 tools/import_linkedin.py <export folder or .zip>

Reads Shares.csv (your posts) and the received-recommendations file, and adds only NEW items to
private/drafts.json. It never publishes anything and never touches the public data/ folder.
Next step: python3 tools/review.py
"""
import csv
import io
import re
import sys
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools import common  # noqa: E402


class ExportFormatError(Exception):
    """The export is missing a file or a required column. Nothing has been changed."""


# Column names are matched loosely: lower-cased, with everything except letters and digits removed.
SHARES_COLUMNS = {
    "date": ("date", "sharedate"),
    "url": ("sharelink", "link", "url"),
    "text": ("sharecommentary", "commentary", "text", "content"),
}
SHARES_REQUIRED = ("date", "url")
REC_COLUMNS = {
    "first": ("firstname",),
    "last": ("lastname",),
    "company": ("company", "companyname"),
    "role": ("jobtitle", "title", "position"),
    "text": ("text", "recommendation", "recommendationtext", "body"),
    "date": ("creationdate", "date", "createdat"),
    "status": ("status",),
}
REC_REQUIRED = ("first", "last", "text")
VISIBLE_STATUSES = {"visible"}

# Month comes first in every numeric format here. Check the dates in the first real import.
DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%m/%d/%y, %I:%M %p", "%m/%d/%y %I:%M %p",
    "%m/%d/%Y, %I:%M %p", "%m/%d/%Y %I:%M %p", "%m/%d/%y", "%m/%d/%Y", "%b %d, %Y", "%d %b %Y",
)


@dataclass
class ImportResult:
    new_posts: int = 0
    new_testimonials: int = 0
    skipped_existing: int = 0
    skipped_status: int = 0
    skipped_statuses: list = field(default_factory=list)
    headers: dict = field(default_factory=dict)


def collapse(text):
    return re.sub(r"\s+", " ", text or "").strip()


def shorten(text, limit):
    """Collapse whitespace and cut to at most `limit` characters at a word boundary, adding an ellipsis."""
    text = collapse(text)
    if len(text) <= limit:
        return text
    cut = text[: limit - 1].rsplit(" ", 1)[0] or text[: limit - 1]
    return cut.rstrip(" ,;:.-") + "…"


def parse_date(raw):
    raw = re.sub(r"\s*UTC$", "", (raw or "").strip())
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return ""


def _norm(header):
    return re.sub(r"[^a-z0-9]", "", header.lower())


def _columns(headers, spec):
    by_norm = {_norm(h): h for h in headers}
    return {key: next((by_norm[o] for o in options if o in by_norm), None) for key, options in spec.items()}


def _cell(row, column):
    return (row.get(column) or "").strip() if column else ""


def _classify(relative_path):
    """Return 'shares', 'recommendations' or None for a path inside the export (folder or zip entry name)."""
    parts = [p for p in re.split(r"[\\/]", str(relative_path)) if p]
    if not parts or "__MACOSX" in parts or parts[-1].startswith("._"):
        return None
    low = parts[-1].lower()
    if low == "shares.csv":
        return "shares"
    if low.endswith(".csv") and "recommendation" in low and "received" in low:
        return "recommendations"
    return None


def read_export_files(source):
    """Return {'shares': text or None, 'recommendations': text or None} from a folder or a .zip."""
    source = Path(source)
    found = {"shares": None, "recommendations": None}
    current = source.name
    try:
        if source.is_dir():
            for f in sorted(source.rglob("*.csv")):
                kind = _classify(f.relative_to(source).as_posix())
                if kind and found[kind] is None:
                    current = f.name
                    found[kind] = f.read_text(encoding="utf-8-sig")
        elif source.is_file() and source.suffix.lower() == ".zip":
            with zipfile.ZipFile(source) as z:
                for info in z.infolist():
                    kind = _classify(info.filename)
                    if kind and found[kind] is None:
                        current = Path(info.filename).name
                        found[kind] = z.read(info).decode("utf-8-sig")
        else:
            raise ExportFormatError(f"{source} is not a folder or a .zip file")
    except zipfile.BadZipFile as e:
        raise ExportFormatError(f"could not read {source.name}: it is not a valid .zip file ({e})") from e
    except UnicodeDecodeError as e:
        raise ExportFormatError(f"could not read {current}: it is not a plain text CSV file ({e.reason})") from e
    except OSError as e:
        raise ExportFormatError(f"could not read {current}: {e.strerror or e}") from e
    if not any(found.values()):
        raise ExportFormatError(f"no Shares.csv or recommendations file found in {source}")
    return found


def _parse_csv(text, spec, required, label):
    reader = csv.DictReader(io.StringIO(text))
    headers = reader.fieldnames or []
    cols = _columns(headers, spec)
    missing = [key for key in required if cols[key] is None]
    if missing:
        raise ExportFormatError(f"{label}: no column found for {', '.join(missing)}. Headers found: {', '.join(headers) or '(none)'}")
    return cols, list(reader), headers


def post_draft(row, cols):
    url, text, raw_date = _cell(row, cols["url"]), _cell(row, cols["text"]), _cell(row, cols["date"])
    iso = parse_date(raw_date)
    notes = []
    if not iso:
        notes.append(f"date could not be read ('{raw_date}'); set it with the edit key")
    first_line = next((line for line in text.splitlines() if line.strip()), "")
    excerpt = shorten(text, 160)
    if not excerpt:
        notes.append("this post has no text; write an excerpt")
    draft = {
        "kind": "post", "status": "draft", "id": common.make_id(url),
        "source": "linkedin", "sourceLabel": "LinkedIn",
        "title": shorten(first_line, 90) or "LinkedIn post", "excerpt": excerpt,
        "date": iso, "url": url, "tags": [],
    }
    if notes:
        draft["note"] = "; ".join(notes)
    return draft


def testimonial_draft(row, cols):
    name = collapse(f"{_cell(row, cols['first'])} {_cell(row, cols['last'])}")
    quote, raw_date = collapse(_cell(row, cols["text"])), _cell(row, cols["date"])
    iso = parse_date(raw_date)
    notes = []
    if not iso:
        notes.append(f"date could not be read ('{raw_date}'); set it with the edit key")
    if len(quote) > 400:
        notes.append(f"quote is {len(quote)} characters; shorten it to 400 or fewer (keep the meaning)")
    draft = {
        "kind": "testimonial", "status": "draft", "id": common.make_id(name, iso, quote),
        "name": name, "role": collapse(_cell(row, cols["role"])), "company": collapse(_cell(row, cols["company"])),
        "quote": quote, "date": iso, "consent": "", "sourceUrl": "",
    }
    if notes:
        draft["note"] = "; ".join(notes)
    return draft


def import_export(source, paths):
    """Add new items from the export to private/drafts.json. Raises ExportFormatError before changing anything."""
    files = read_export_files(source)
    shares = _parse_csv(files["shares"], SHARES_COLUMNS, SHARES_REQUIRED, "Shares.csv") if files["shares"] is not None else None
    recs = _parse_csv(files["recommendations"], REC_COLUMNS, REC_REQUIRED, "Recommendations file") if files["recommendations"] is not None else None

    drafts = common.load_drafts(paths)
    known = {d.get("id") for d in drafts}
    known |= {i.get("id") for i in common.load_json(paths.posts, [])}
    known |= {i.get("id") for i in common.load_json(paths.testimonials, [])}
    known |= set(common.load_discarded(paths))

    result, new = ImportResult(), []
    seen_statuses = set()
    if shares:
        cols, rows, headers = shares
        result.headers["Shares.csv"] = {"found": headers, "mapped": cols}
        for row in rows:
            if not _cell(row, cols["url"]):
                continue
            draft = post_draft(row, cols)
            if draft["id"] in known:
                result.skipped_existing += 1
                continue
            known.add(draft["id"])
            new.append(draft)
            result.new_posts += 1
    if recs:
        cols, rows, headers = recs
        result.headers["Recommendations file"] = {"found": headers, "mapped": cols}
        for row in rows:
            if cols["status"]:
                raw_status = _cell(row, cols["status"])
                if raw_status.lower() not in VISIBLE_STATUSES:
                    result.skipped_status += 1
                    seen_statuses.add(raw_status or "(blank)")
                    continue
            draft = testimonial_draft(row, cols)
            if not draft["quote"]:
                continue
            if draft["id"] in known:
                result.skipped_existing += 1
                continue
            known.add(draft["id"])
            new.append(draft)
            result.new_testimonials += 1
    result.skipped_statuses = sorted(seen_statuses)
    if new:
        common.save_drafts(paths, drafts + new)
    return result


def main(argv=None, paths=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("Usage: python3 tools/import_linkedin.py <export folder or .zip>")
        return 2
    paths = paths or common.Paths()
    try:
        r = import_export(argv[0], paths)
    except ExportFormatError as e:
        print(f"error: {e}")
        print("Nothing was changed.")
        return 2
    for name, info in r.headers.items():
        print(f"{name} headers: {', '.join(info['found']) or '(none)'}")
        mapped = ", ".join(f"{field} <- {header or '(not found)'}" for field, header in info["mapped"].items())
        print(f"  mapped: {mapped}")
    print(f"Imported {r.new_posts} new post draft(s) and {r.new_testimonials} new testimonial draft(s).")
    if r.skipped_status:
        seen = f" (seen: {', '.join(r.skipped_statuses)})" if r.skipped_statuses else ""
        print(f"Skipped {r.skipped_existing} already known item(s) and {r.skipped_status} recommendation(s) whose status is not visible{seen}.")
    else:
        print(f"Skipped {r.skipped_existing} already known item(s) and {r.skipped_status} hidden recommendation(s).")
    if r.new_posts or r.new_testimonials:
        print("Next: python3 tools/review.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())

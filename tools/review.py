"""Review private drafts one at a time: publish, edit, skip or discard.

Usage: python3 tools/review.py
Publishing moves a draft into the public data files, after the same validation that tools/check.py uses.
A testimonial cannot be published until its consent is set. Quit any time; drafts you did not finish are kept.
"""
import copy
import sys
from dataclasses import dataclass
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools import common  # noqa: E402

EDITABLE = {
    "post": ("title", "excerpt", "date", "source", "sourceLabel", "tags"),
    "testimonial": ("name", "role", "company", "quote", "date", "consent", "sourceUrl"),
}
SHOWN = {
    "post": ("title", "source", "sourceLabel", "date", "tags", "url", "excerpt"),
    "testimonial": ("name", "role", "company", "date", "consent", "sourceUrl", "quote"),
}
CONSENT_ALIASES = {"w": "written", "l": "public-linkedin"}
PROMPT = "[p]ublish  [e]dit  [s]kip  [d]iscard  [q]uit > "


@dataclass
class Summary:
    published: int = 0
    skipped: int = 0
    discarded: int = 0
    remaining: int = 0


def parse_value(field, text):
    text = text.strip()
    if field == "tags":
        return [t.strip().lower() for t in text.split(",") if t.strip()]
    if field == "consent":
        return CONSENT_ALIASES.get(text.lower(), text)
    return text


def show(draft, index, total, out):
    out(f"\n--- {index}/{total}: {draft.get('kind', '?')} ---")
    for field in SHOWN.get(draft.get("kind"), ()):
        value = draft.get(field, "")
        out(f"  {field:12}: {', '.join(value) if isinstance(value, list) else value}")
    if draft.get("note"):
        out(f"  NOTE        : {draft['note']}")


def review(paths, inp=input, out=print):
    queue = common.load_drafts(paths)
    summary = Summary()
    if not queue:
        out("No drafts to review.")
        return summary
    original = copy.deepcopy(queue)
    keep, discarded, i = [], [], 0
    try:
        while i < len(queue):
            draft = queue[i]
            kind = draft.get("kind")
            show(draft, i + 1, len(queue), out)
            try:
                choice = inp(PROMPT).strip().lower()
            except EOFError:
                choice = "q"
            if choice in ("p", "publish"):
                errors = common.publish(paths, kind, draft)
                if errors:
                    out("Cannot publish yet:")
                    for e in errors:
                        out(f"  - {e}")
                    if kind == "testimonial" and any(e.startswith("consent") for e in errors):
                        out("Set it with: e, then consent, then w or l.")
                    continue
                summary.published += 1
                i += 1
            elif choice in ("e", "edit"):
                try:
                    field = inp(f"field ({', '.join(EDITABLE.get(kind, ()))}) > ").strip()
                    if field not in EDITABLE.get(kind, ()):
                        out(f"'{field}' cannot be edited. Choose from: {', '.join(EDITABLE.get(kind, ()))}")
                        continue
                    label = "new consent (w = written, l = public-linkedin)" if field == "consent" else f"new {field}"
                    draft[field] = parse_value(field, inp(f"{label} > "))
                except EOFError:
                    break
            elif choice in ("s", "skip"):
                keep.append(draft)
                summary.skipped += 1
                i += 1
            elif choice in ("d", "discard"):
                if draft.get("id"):
                    discarded.append(draft["id"])
                summary.discarded += 1
                i += 1
            elif choice in ("q", "quit"):
                break
            else:
                out("Choose p, e, s, d or q.")
    except KeyboardInterrupt:
        out("\nInterrupted: unfinished drafts are kept.")
    finally:
        keep.extend(queue[i:])
        summary.remaining = len(keep)
        if keep != original:
            common.save_drafts(paths, keep)
        common.remember_discarded(paths, discarded)
    return summary


def main(argv=None, paths=None):
    s = review(paths or common.Paths())
    print(f"\nPublished {s.published}, skipped {s.skipped}, discarded {s.discarded}; {s.remaining} left in drafts.")
    if s.published:
        print("Next: python3 tools/check.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())

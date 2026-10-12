# Sunil Kumar: personal website

A static site (HTML, CSS and JavaScript) hosted on GitHub Pages. Projects, Testimonials and Posts come from
`data/data.js`, which is generated from the JSON files in `data/`.

## Preview locally

Open `index.html` in a browser.

## Keep the content up to date

All commands run from this folder with `python3`. Nothing is published until you review it.

1. Download your LinkedIn data. The menu names may differ; look in Settings and Data privacy for
   "Get a copy of your data". The download usually arrives within a day or two. Keep it in Downloads or in
   `private/linkedin-export/`, never in the repo folder root.
2. `python3 tools/import_linkedin.py <the downloaded folder or .zip>` adds new posts and recommendations as drafts.
3. `python3 tools/review.py` steps through the drafts: publish, edit, skip or discard. A testimonial cannot be
   published until its consent is set. Discarded items are remembered and are not brought back by the next import.
4. `python3 tools/check.py` checks the public data. Fix any errors it reports.
5. Push the change. First run `gh auth status` and check it shows `SunilKumar-Official`. Then:
   `git add data`, `git commit -m "Update posts"`, `git push`. GitHub Pages updates in about a minute.

Add one item without an export:

- `python3 tools/add.py post` or `python3 tools/add.py testimonial`. This is the way to add posts from other
  communities. Without `--draft` it publishes right after you answer `y`; add `--draft` to save it privately first.
- LinkedIn posts should come in through the import. A LinkedIn post added by hand from its browser link would
  later be imported again as a duplicate.

After editing a JSON file by hand, run `python3 tools/build_data.py`.

Drafts, raw exports and backups live in `private/`, which is never committed.

## Tests

`python3 -m unittest discover -s tests` (the page test needs Chrome or Chromium and is skipped without it).

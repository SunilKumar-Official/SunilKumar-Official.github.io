"""Build the resume PDF and the two QR codes.

Usage (QR codes need the `segno` package, which lives in the project's .venv):
    .venv/bin/python tools/build_resume.py

What it writes:
    assets/Sunil-Kumar-Resume.pdf   the one-page resume, printed with headless Chrome
    assets/qr-resume.svg            QR code (shown on the Contact page) that opens the PDF

The resume's layout is tools/resume/resume.template.html. It holds no personal contact
details. Email, phone and location come from private/contact-details.json (gitignored) and are
filled in here, so they exist only inside the finished PDF.

The build fails, without touching assets/, if the resume would not fit on a single A4 page.
Set CHROME to the browser binary if Chrome is not in its usual macOS location.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "tools" / "resume" / "resume.template.html"
DETAILS = ROOT / "private" / "contact-details.json"
WORK_DIR = ROOT / "private" / "resume"  # two levels below ROOT so the template's ../../assets/fonts paths resolve
PDF_OUT = ROOT / "assets" / "Sunil-Kumar-Resume.pdf"
QR_OUT = ROOT / "assets" / "qr-resume.svg"

SITE_URL = "https://sunilkumar-official.github.io/"
PDF_URL = SITE_URL + "assets/Sunil-Kumar-Resume.pdf"
CHROME_DEFAULT = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def load_details(path=DETAILS):
    if not path.exists():
        raise SystemExit(f"Missing {path}. Create it with email, phone, city, region and country.")
    d = json.loads(path.read_text(encoding="utf-8"))
    for key in ("email", "phone", "city", "country"):
        if not d.get(key):
            raise SystemExit(f"{path} needs a non-empty '{key}'.")
    return d


def location_text(d):
    return ", ".join(p for p in (d["city"], d.get("region"), d["country"]) if p)


def render_template(template, details, qr_site_svg):
    """Fill the template's placeholders. Raises if any placeholder is left over."""
    page = (template
            .replace("{{EMAIL}}", details["email"])
            .replace("{{PHONE}}", details["phone"])
            .replace("{{LOCATION}}", location_text(details))
            .replace("{{QR_SITE_SVG}}", qr_site_svg))
    left = re.findall(r"\{\{[A-Z_]+\}\}", page)
    if left:
        raise ValueError(f"unfilled placeholders: {sorted(set(left))}")
    return page


def count_pdf_pages(data):
    return len(re.findall(rb"/Type\s*/Page[^s]", data))


def make_qrs():
    try:
        import segno
    except ImportError:
        raise SystemExit("segno is not installed for this Python. Run: .venv/bin/python tools/build_resume.py")
    site = segno.make(SITE_URL, error="m")
    inline = site.svg_inline(scale=1, border=1, dark="#000", light="#fff", omitsize=True)
    inline = inline.replace("<svg ", '<svg width="84" height="84" shape-rendering="crispEdges" ', 1)
    pdf_qr = segno.make(PDF_URL, error="m")
    return inline, pdf_qr


def chrome_path():
    path = os.environ.get("CHROME", CHROME_DEFAULT)
    if not Path(path).exists():
        raise SystemExit(f"Chrome not found at {path}. Set the CHROME environment variable.")
    return path


def main():
    details = load_details()
    inline_qr, pdf_qr = make_qrs()
    page = render_template(TEMPLATE.read_text(encoding="utf-8"), details, inline_qr)

    WORK_DIR.mkdir(parents=True, exist_ok=True)
    html_path = WORK_DIR / "resume.html"
    html_path.write_text(page, encoding="utf-8")
    chrome = chrome_path()
    url = html_path.as_uri()

    dom = subprocess.run([chrome, "--headless", "--disable-gpu", "--virtual-time-budget=6000", "--dump-dom", url],
                         capture_output=True, text=True, check=True).stdout
    fit = re.search(r'data-fit="(\w+)"', dom)
    if not fit or fit.group(1) != "fits":
        raise SystemExit("The resume does not fit on one A4 page. Tighten tools/resume/resume.template.html.")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_pdf = Path(tmp) / "resume.pdf"
        subprocess.run([chrome, "--headless", "--disable-gpu", "--virtual-time-budget=6000", "--no-pdf-header-footer",
                        f"--print-to-pdf={tmp_pdf}", url], capture_output=True, check=True)
        data = tmp_pdf.read_bytes()
        pages = count_pdf_pages(data)
        if not data.startswith(b"%PDF") or pages != 1:
            raise SystemExit(f"Expected a one-page PDF, got {pages} page(s).")
        PDF_OUT.write_bytes(data)
    pdf_qr.save(str(QR_OUT), kind="svg", scale=4, border=1, dark="#000", light="#fff")
    print(f"wrote {PDF_OUT} (1 page, {PDF_OUT.stat().st_size // 1024} KB)")
    print(f"wrote {QR_OUT}")


if __name__ == "__main__":
    sys.exit(main())

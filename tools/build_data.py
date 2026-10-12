"""Regenerate data/data.js from the public JSON files.

Usage: python3 tools/build_data.py
The other tools do this automatically; run it yourself only after editing a JSON file by hand.
"""
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools import common  # noqa: E402


def main(argv=None, paths=None):
    paths = paths or common.Paths()
    common.write_data_js(paths)
    print(f"wrote {paths.data_js}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

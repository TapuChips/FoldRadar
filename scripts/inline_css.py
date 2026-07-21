# -*- coding: utf-8 -*-
"""Inline style.css into each page's <head> to eliminate the flash of unstyled
content (FOUC). The stylesheet becomes part of the HTML document, so the page
paints fully styled on the first frame with no extra network request.

Reversible + idempotent: replaces either the <link> or a previously-inlined
<style data-app-css> block, so it can be re-run any time style.css changes.
"""
import glob
import io
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_MARKER = re.compile(
    r'<link rel="stylesheet" href="/style\.css">|<style data-app-css>.*?</style>',
    re.DOTALL,
)


def inline_html(html, css):
    """Return html with the stylesheet link/inline block replaced by inlined CSS."""
    block = "<style data-app-css>\n" + css + "\n</style>"
    if _MARKER.search(html):
        return _MARKER.sub(lambda _m: block, html, count=1)
    return html


def inline_all():
    css = (ROOT / "style.css").read_text(encoding="utf-8")
    paths = glob.glob(str(ROOT / "*.html")) + glob.glob(str(ROOT / "de" / "*.html"))
    changed = 0
    for p in paths:
        s = io.open(p, encoding="utf-8").read()
        s2 = inline_html(s, css)
        if s2 != s:
            io.open(p, "w", encoding="utf-8", newline="\n").write(s2)
            changed += 1
    return changed, len(css)


if __name__ == "__main__":
    n, size = inline_all()
    print(f"inlined {size} bytes of CSS into {n} page(s)")

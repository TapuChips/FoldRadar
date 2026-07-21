# -*- coding: utf-8 -*-
"""FoldRadar daily news builder.

Pulls RSS/Atom feeds from foldable-focused creators and phone-news sites,
then rewrites each item into ONE original sentence in FoldRadar's voice and
publishes it on /news. Sources are credited by name (no outbound links) so
readers stay on-site; every item carries a CTA into our own coverage.

Rewriting uses the OpenAI API when OPENAI_API_KEY is set (add it as a GitHub
Actions secret for the daily run). Without a key it falls back to the headline
text so the page still builds. Run daily by GitHub Actions.
"""
import datetime
import html
import json
import os
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from inline_css import inline_html

ROOT = Path(__file__).resolve().parent.parent

# (label, url, kind, filtered)  — filtered=False for foldable-only channels
FEEDS = [
    ("Shane Craig", "https://www.youtube.com/feeds/videos.xml?channel_id=UCCKQStaJH5LuMGHHeM9Y-OA", "video", False),
    ("Average Dad", "https://www.youtube.com/feeds/videos.xml?channel_id=UCEz5Ci0AKKxQvVwS8E88VUg", "video", True),
    ("GSMArena", "https://www.gsmarena.com/rss-news-reviews.php3", "news", True),
    ("9to5Google", "https://9to5google.com/feed/", "news", True),
    ("MacRumors", "https://feeds.macrumors.com/MacRumors-All", "news", True),
    ("Android Authority", "https://www.androidauthority.com/feed/", "news", True),
]

KEYWORDS = re.compile(
    r"fold|flip|razr|hinge|flex window|book-style|clamshell|tri-fold|trifold",
    re.IGNORECASE,
)
NS = {"atom": "http://www.w3.org/2005/Atom", "media": "http://search.yahoo.com/mrss/"}

# CTAs rotated across items so every entry drives into our own pages
CTAS = [
    ("/iphone-fold", "Read the iPhone Fold tracker"),
    ("/which-foldable", "Which foldable fits you?"),
    ("/best-foldable-phones", "See the best foldables"),
    ("/news#launch-alert", "Get the launch alert"),
    ("/iphone-fold-vs-galaxy-z-fold", "iPhone Fold vs Z Fold"),
]


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "FoldRadarBot/1.0 (+https://foldradar.com)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def parse_feed(label, url, kind, filtered):
    items = []
    try:
        root = ET.fromstring(fetch(url))
    except Exception as e:
        print(f"!! {label}: {e}")
        return items
    if root.tag.endswith("feed"):  # Atom (YouTube)
        for entry in root.findall("atom:entry", NS):
            title = (entry.findtext("atom:title", "", NS) or "").strip()
            date = (entry.findtext("atom:published", "", NS) or "")[:10]
            items.append({"title": title, "date": date, "source": label, "kind": kind})
    else:  # RSS
        for it in root.iter("item"):
            title = (it.findtext("title") or "").strip()
            pub = it.findtext("pubDate") or ""
            try:
                date = datetime.datetime.strptime(pub[5:16], "%d %b %Y").strftime("%Y-%m-%d")
            except ValueError:
                date = ""
            items.append({"title": title, "date": date, "source": label, "kind": kind})
    if filtered:
        items = [i for i in items if KEYWORDS.search(i["title"])]
    return items[:8]


def summarize(items):
    """Rewrite each headline as one original sentence. OpenAI if keyed, else fallback."""
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key or not items:
        return [i["title"] for i in items]
    listing = "\n".join(f'{n+1}. "{i["title"]}" (source: {i["source"]})' for n, i in enumerate(items))
    prompt = (
        "You are FoldRadar, an independent foldable-phone news site. For each headline "
        "below, write ONE original sentence (max 28 words) summarizing the story for our "
        "readers. Use your own wording — do NOT copy the headline's phrasing. Stay factual "
        "and neutral; never invent details the headline does not state. Do not mention the "
        'source in the sentence. Return ONLY JSON: {"summaries": ["...", ...]} in the same '
        "order.\n\n" + listing
    )
    try:
        body = json.dumps({
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.6,
            "response_format": {"type": "json_object"},
        }).encode()
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions", data=body,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            content = json.loads(r.read())["choices"][0]["message"]["content"]
        out = json.loads(content).get("summaries", [])
        # pad/truncate to match, fall back to title on any gap
        result = []
        for n, i in enumerate(items):
            s = out[n].strip() if n < len(out) and isinstance(out[n], str) and out[n].strip() else i["title"]
            result.append(s)
        print(f"   rewrote {len(items)} items via OpenAI")
        return result
    except Exception as e:
        print(f"   (OpenAI rewrite failed: {str(e)[:90]} — using headlines)")
        return [i["title"] for i in items]


def build():
    all_items = []
    for feed in FEEDS:
        got = parse_feed(*feed)
        print(f"   {feed[0]}: {len(got)} items")
        all_items.extend(got)

    all_items.sort(key=lambda i: i["date"], reverse=True)
    digest = all_items[:16]
    summaries = summarize(digest)
    for it, s in zip(digest, summaries):
        it["summary"] = s

    today = datetime.date.today()
    updated_human = today.strftime("%B %d, %Y")

    def card(item, idx):
        s = html.escape(item["summary"])
        src = html.escape(item["source"])
        cta_url, cta_label = CTAS[idx % len(CTAS)]
        return (
            '    <li class="digest-item">\n'
            f'      <p class="digest-text">{s}</p>\n'
            f'      <p class="digest-meta"><span class="via">via {src}</span>'
            f'<a class="digest-cta" href="{cta_url}">{html.escape(cta_label)} →</a></p>\n'
            '    </li>'
        )

    digest_html = "\n".join(card(it, n) for n, it in enumerate(digest)) \
        or '    <li class="digest-item"><p class="digest-text">No fresh foldable stories today — check back tomorrow.</p></li>'

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Foldable News Today — Daily Digest | FoldRadar</title>
<meta name="description" content="Today's foldable phone news in FoldRadar's words: iPhone Fold rumors, Galaxy Z Fold and Razr, summarized daily and credited to the source. Updated {updated_human}.">
<link rel="canonical" href="https://foldradar.com/news">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="preload" href="/fonts/Inter-400.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/fonts/SpaceGrotesk-700.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/style.css">
<meta property="og:type" content="website">
<meta property="og:title" content="Foldable News Today — Daily Digest">
<meta property="og:description" content="The day's foldable phone stories, summarized in FoldRadar's words. Updated daily.">
<meta property="og:url" content="https://foldradar.com/news">
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "WebPage",
  "name": "Foldable news today — daily digest",
  "dateModified": "{today.isoformat()}",
  "mainEntityOfPage": "https://foldradar.com/news",
  "publisher": {{ "@id": "https://foldradar.com/#org" }}
}}
</script>
<script defer src="/_vercel/insights/script.js"></script>
</head>
<body>
<header class="site">
  <nav class="nav">
    <a class="logo" href="/">Fold<span>Radar</span></a>
    <a href="/iphone-fold">iPhone Fold</a>
    <a href="/news">News</a>
    <a href="/which-foldable">Quiz</a>
    <a href="/best-foldable-phones">Best foldables</a>
    <a class="lang" href="/de" lang="de">Deutsch</a>
  </nav>
</header>
<main>
  <p class="crumbs"><a href="/">FoldRadar</a> › News</p>
  <h1>Foldable news today</h1>
  <p class="updated">Auto-updated daily · Last refresh: {updated_human}</p>
  <p class="lead">The day's foldable stories — iPhone Fold rumors, Galaxy Z Fold, Razr and everything with a hinge — summarized in our own words and credited to the reporters who broke them.</p>

  <ul class="digest">
{digest_html}
  </ul>

  <div class="notify" id="launch-alert">
    <h2>One email when the iPhone Fold is announced</h2>
    <p>Skip the daily checking — date, price, pre-order links, once.</p>
    <form action="https://formsubmit.co/itzike25@gmail.com" method="POST">
      <input type="hidden" name="_subject" value="FoldRadar launch-alert signup">
      <input type="hidden" name="_next" value="https://foldradar.com/thanks">
      <input type="hidden" name="_captcha" value="false">
      <input type="email" name="email" required placeholder="you@example.com" aria-label="Email address">
      <button class="btn" type="submit">Notify me</button>
    </form>
  </div>

  <p class="disclosure">Summaries are FoldRadar's own, written from public reporting and credited to the outlet or creator named — GSMArena, MacRumors, 9to5Google, Android Authority, Shane Craig and Average Dad. We don't republish their text; we point you to our own coverage.</p>
</main>
<footer class="site">
  <div class="inner">
    <p><strong>FoldRadar</strong> — independent foldable phone tracker. Not affiliated with Apple, Samsung, Google or Honor. All trademarks belong to their owners.</p>
    <p>Some outbound links may be affiliate links; purchases through them can earn us a commission at no cost to you.</p>
    <p><a href="/about">About</a> · <a href="/privacy">Privacy</a> · <a href="/de" lang="de">Deutsch</a></p>
  </div>
</footer>
</body>
</html>
"""
    css = (ROOT / "style.css").read_text(encoding="utf-8")
    page = inline_html(page, css)
    (ROOT / "news.html").write_text(page, encoding="utf-8", newline="\n")
    print(f"news.html written: {len(digest)} digest items")

    # --- homepage "Today in foldables" strip: top 3 summaries, on-site ---
    top3 = digest[:3]
    strip_lines = []
    for item in top3:
        s = html.escape(item.get("summary", item["title"]))
        src = html.escape(item["source"])
        strip_lines.append(
            f'      <li><a class="ns-item" href="/news">{s}</a>'
            f'<span class="feedmeta">via {src}</span></li>'
        )
    strip = "\n".join(strip_lines) or '      <li><a class="ns-item" href="/news">See today\'s foldable news →</a></li>'

    index_path = ROOT / "index.html"
    idx = index_path.read_text(encoding="utf-8")
    start, end = "<!-- NEWS-STRIP:START -->", "<!-- NEWS-STRIP:END -->"
    if start in idx and end in idx:
        pre, rest = idx.split(start, 1)
        _, post = rest.split(end, 1)
        updated = pre + start + "\n" + strip + "\n" + end + post
        index_path.write_text(inline_html(updated, css), encoding="utf-8", newline="\n")
        print(f"index.html strip updated: {len(top3)} items")
    else:
        print("!! NEWS-STRIP markers not found in index.html — strip skipped")

    # --- sitemap: bump /news lastmod so crawlers see the daily change ---
    sm_path = ROOT / "sitemap.xml"
    sm = sm_path.read_text(encoding="utf-8")
    new_sm = re.sub(
        r"(<loc>https://foldradar\.com/news</loc>\s*<lastmod>)[0-9-]+(</lastmod>)",
        rf"\g<1>{today.isoformat()}\g<2>", sm,
    )
    if new_sm != sm:
        sm_path.write_text(new_sm, encoding="utf-8", newline="\n")
        print("sitemap.xml /news lastmod bumped")


if __name__ == "__main__":
    build()

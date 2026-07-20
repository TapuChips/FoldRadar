# -*- coding: utf-8 -*-
"""FoldRadar daily news builder.

Pulls RSS/Atom feeds from foldable-focused creators and phone-news sites,
filters for foldable topics, and regenerates news.html (headlines + links
only — full content stays with the sources). Run daily by GitHub Actions.
"""
import datetime
import html
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

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

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "media": "http://search.yahoo.com/mrss/",
}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "FoldRadarBot/1.0 (+https://foldradar.com)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def parse_feed(label, url, kind, filtered):
    """Return list of dicts: title, link, date (datetime), source, kind."""
    items = []
    try:
        root = ET.fromstring(fetch(url))
    except Exception as e:
        print(f"!! {label}: {e}")
        return items

    if root.tag.endswith("feed"):  # Atom (YouTube)
        for entry in root.findall("atom:entry", NS):
            title = (entry.findtext("atom:title", "", NS) or "").strip()
            link_el = entry.find("atom:link[@rel='alternate']", NS)
            link = link_el.get("href") if link_el is not None else ""
            date = (entry.findtext("atom:published", "", NS) or "")[:10]
            items.append({"title": title, "link": link, "date": date, "source": label, "kind": kind})
    else:  # RSS
        for it in root.iter("item"):
            title = (it.findtext("title") or "").strip()
            link = (it.findtext("link") or "").strip()
            pub = it.findtext("pubDate") or ""
            try:
                date = datetime.datetime.strptime(pub[5:16], "%d %b %Y").strftime("%Y-%m-%d")
            except ValueError:
                date = ""
            items.append({"title": title, "link": link, "date": date, "source": label, "kind": kind})

    if filtered:
        items = [i for i in items if KEYWORDS.search(i["title"])]
    return items[:8]


def build():
    all_items = []
    for feed in FEEDS:
        got = parse_feed(*feed)
        print(f"   {feed[0]}: {len(got)} items")
        all_items.extend(got)

    all_items.sort(key=lambda i: i["date"], reverse=True)
    videos = [i for i in all_items if i["kind"] == "video"][:10]
    news = [i for i in all_items if i["kind"] == "news"][:14]
    today = datetime.date.today()
    updated_human = today.strftime("%B %d, %Y")

    def li(item):
        t = html.escape(item["title"])
        u = html.escape(item["link"])
        d = item["date"] or ""
        return (f'    <li><a href="{u}" rel="noopener" target="_blank">{t}</a>'
                f'<span class="feedmeta">{html.escape(item["source"])}{" · " + d if d else ""}</span></li>')

    videos_html = "\n".join(li(i) for i in videos) or "    <li>No new videos today — check back tomorrow.</li>"
    news_html = "\n".join(li(i) for i in news) or "    <li>No foldable headlines today — check back tomorrow.</li>"

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Foldable News Today — Daily Feed | FoldRadar</title>
<meta name="description" content="Daily foldable phone news: iPhone Fold rumors, Galaxy Z Fold and Razr coverage from GSMArena, MacRumors, 9to5Google, plus videos from Shane Craig and Average Dad. Updated {updated_human}.">
<link rel="canonical" href="https://foldradar.com/news">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/style.css">
<meta property="og:type" content="website">
<meta property="og:title" content="Foldable News Today — Daily Feed">
<meta property="og:description" content="The day's foldable phone headlines and videos, in one place. Updated daily.">
<meta property="og:url" content="https://foldradar.com/news">
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "WebPage",
  "name": "Foldable news today — daily feed",
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
  <p class="lead">The day's foldable headlines and videos in one place — iPhone Fold rumors, Galaxy Z Fold, Razr, and everything with a hinge. Curated from the sources we trust; every link goes to the original.</p>

  <h2>Latest videos</h2>
  <ul class="feedlist">
{videos_html}
  </ul>

  <h2>Latest headlines</h2>
  <ul class="feedlist">
{news_html}
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

  <p class="disclosure">Headlines and video titles belong to their publishers — GSMArena, MacRumors, 9to5Google, Android Authority, Shane Craig and Average Dad — and link to the original source. FoldRadar aggregates titles only.</p>
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
    (ROOT / "news.html").write_text(page, encoding="utf-8", newline="\n")
    print(f"news.html written: {len(videos)} videos, {len(news)} headlines")

    # --- homepage "Today in foldables" strip: top 3 newest items overall ---
    top3 = all_items[:3]
    strip_lines = []
    for item in top3:
        t = html.escape(item["title"])
        u = html.escape(item["link"])
        strip_lines.append(
            f'      <li><a class="ns-item" href="{u}" rel="noopener" target="_blank">{t}</a>'
            f'<span class="feedmeta">{html.escape(item["source"])}</span></li>'
        )
    strip = "\n".join(strip_lines) or '      <li><a class="ns-item" href="/news">See today\'s foldable news →</a></li>'

    index_path = ROOT / "index.html"
    idx = index_path.read_text(encoding="utf-8")
    start, end = "<!-- NEWS-STRIP:START -->", "<!-- NEWS-STRIP:END -->"
    if start in idx and end in idx:
        pre, rest = idx.split(start, 1)
        _, post = rest.split(end, 1)
        index_path.write_text(pre + start + "\n" + strip + "\n" + end + post,
                              encoding="utf-8", newline="\n")
        print(f"index.html strip updated: {len(top3)} items")
    else:
        print("!! NEWS-STRIP markers not found in index.html — strip skipped")


if __name__ == "__main__":
    build()

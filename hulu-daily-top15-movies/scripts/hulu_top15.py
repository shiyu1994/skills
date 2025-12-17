#!/usr/bin/env python3
"""
Fetch and parse Hulu Daily Top 15 Movies (United States) for recent days.

Primary source: FlixPatrol daily charts.
- Per-platform daily page: https://flixpatrol.com/top10/hulu/united-states/YYYY-MM-DD/
- Aggregated streaming page: https://flixpatrol.com/top10/streaming/united-states/YYYY-MM-DD/

Outputs JSON by default. Can also render text.

Usage:
  scripts/hulu_top15.py --days 5 --format json

No external dependencies; uses Python stdlib only.
"""
import argparse
import datetime as dt
import json
import re
import sys
import time
import urllib.request
from urllib.error import HTTPError, URLError
from html import unescape

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

COUNTRY_SLUG = "united-states"
PLATFORM_SLUG = "hulu"

# -------------------------
# Networking helpers
# -------------------------

def http_get(url: str, timeout: float = 20.0, retries: int = 2, sleep_between: float = 0.8):
    """Fetch URL with retries and UA header. Return decoded text or None."""
    headers = {"User-Agent": DEFAULT_USER_AGENT, "Accept-Language": "en-US,en;q=0.8"}
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                # Decode using declared charset or fallback to utf-8
                charset = resp.headers.get_content_charset() or "utf-8"
                return resp.read().decode(charset, errors="replace")
        except (HTTPError, URLError) as e:
            if attempt < retries:
                time.sleep(sleep_between * (attempt + 1))
                continue
            return None
        except Exception:
            if attempt < retries:
                time.sleep(sleep_between * (attempt + 1))
                continue
            return None

# -------------------------
# Parsing helpers
# -------------------------

def _normalize_whitespace(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _clean_anchor_text(html_text: str) -> str:
    # remove tags
    text = re.sub(r"<[^>]+>", " ", html_text)
    text = unescape(text)
    return _normalize_whitespace(text)


def _extract_year(text: str):
    # Try to find a (YYYY) or separate year token
    m = re.search(r"\((19\d{2}|20\d{2})\)", text)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            pass
    # try trailing year token
    m = re.search(r"(?:^|\s)(19\d{2}|20\d{2})(?:$|\s)", text)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            pass
    return None


def _extract_titles_from_section(html: str, max_items: int = 20):
    """Extract titles from a section of HTML where items are anchors to /title/ pages.
    Returns list of strings (title text) in order of appearance.
    """
    items = []
    # Common anchor patterns on FlixPatrol that include the title text near <a href="/title/...">
    # We capture the anchor block to then clean the visible text.
    for m in re.finditer(r"<a[^>]+href=\"/title/[^\"]+\"[^>]*>(.*?)</a>", html, flags=re.IGNORECASE | re.DOTALL):
        anchor_inner = m.group(1)
        title_text = _clean_anchor_text(anchor_inner)
        # filter out empty or non-title anchors
        if not title_text or len(title_text) < 2:
            continue
        # Avoid collecting duplicates from nested anchors
        if items and title_text == items[-1]:
            continue
        items.append(title_text)
        if len(items) >= max_items:
            break
    # De-duplicate while preserving order
    seen = set()
    unique = []
    for t in items:
        if t.lower() in seen:
            continue
        seen.add(t.lower())
        unique.append(t)
    return unique


def _slice_between(html: str, start_marker: str, end_marker: str | None = None, max_len: int = 120000):
    pos = html.lower().find(start_marker.lower())
    if pos < 0:
        return None
    segment = html[pos: pos + max_len]
    if end_marker:
        end_pos = segment.lower().find(end_marker.lower())
        if end_pos > 0:
            segment = segment[:end_pos]
    return segment


def parse_hulu_movies_from_streaming_page(html: str) -> list[str]:
    """Parse the 'Hulu TOP 10' Movies section from the aggregated streaming page."""
    # Narrow down to Hulu block first
    block = _slice_between(html, "Hulu TOP 10", end_marker="TOP 10 on", max_len=60000)
    if not block:
        # fallback: try more generic block boundaries
        block = _slice_between(html, "Hulu TOP 10", end_marker="TOP 10", max_len=60000)
    if not block:
        return []
    # Within Hulu block, find Movies section up to TV Shows section or end
    movies_sec = _slice_between(block, "TOP 10 Movies", end_marker="TOP 10 TV", max_len=30000)
    if not movies_sec:
        # Another possible case: only movies are present
        movies_sec = _slice_between(block, "TOP 10 Movies", end_marker=None, max_len=30000)
    if not movies_sec:
        return []
    titles = _extract_titles_from_section(movies_sec, max_items=30)
    return titles


def parse_hulu_movies_from_platform_daily_page(html: str) -> list[str]:
    """Parse the per-platform daily Hulu page to extract Movies list (aiming for >=15)."""
    # Find Movies section
    movies_sec = _slice_between(html, "TOP 10 Movies", end_marker="TOP 10 TV", max_len=80000)
    if not movies_sec:
        movies_sec = _slice_between(html, "TOP Movies", end_marker="TOP TV", max_len=80000)
    if not movies_sec:
        # fallback to any 'Movies' heading
        movies_sec = _slice_between(html, ">Movies<", end_marker=">TV", max_len=80000)
    if not movies_sec:
        return []
    titles = _extract_titles_from_section(movies_sec, max_items=50)
    return titles

# -------------------------
# Orchestrator
# -------------------------

def fetch_daily_top15(date: dt.date, sleep_between: float = 0.5) -> dict:
    """Attempt to get Hulu daily Top 15 movies for a particular date.
    Returns dict: { 'date': 'YYYY-MM-DD', 'items': [ {rank,title,year,content_type,source_url}, ... ], 'notes': [...]}.
    """
    ymd = date.strftime("%Y-%m-%d")
    notes: list[str] = []

    # 1) Try per-platform daily page
    url_platform = f"https://flixpatrol.com/top10/{PLATFORM_SLUG}/{COUNTRY_SLUG}/{ymd}/"
    html = http_get(url_platform)
    titles = []
    if html:
        titles = parse_hulu_movies_from_platform_daily_page(html)
        if titles:
            notes.append(f"Parsed {len(titles)} from platform page")
        else:
            notes.append("Platform daily page parsed 0 items")
    else:
        notes.append("Platform daily page fetch failed")

    # 2) If fewer than 15, try aggregated streaming page for Hulu block
    if len(titles) < 15:
        time.sleep(sleep_between)
        url_streaming = f"https://flixpatrol.com/top10/streaming/{COUNTRY_SLUG}/{ymd}/"
        html2 = http_get(url_streaming)
        if html2:
            titles2 = parse_hulu_movies_from_streaming_page(html2)
            if titles2:
                notes.append(f"Parsed {len(titles2)} from streaming page (Hulu block)")
                # Merge unique while preserving platform page order first
                seen = set(t.lower() for t in titles)
                for t in titles2:
                    if t.lower() not in seen:
                        titles.append(t)
                        seen.add(t.lower())
            else:
                notes.append("Streaming page Hulu block parsed 0 items")
        else:
            notes.append("Streaming page fetch failed")

    # 3) Trim to Top 15 and assemble items
    items = []
    for idx, title in enumerate(titles[:15], start=1):
        items.append({
            "rank": idx,
            "title": title,
            "year": _extract_year(title),
            "content_type": "movie",
            "source_url": url_platform if html else (url_streaming if 'url_streaming' in locals() else None)
        })

    # If we got fewer than 15, record note
    if len(items) < 15:
        notes.append(f"Only {len(items)} items available; could not fill Top 15")

    return {"date": ymd, "items": items, "notes": notes}


def fetch_recent(days: int = 3, sleep_between: float = 0.5) -> dict:
    """Fetch recent days. Returns structured JSON with metadata and results array."""
    today = dt.date.today()
    dates = [today - dt.timedelta(days=i) for i in range(days)]
    results = []
    for d in dates:
        results.append(fetch_daily_top15(d, sleep_between=sleep_between))
        time.sleep(sleep_between)
    payload = {
        "metadata": {
            "country": COUNTRY_SLUG,
            "attempted_days": days,
            "generated_at": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "source": "flixpatrol",
            "platform": PLATFORM_SLUG,
        },
        "results": results,
    }
    return payload

# -------------------------
# Rendering helpers
# -------------------------

def to_text(payload: dict) -> str:
    lines = []
    md = payload.get("metadata", {})
    lines.append(f"Hulu Daily Top 15 Movies — country={md.get('country','united-states')} generated_at={md.get('generated_at','')}")
    for day in payload.get("results", []):
        lines.append("")
        lines.append(f"Date: {day['date']}")
        for item in day.get("items", []):
            yr = f" ({item['year']})" if item.get("year") else ""
            lines.append(f"  {item['rank']:>2}. {item['title']}{yr}")
        if day.get("notes"):
            lines.append("  Notes: " + "; ".join(day["notes"]))
    return "\n".join(lines)

# -------------------------
# CLI
# -------------------------

def main(argv=None):
    p = argparse.ArgumentParser(description="Fetch Hulu Daily Top 15 Movies (US)")
    p.add_argument("--days", type=int, default=3, help="How many recent days to fetch (default: 3)")
    p.add_argument("--format", choices=["json", "text"], default="json", help="Output format")
    p.add_argument("--sleep", type=float, default=0.5, help="Sleep seconds between requests")
    p.add_argument("--country", default=COUNTRY_SLUG, help="Country slug (currently only 'united-states' is supported)")
    p.add_argument("--output", default=None, help="Output file path (optional)")
    args = p.parse_args(argv)

    if args.country != COUNTRY_SLUG:
        print(f"Warning: Only '{COUNTRY_SLUG}' is supported right now; ignoring '{args.country}'.", file=sys.stderr)

    payload = fetch_recent(days=max(1, args.days), sleep_between=max(0.0, args.sleep))

    if args.format == "json":
        out = json.dumps(payload, ensure_ascii=False, indent=2)
    else:
        out = to_text(payload)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(out)
        print(args.output)
    else:
        print(out)


if __name__ == "__main__":
    sys.exit(main())

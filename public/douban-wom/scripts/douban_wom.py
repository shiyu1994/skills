#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fetch and parse Douban's weekly word-of-mouth (一周口碑榜) movie rankings.

Defaults: print current top 5 as JSON.
Optional: --recent N to include N archived weeks (Wayback snapshots) in addition to current.
"""
from __future__ import annotations
import argparse
import json
import re
import time
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple

import requests
from bs4 import BeautifulSoup  # ensure installed in environment

from html_parsers import parse_weekly_top

CURRENT_URL = "https://movie.douban.com/chart?t=1477886984558"
WAYBACK_CDX = "https://web.archive.org/cdx/search/cdx"
WAYBACK_FETCH_TMPL = "https://web.archive.org/web/{timestamp}id_/{url}"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


def http_get(url: str, timeout: float = 15.0, max_retries: int = 2) -> requests.Response:
    last_err: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        try:
            resp = requests.get(url, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"}, timeout=timeout)
            if resp.status_code == 200:
                return resp
            # Occasionally non-200; small backoff
            time.sleep(1.2 * (attempt + 1))
        except Exception as e:
            last_err = e
            time.sleep(1.2 * (attempt + 1))
    if last_err:
        raise last_err
    raise RuntimeError(f"Failed to GET {url}")


def fetch_current() -> Dict[str, object]:
    resp = http_get(CURRENT_URL)
    html = resp.text
    data = parse_weekly_top(html, limit=5)
    # Add current year best-effort inference for label
    year = datetime.now().year
    return {
        "source": CURRENT_URL,
        "is_archive": False,
        "year_guess": year,
        **data,
    }


def cdx_snapshots(url: str, limit: int = 10, years_back: int = 2) -> List[Dict[str, str]]:
    """Query Wayback CDX API for recent snapshots of the target URL."""
    now = datetime.now(timezone.utc)
    params = {
        "url": url,
        "output": "json",
        "filter": ["statuscode:200"],
        "limit": str(max(1, limit * 4)),  # ask extra, will filter later
        "collapse": "timestamp:7",  # collapse to daily snapshot
        # restrict time window to reduce irrelevant noise
        "from": str(now.year - years_back),
        "to": str(now.year),
    }
    # Query CDX
    r = requests.get(WAYBACK_CDX, params=params, headers={"User-Agent": UA}, timeout=20)
    r.raise_for_status()
    data_text = r.text

    try:
        data = json.loads(data_text)
    except Exception:
        # Some CDX deployments return CSV-like text; fallback parse
        lines = [ln for ln in data_text.splitlines() if ln.strip()]
        if not lines:
            return []
        headers = lines[0].strip().split(" ")
        rows = []
        for ln in lines[1:]:
            parts = ln.split(" ")
            row = {h: (parts[i] if i < len(parts) else "") for i, h in enumerate(headers)}
            rows.append(row)
        return rows[:limit]

    # First row is headers when JSON
    if not data or len(data) < 2:
        return []
    headers = data[0]
    rows = [dict(zip(headers, row)) for row in data[1:]]
    # Sort desc by timestamp (string compare safe) and take `limit`
    rows.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
    return rows[:limit]


def fetch_archive(timestamp: str) -> Dict[str, object]:
    url = WAYBACK_FETCH_TMPL.format(timestamp=timestamp, url=CURRENT_URL)
    resp = http_get(url)
    html = resp.text
    data = parse_weekly_top(html, limit=5)
    # Year from timestamp (YYYYmmdd..)
    year = None
    m = re.match(r"^(\d{4})", timestamp)
    if m:
        year = int(m.group(1))
    return {
        "source": url,
        "is_archive": True,
        "year_guess": year,
        **data,
    }


def run(recent: int = 0) -> Dict[str, object]:
    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "current": None,
        "recent_archives": [],
        "notes": [],
    }
    # Current
    try:
        out["current"] = fetch_current()
    except Exception as e:
        out["current"] = {"error": f"failed_current: {e}"}

    # Archives
    if recent and recent > 0:
        try:
            snaps = cdx_snapshots(CURRENT_URL, limit=recent)
        except Exception as e:
            out["notes"].append(f"archive_list_error: {e}")
            snaps = []
        for snap in snaps:
            ts = snap.get("timestamp")
            if not ts:
                continue
            try:
                archive = fetch_archive(ts)
            except Exception as e:
                archive = {"error": f"failed_archive_{ts}: {e}", "timestamp": ts}
            out["recent_archives"].append(archive)
    return out


def main():
    parser = argparse.ArgumentParser(description="Parse Douban weekly WOM top 5 movies.")
    parser.add_argument("--recent", type=int, default=0, help="Include N archived recent weeks (Wayback)")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()

    result = run(recent=args.recent)
    if args.pretty:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Fetch and parse Douban Movie weekly word-of-mouth ranking (一周口碑榜).

This script is designed to be used by the douban-wom Claude Skill.
It fetches https://movie.douban.com/chart and extracts the movies
ranked 1–5 in the 一周口碑榜 section.

It relies only on the Python standard library for maximum portability.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any


DOUBAN_CHART_URL = "https://movie.douban.com/chart"


@dataclass
class WeeklyMovie:
    """Structured data for a single movie on the weekly word-of-mouth chart."""

    rank: int
    title: str
    url: str
    trend: Optional[str] = None  # e.g. "+3", "-2", "0" or None if unavailable


@dataclass
class WeeklyRanking:
    """Container for the weekly ranking results."""

    week_label: Optional[str]  # e.g. "11月28日 更新", or None if not found
    source_url: str
    movies: List[WeeklyMovie]


class DoubanChartError(RuntimeError):
    """Base error type for this module."""


def fetch_chart_html(url: str = DOUBAN_CHART_URL, timeout: int = 10) -> str:
    """Fetch the Douban chart page HTML.

    Uses a desktop User-Agent to reduce the risk of being blocked.
    Raises DoubanChartError on network or decoding issues.
    """

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        )
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            # Douban typically uses UTF-8
            charset = resp.headers.get_content_charset() or "utf-8"
            return resp.read().decode(charset, errors="replace")
    except Exception as exc:  # noqa: BLE001
        raise DoubanChartError(f"Failed to fetch Douban chart page: {exc}") from exc


def _extract_week_section(html: str) -> str:
    """Return the HTML fragment for the 一周口碑榜 <ul>.

    This looks for the <ul class="content" id="listCont2"> section.
    Raises DoubanChartError if the section cannot be found.
    """

    # First try to locate by id, which is most stable
    id_pos = html.find('id="listCont2"')
    if id_pos == -1:
        raise DoubanChartError("Could not find weekly word-of-mouth list (id=listCont2) in page HTML.")

    # Walk backwards to the opening <ul ...> tag
    ul_start = html.rfind("<ul", 0, id_pos)
    if ul_start == -1:
        raise DoubanChartError("Found listCont2 id but could not locate enclosing <ul> tag.")

    # Find the closing </ul> tag after the id position
    ul_end = html.find("</ul>", id_pos)
    if ul_end == -1:
        raise DoubanChartError("Could not find closing </ul> for weekly list.")

    ul_end += len("</ul>")
    return html[ul_start:ul_end]


def _parse_week_label(html: str) -> Optional[str]:
    """Extract the update label from the 一周口碑榜 heading, if present.

    Example snippet:
        <h2>一周口碑榜· · · · · · <span class="box_chart_num color-gray">11月28日 更新</span></h2>
    """

    # Restrict search to the broader ranking section for robustness
    heading_pattern = re.compile(
        r"<h2>\s*一周口碑榜[\s\S]*?<span[^>]*>([^<]+)</span>",
        re.IGNORECASE,
    )
    m = heading_pattern.search(html)
    if not m:
        return None
    return m.group(1).strip()


def _parse_weekly_movies(ul_html: str) -> List[WeeklyMovie]:
    """Parse the <ul> fragment into a list of WeeklyMovie entries.

    The structure looks like:

        <li class="clearfix">
            <div class="no">1</div>
            <div class="name">
                <a ... href="https://movie.douban.com/subject/.../">\n  片名\n</a>
            </div>
            <span>
                <div class="up">10</div>
            </span>
        </li>
    """

    # Extract individual <li> blocks
    li_pattern = re.compile(r"<li[^>]*>([\s\S]*?)</li>")
    li_blocks = li_pattern.findall(ul_html)
    movies: List[WeeklyMovie] = []

    for li in li_blocks:
        # Rank
        rank_match = re.search(r"<div\\s+class=\"no\">\\s*(\\d+)\\s*</div>", li)
        if not rank_match:
            # Skip malformed entries rather than failing everything
            continue
        rank = int(rank_match.group(1))

        # URL and title
        a_match = re.search(
            r"<a[^>]*href=\"([^\"]+)\"[^>]*>([\s\S]*?)</a>",
            li,
            re.IGNORECASE,
        )
        if not a_match:
            continue
        url = a_match.group(1).strip()

        # Inner text may contain spans and newlines; strip tags then whitespace
        raw_title_html = a_match.group(2)
        # Remove nested tags
        title_text = re.sub(r"<[^>]+>", "", raw_title_html)
        title = " ".join(title_text.split())  # normalize whitespace

        # Trend (up/down/no change). The page uses <div class="up">N</div> etc.
        trend_match = re.search(
            r"<div\\s+class=\"(up|down)\">\\s*(\\d+)\\s*</div>",
            li,
        )
        trend: Optional[str]
        if trend_match:
            direction, amount = trend_match.groups()
            sign = "+" if direction == "up" else "-"
            trend = f"{sign}{amount}"
        else:
            # Could be no-change or missing; represent as None
            trend = None

        movies.append(WeeklyMovie(rank=rank, title=title, url=url, trend=trend))

    # Sort defensively by rank
    movies.sort(key=lambda m: m.rank)
    return movies


def parse_weekly_ranking_from_html(html: str) -> WeeklyRanking:
    """Parse a full Douban chart page HTML into a WeeklyRanking.

    This is separated from network fetching so it can be unit-tested
    using stored HTML fixtures.
    """

    ul_html = _extract_week_section(html)
    week_label = _parse_week_label(html)
    movies = _parse_weekly_movies(ul_html)
    return WeeklyRanking(week_label=week_label, source_url=DOUBAN_CHART_URL, movies=movies)


def fetch_current_week_top5() -> WeeklyRanking:
    """Fetch the current weekly word-of-mouth ranking and return top 1–5 movies.

    If the list has fewer than 5 entries, all available entries are returned.
    """

    html = fetch_chart_html()
    ranking = parse_weekly_ranking_from_html(html)

    # Keep only ranks 1–5 while preserving order
    top = [m for m in ranking.movies if 1 <= m.rank <= 5]
    ranking.movies = top[:5]
    return ranking


def as_json_serializable(ranking: WeeklyRanking) -> Dict[str, Any]:
    """Return a JSON-serializable representation of WeeklyRanking."""

    return {
        "week_label": ranking.week_label,
        "source_url": ranking.source_url,
        "movies": [asdict(m) for m in ranking.movies],
    }


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point.

    Prints a JSON object with week_label, source_url and movies[rank,title,url,trend].
    """

    _ = argv  # currently unused, reserved for future options
    try:
        ranking = fetch_current_week_top5()
    except DoubanChartError as exc:
        sys.stderr.write(str(exc) + "\n")
        return 1

    print(json.dumps(as_json_serializable(ranking), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover - direct execution path
    raise SystemExit(main())

---
name: douban-wom
description: "Fetch and parse Douban Movie weekly word-of-mouth ranking (一周口碑榜) from movie.douban.com/chart and extract the movies ranked 1–5. Use this skill whenever the user asks about the top entries on Douban's weekly word-of-mouth movie chart, wants a quick summary of the current weekly word-of-mouth movie rankings, or needs structured data (title, rank, URL, trend) for the top 1–5 movies without providing any URLs or HTML themselves."
---

# Douban weekly word-of-mouth movies

## Purpose

Provide a reliable, repeatable way to retrieve and parse the "一周口碑榜" (weekly word-of-mouth chart)
from https://movie.douban.com/chart and return the movies ranked 1–5 as structured data.

The user should never be asked to supply URLs or raw HTML. This skill is self-contained: it knows
where to fetch data from and how to parse it.

## Quick usage pattern

1. When the user asks about the current Douban weekly word-of-mouth ranking (especially top N
   movies), trigger this skill based on the description.
2. Run the parser script to obtain the current top 1–5 movies:
   - Preferred: execute `scripts/douban_wom_chart.py` and use its JSON output.
   - Fallback (for debugging): inspect the script source and adapt the parsing logic if the page
     markup changes.
3. Present a concise summary first (progressive disclosure):
   - Give the week label (if available) and the top 1–5 titles with their ranks.
   - Only if the user asks for more, add Douban subject URLs or trend (up/down) details.

## Workflow

The typical workflow for this skill is:

1. **Fetch HTML**
   - Use `fetch_chart_html()` from `scripts/douban_wom_chart.py` to download
     `https://movie.douban.com/chart`.
   - The script already sets an appropriate User-Agent and handles decoding.

2. **Parse weekly ranking**
   - Call `parse_weekly_ranking_from_html(html)` to obtain a `WeeklyRanking` object.
   - This function:
     - Locates the 一周口碑榜 `<ul class="content" id="listCont2">` section.
     - Extracts the update label from the heading (e.g. `11月28日 更新`) when present.
     - Parses each `<li>` into `WeeklyMovie(rank, title, url, trend)`.

3. **Limit to ranks 1–5**
   - Use `fetch_current_week_top5()` for the common case; it returns a `WeeklyRanking` instance
     where `movies` already contains only ranks 1–5 (or fewer if the list is shorter).

4. **Return results to the user**
   - Start with a compact, human-readable answer, for example:

     "本周豆瓣电影一周口碑榜前五名是：1. 疯狂动物城2 2. 火车梦 3. 人偶之家 4. 太空百合战姬 5. 普通事故。"

   - If the user asks for structured data, serialize `WeeklyRanking` via `as_json_serializable()`
     in the script to get a dict with `week_label`, `source_url`, and a `movies` list containing
     `rank`, `title`, `url`, and `trend`.

## Scripts in this skill

All scripts live in `scripts/` and rely only on the Python standard library.

### `scripts/douban_wom_chart.py`

Core functionality for this skill.

Key functions:

- `fetch_chart_html(url=DOUBAN_CHART_URL, timeout=10) -> str`
  - Downloads the Douban chart page HTML.
  - Raises `DoubanChartError` on network/decoding failure.

- `parse_weekly_ranking_from_html(html: str) -> WeeklyRanking`
  - Parses a full chart HTML string.
  - Returns a `WeeklyRanking` with `week_label`, `source_url`, and a list of `WeeklyMovie`.

- `fetch_current_week_top5() -> WeeklyRanking`
  - Convenience helper that fetches the page and returns only ranks 1–5.

- `as_json_serializable(ranking: WeeklyRanking) -> dict`
  - Converts `WeeklyRanking` to a JSON-serializable dict.

- CLI usage: running the script directly will print a nicely formatted JSON object with the
  current top 1–5 movies, for example:

  ```json
  {
    "week_label": "11月28日 更新",
    "source_url": "https://movie.douban.com/chart",
    "movies": [
      {"rank": 1, "title": "疯狂动物城2", "url": "https://movie.douban.com/subject/26817136/", "trend": "+10"},
      ... up to rank 5 ...
    ]
  }
  ```

### `scripts/selftest.py`

Self-contained unit tests for the parser logic.

- Uses an embedded HTML snippet copied from the actual Douban chart page to test parsing.
- Covers the following cases:
  - Correct extraction of the weekly `<ul id="listCont2">` section.
  - Correct parsing of the week label (e.g. `11月28日 更新`).
  - Correct parsing of ranks, titles, URLs, and trends for a typical 10-item list.
  - Handling of pages with fewer than 5 items.
  - Graceful failure when the weekly section is missing.

Run this script during maintenance or when Douban changes the page layout to quickly validate that
parsing still works.

## Progressive disclosure guidelines

When using this skill in a conversation:

1. **Start simple**
   - Provide only the ranked list of titles (1–5) and, optionally, the week label.
   - Avoid dumping raw JSON or excessive metadata unless the user explicitly requests it.

2. **Offer more detail on demand**
   - If the user asks for links, add the Douban subject URLs.
   - If they care about movement on the chart, surface the `trend` field (e.g. `+3` or `-1`).
   - Only if they ask for structured data, present a JSON-like structure or table.

3. **Handle errors clearly**
   - If the HTML structure changes and parsing fails, explain succinctly that the Douban chart
     layout appears to have changed and parsing did not succeed.
   - When possible, inspect and patch `scripts/douban_wom_chart.py` to adapt to the new structure,
     re-run the self-tests, and then try again.

By following this pattern, the skill remains token-efficient while still supporting rich, detailed
output when the user needs it.

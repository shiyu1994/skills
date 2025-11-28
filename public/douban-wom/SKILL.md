---
name: douban-wom
description: Parse the top 1–5 movies from Douban's weekly word-of-mouth movie ranking. Use when Claude needs current or recent-week lists from movie.douban.com/chart (一周口碑榜). Includes scripts to fetch the live chart and recent weeks via Wayback snapshots, returning clean JSON without requiring user input.
---

# Douban Weekly Word-of-Mouth (Movies)

Minimal, reliable tools to extract the weekly “一周口碑榜” (word-of-mouth) movie rankings from Douban.

## Quick start (no inputs required)

- Get current week top 5 as JSON:
  - Run scripts/douban_wom.py (no args)
- Get current + recent weeks (archives) as JSON:
  - Run scripts/douban_wom.py --recent 4

Outputs include: week_label (e.g., "11月28日 更新"), inferred_year (best effort), and entries [{rank, title, url}].

## What this Skill does

- Scrapes “一周口碑榜” from https://movie.douban.com/chart?t=1477886984558
- Robustly parses the section headed by “一周口碑榜” regardless of minor DOM shifts
- Falls back to Internet Archive snapshots to retrieve recent past weeks
- Normalizes and returns the top 5

## Usage patterns

- Need current week’s top 5 movies (official Douban chart)
- Compare how rankings changed across recent weeks
- Retrieve titles/links in a machine-usable format (JSON)

## Script reference

- scripts/douban_wom.py
  - main entrypoint. No-arg default prints current top 5. Use --recent N to include N archived weeks.
- scripts/html_parsers.py
  - DOM parsing utilities for the chart page (kept small and resilient; depends on BeautifulSoup).

## Implementation notes

- Networking: uses requests with desktop User-Agent, timeout, and simple retry.
- Parsing: finds the H2 that contains “一周口碑榜”, then the nearest UL.content list items; trims whitespace and limits to rank 1–5.
- Archives: queries Wayback CDX API for the latest valid snapshots, fetches the archived chart pages and parses the same section.
- Year inference: since the visible label is like “11月28日 更新”, we infer year from snapshot timestamp (archives) or current year (live). The label is preserved as-is.

## Troubleshooting

- If live fetch is blocked/403, the script will still return archived weeks when --recent is provided. For live-only runs, it retries with backoff and returns a clear error message if unavailable.
- If the DOM changes substantially, see scripts/html_parsers.py; adjust the selector near find_weekly_wom_section.


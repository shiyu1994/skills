---
name: hulu-daily-top15-movies
description: Parse and report Hulu Daily Top 15 Movies for recent days in the United States. Automatically fetches daily charts (no user inputs required) from reliable public sources and outputs normalized results (JSON and text). Use this skill when you need Hulu daily movie rankings (Top 15) for today or the past N days, and for validating or comparing daily lists.
---

# Hulu Daily Top 15 Movies Parser

Overview

This skill automatically fetches and parses Hulu's daily Top 15 Movies lists for recent days (default: United States, last 3–7 days). It is fully self-contained and does not require the user to supply URLs or parameters.

What this skill does

- Retrieves daily Hulu Movies rankings for recent dates (default country: United States) from public chart aggregators
- Normalizes rankings to a consistent schema (date, rank, title, year if available, content_type, source_url)
- Returns results in JSON (default) or human-readable text
- Handles network errors, partial data, and content structure changes with fallbacks and heuristics
- Includes an automated test suite and offline parser tests for regression safety

When to use this skill

- "Get the Hulu Daily Top 15 Movies for the last X days"
- "What’s Hulu’s Top Movies today and yesterday?"
- "Export Hulu daily Top 15 Movies as JSON/CSV"

Primary data source

- FlixPatrol daily charts (public):
  - Per-platform daily page: https://flixpatrol.com/top10/hulu/united-states/YYYY-MM-DD/
  - Aggregated streaming page: https://flixpatrol.com/top10/streaming/united-states/YYYY-MM-DD/

Note: FlixPatrol is a widely used aggregator of daily streaming charts. Exact page markup may evolve; this skill’s parser is designed with resilient heuristics and multiple fallbacks.

Outputs

- JSON array per date with objects: { date, rank, title, year?, content_type: "movie", source_url }
- Text summary per date (ranked list)

How to run

- Default (last 3 days, JSON):
  - scripts/hulu_top15.py
- With options:
  - scripts/hulu_top15.py --days 7 --format text
- Save JSON to a file:
  - scripts/hulu_top15.py --days 7 --output out.json

Public scripts

- scripts/hulu_top15.py
  - Fetch and parse Hulu Daily Top 15 Movies for recent days. CLI options:
    - --days N (default: 3)
    - --format json|text (default: json)
    - --sleep SECONDS between network calls (default: 0.5)
    - --country united-states (default, currently supported)
    - --output FILEPATH (optional)

- scripts/test_hulu_top15.py
  - Runs parser unit tests with offline HTML fixtures and live fetch integration tests (best-effort; handles network errors gracefully).

Implementation notes

- The parser first tries the per-platform daily page for Hulu (which may include more than 10 entries in the full chart). If fewer than 15 movies are available from that page, it falls back to the aggregated streaming page and merges unique movie titles to fill up to 15 items when possible.
- If only 10 items are available after all fallbacks, the script will return those 10 with a warning note in the metadata.
- HTTP requests use a desktop User-Agent and short delays to be polite.
- Only Python standard library is used (urllib, html.parser, re, json, datetime, time). No external dependencies required.

Returned structure

- Top-level JSON: { "metadata": { "country": "united-states", "attempted_days": N, "generated_at": ISO8601 }, "results": [ { "date": "YYYY-MM-DD", "items": [ { "rank": 1, "title": "...", "year": 2024?, "content_type": "movie", "source_url": "..." }, ... ] } ] }

Troubleshooting

- Network errors or temporary blocks (HTTP 403/429) will be retried with short backoff; if persistent, the script returns partial results with error notes.
- If page markup changes, the offline unit tests still validate the parser against known HTML snapshots to keep functionality robust. Update heuristics when needed in scripts/hulu_top15.py.


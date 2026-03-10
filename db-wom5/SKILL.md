---
name: db-wom5
description: Fetch and parse Douban’s weekly word-of-mouth movie ranking (一周口碑电影榜) and extract ranks 1–5 (optionally for several recent weeks) using Douban mobile (m.douban.com) rexxar JSON endpoints. Use when you need the current weekly “口碑榜” top 5 in a structured form (JSON/CSV/table) without user-provided URLs.
---

# Douban weekly WOM top 5

## Workflow

1. Run `scripts/fetch_weekly_wom.py` to fetch Douban“一周口碑电影榜” and print ranks **1–5**.
   - Defaults to attempting multiple recent weeks; falls back to the latest week if Douban doesn’t expose history.

2. If output looks wrong or Douban changes response formats, run `scripts/test_weekly_wom.py`.

## Output contract (what to report)

When presenting results, use this structure:

- `week_label`: a human-readable label for the week (best-effort)
- `fetched_at`: ISO timestamp
- `source`: the exact URL used
- `items`: list of 5 objects with:
  - `rank` (1..5)
  - `title`
  - `rating` (float or null)
  - `good_rate` (0..1 float or null)
  - `year` (int or null)
  - `countries` (list)
  - `genres` (list)
  - `subject_id` (string/int or null)
  - `subject_url` (string or null)

## Bundled resources

- `scripts/douban_wom.py`: HTTP + parsing utilities (JSON-shape tolerant)
- `scripts/fetch_weekly_wom.py`: main runnable (no input required)
- `scripts/test_weekly_wom.py`: unit + lightweight integration tests

#!/usr/bin/env python3
"""Fetch Douban weekly word-of-mouth movie ranking (一周口碑电影榜) top 1-5.

No user input required.

Usage (optional):
  python fetch_weekly_wom.py            # fetch latest, attempt recent weeks
  python fetch_weekly_wom.py --weeks 8  # attempt more weeks (if supported)
  python fetch_weekly_wom.py --json     # machine-readable JSON

Runner note:
Some execution harnesses pass an empty-string argv entry; this script filters
empty args for robustness.
"""

from __future__ import annotations

import argparse
import json
import sys

from douban_wom import DoubanFetchError, fetch_recent_weeks, to_jsonable, format_table


def main(argv=None) -> int:
    # Robustly handle runners that pass empty args.
    if argv is None:
        argv = sys.argv[1:]
    argv = [a for a in argv if a]

    p = argparse.ArgumentParser(add_help=True)
    p.add_argument("--weeks", type=int, default=6)
    p.add_argument("--json", action="store_true", help="print JSON instead of markdown table")
    args = p.parse_args(argv)

    try:
        weeks = fetch_recent_weeks(max_weeks=max(1, args.weeks))
    except DoubanFetchError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(to_jsonable(weeks), ensure_ascii=False, indent=2))
        return 0

    # Human readable.
    for i, w in enumerate(weeks):
        if i:
            print("\n\n---\n")
        print(format_table(w))

    if len(weeks) == 1:
        print("\n\nNOTE: Only the latest week was returned (Douban may not expose history for this list via the public endpoint).")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

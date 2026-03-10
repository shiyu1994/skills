#!/usr/bin/env python3
"""Backwards-compatible entrypoint.

This file exists only because the skill template creates it.
It simply runs `fetch_weekly_wom.py`.
"""

from fetch_weekly_wom import main


if __name__ == "__main__":
    raise SystemExit(main())

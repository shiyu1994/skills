#!/usr/bin/env python3
"""Remove development/runtime artifacts that should not ship with the skill.

Safe to run multiple times.

Removes:
- __pycache__/ and *.pyc
- one-off exploration scripts used during skill development
"""

from __future__ import annotations

import shutil
from pathlib import Path


DEV_HELPERS = [
    "inspect_weekly_payload.py",
    "inspect_collection_meta.py",
    "inspect_chart_endpoints.py",
    "inspect_skynet.py",
    "probe_history_params.py",
    "print_chart_id.py",
]


def main() -> None:
    here = Path(__file__).resolve().parent

    # Remove __pycache__ under scripts/
    for p in here.rglob("__pycache__"):
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
            print("removed", p)

    # Remove .pyc files if any remain
    for p in here.rglob("*.pyc"):
        try:
            p.unlink()
            print("removed", p)
        except FileNotFoundError:
            pass

    # Remove dev helper scripts
    for name in DEV_HELPERS:
        p = here / name
        if p.exists():
            p.unlink()
            print("removed", p)


if __name__ == "__main__":
    main()

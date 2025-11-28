#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test the HTML parser against local fixtures to validate corner cases.
"""
import json
from pathlib import Path
from html_parsers import parse_weekly_top

BASE = Path(__file__).resolve().parent.parent / 'assets' / 'fixtures'

def run_case(name):
    html = (BASE / name).read_text(encoding='utf-8')
    return parse_weekly_top(html, limit=5)


def main():
    results = {}
    for fname in [
        'fixture_current_like.html',
        'fixture_alt_ul_id.html',
        'fixture_missing_section.html',
    ]:
        results[fname] = run_case(fname)
    print(json.dumps(results, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()

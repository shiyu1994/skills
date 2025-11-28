#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from pathlib import Path
from html_parsers import parse_weekly_top

html = (Path(__file__).resolve().parent.parent / 'assets' / 'fixtures' / 'fixture_short_list.html').read_text(encoding='utf-8')
print(json.dumps(parse_weekly_top(html, limit=5), ensure_ascii=False, indent=2))

#!/usr/bin/env python3
"""Self-tests for Douban weekly WOM parsing.

Runs:
- Unit tests with fixture payloads (no network)
- Optional integration test against live Douban endpoint

Usage:
  python test_weekly_wom.py

Note: Some runners pass an empty argv entry; we override argv in unittest.main
for robustness.
"""

from __future__ import annotations

import os
import unittest

from douban_wom import (
    DoubanFetchError,
    parse_weekly_items,
    fetch_weekly_top5,
)


FIXTURE_PAYLOAD_SHAPE_A = {
    "subject_collection": {"name": "一周口碑电影榜"},
    "subject_collection_items": [
        {
            "rank": 1,
            "title": "片名A",
            "rating": {"value": 8.1},
            "good_rating_stats": 77,
            "year": "2024",
            "countries": ["中国大陆"],
            "genres": ["剧情"],
            "id": "123",
            "url": "https://movie.douban.com/subject/123/",
        },
        {
            "rank": 2,
            "title": "片名B",
            "rating": 7.9,
            "good_rate": 0.74,
            "card_subtitle": "2025 / 日本 / 剧情",
            "subject_id": 456,
            "share_url": "https://movie.douban.com/subject/456/",
        },
        {
            "rank": 3,
            "name": "片名C",
            "rating": {"value": "8.0"},
            "good_rate": None,
            "year": None,
            "countries": None,
            "genres": None,
            "subject": {"id": 789, "url": "https://movie.douban.com/subject/789/"},
        },
        {"rank": 4, "title": "片名D", "rating": None},
        {"rank": 5, "title": "片名E", "rating": {"value": 6.5}},
        {"rank": 6, "title": "extra"},
    ],
}


FIXTURE_PAYLOAD_SHAPE_B = {
    "title": "一周口碑电影榜",
    "items": [
        {"title": f"片名{i}", "rating": {"value": 7.0 + i / 10.0}, "id": str(1000 + i)}
        for i in range(1, 11)
    ],
}


class TestParsing(unittest.TestCase):
    def test_parse_shape_a(self):
        items = parse_weekly_items(FIXTURE_PAYLOAD_SHAPE_A, top_n=5)
        self.assertEqual(len(items), 5)
        self.assertEqual([it.rank for it in items], [1, 2, 3, 4, 5])
        self.assertEqual(items[0].title, "片名A")
        self.assertAlmostEqual(items[0].good_rate or 0.0, 0.77, places=2)
        self.assertEqual(items[0].year, 2024)
        self.assertEqual(items[0].subject_id, "123")

        # card_subtitle fallback
        self.assertEqual(items[1].year, 2025)
        self.assertEqual(items[1].countries, ["日本"])
        self.assertEqual(items[1].genres, ["剧情"])

    def test_parse_shape_b(self):
        items = parse_weekly_items(FIXTURE_PAYLOAD_SHAPE_B, top_n=5)
        self.assertEqual(len(items), 5)
        self.assertEqual(items[0].title, "片名1")
        self.assertAlmostEqual(items[0].rating or 0.0, 7.1, places=3)

    def test_parse_too_few_items(self):
        with self.assertRaises(DoubanFetchError):
            parse_weekly_items({"items": [{"title": "x"}]}, top_n=5)


class TestIntegration(unittest.TestCase):
    @unittest.skipUnless(os.environ.get("DOUBAN_LIVE_TEST") == "1", "Set DOUBAN_LIVE_TEST=1 to run live test")
    def test_live_fetch(self):
        wk = fetch_weekly_top5()
        self.assertEqual(len(wk.items), 5)
        self.assertTrue(all(it.title for it in wk.items))
        self.assertEqual([it.rank for it in wk.items], [1, 2, 3, 4, 5])


if __name__ == "__main__":
    unittest.main(argv=["test_weekly_wom"], verbosity=2)

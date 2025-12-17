#!/usr/bin/env python3
"""
Offline and live tests for Hulu Daily Top 15 Movies parser.

Run: scripts/test_hulu_top15.py
"""
import datetime as dt
import json
import sys

from hulu_top15 import (
    parse_hulu_movies_from_streaming_page,
    parse_hulu_movies_from_platform_daily_page,
    fetch_daily_top15,
    fetch_recent,
)


STREAMING_SAMPLE_HTML = r"""
<div>
  <h2>Hulu TOP 10 in the United States on 2025-07-04</h2>
  <h3>TOP 10 Movies</h3>
  <ol>
    <li><a href="/title/movie-1/">Movie One (2024)</a></li>
    <li><a href="/title/movie-2/">Movie Two</a></li>
    <li><a href="/title/movie-3/">Movie Three (2023)</a></li>
    <li><a href="/title/movie-4/">Movie Four</a></li>
    <li><a href="/title/movie-5/">Movie Five</a></li>
    <li><a href="/title/movie-6/">Movie Six</a></li>
    <li><a href="/title/movie-7/">Movie Seven</a></li>
    <li><a href="/title/movie-8/">Movie Eight</a></li>
    <li><a href="/title/movie-9/">Movie Nine</a></li>
    <li><a href="/title/movie-10/">Movie Ten</a></li>
  </ol>
  <h3>TOP 10 TV Shows</h3>
  <ol>
    <li><a href="/title/show-1/">Show One</a></li>
  </ol>
</div>
"""

PLATFORM_SAMPLE_HTML = r"""
<section>
  <h2>TOP 10 Movies</h2>
  <ol>
    <li><a href="/title/movie-1/">Movie One (2024)</a></li>
    <li><a href="/title/movie-2/">Movie Two</a></li>
    <li><a href="/title/movie-3/">Movie Three (2023)</a></li>
    <li><a href="/title/movie-4/">Movie Four</a></li>
    <li><a href="/title/movie-5/">Movie Five</a></li>
    <li><a href="/title/movie-6/">Movie Six</a></li>
    <li><a href="/title/movie-7/">Movie Seven</a></li>
    <li><a href="/title/movie-8/">Movie Eight</a></li>
    <li><a href="/title/movie-9/">Movie Nine</a></li>
    <li><a href="/title/movie-10/">Movie Ten</a></li>
    <li><a href="/title/movie-11/">Movie Eleven</a></li>
    <li><a href="/title/movie-12/">Movie Twelve</a></li>
    <li><a href="/title/movie-13/">Movie Thirteen</a></li>
    <li><a href="/title/movie-14/">Movie Fourteen</a></li>
    <li><a href="/title/movie-15/">Movie Fifteen</a></li>
  </ol>
  <h2>TOP 10 TV Shows</h2>
</section>
"""


def assert_equal(a, b, msg=""):
    if a != b:
        raise AssertionError(f"{msg} Expected {b}, got {a}")


def test_parsers_offline():
    movies_s = parse_hulu_movies_from_streaming_page(STREAMING_SAMPLE_HTML)
    assert_equal(len(movies_s), 10, "streaming page should yield 10 movies")
    assert_equal(movies_s[0], "Movie One (2024)", "first movie")

    movies_p = parse_hulu_movies_from_platform_daily_page(PLATFORM_SAMPLE_HTML)
    assert_equal(len(movies_p), 15, "platform daily page should yield 15 movies")
    assert_equal(movies_p[10], "Movie Eleven", "11th movie")


def test_orchestrator_offline_merge():
    # Monkey patch http_get to return our samples
    import hulu_top15 as mod

    def fake_http_get(url: str, timeout: float = 20.0, retries: int = 2, sleep_between: float = 0.8):
        if "/top10/hulu/" in url:
            return PLATFORM_SAMPLE_HTML.replace("<li><a href=\"/title/movie-11/\">Movie Eleven</a></li>", "")\
                                      .replace("<li><a href=\"/title/movie-12/\">Movie Twelve</a></li>", "")\
                                      .replace("<li><a href=\"/title/movie-13/\">Movie Thirteen</a></li>", "")\
                                      .replace("<li><a href=\"/title/movie-14/\">Movie Fourteen</a></li>", "")\
                                      .replace("<li><a href=\"/title/movie-15/\">Movie Fifteen</a></li>", "")
        if "/top10/streaming/" in url:
            return STREAMING_SAMPLE_HTML.replace("Movie One (2024)", "Movie Eleven").replace("Movie Two", "Movie Twelve")\
                                        .replace("Movie Three (2023)", "Movie Thirteen").replace("Movie Four", "Movie Fourteen")\
                                        .replace("Movie Five", "Movie Fifteen")
        return None

    old_http_get = mod.http_get
    mod.http_get = fake_http_get
    try:
        today = dt.date(2025, 7, 4)
        res = fetch_daily_top15(today)
        assert_equal(len(res["items"]), 15, "merged list should reach 15")
        assert_equal(res["items"][10]["title"], "Movie Eleven", "11th merged title")
    finally:
        mod.http_get = old_http_get


def live_smoke_test():
    """Best-effort live test. Not fatal if network blocks occur."""
    try:
        payload = fetch_recent(days=2)
        # Require at least 1 day returned
        assert len(payload.get("results", [])) >= 1
        # Print a short summary to stdout
        print(json.dumps({
            "meta": payload.get("metadata", {}),
            "day0_items": [it["title"] for it in payload.get("results", [{}])[0].get("items", [])][:5]
        }, indent=2))
        print("Live smoke test completed (best effort).")
    except Exception as e:
        print(f"[WARN] Live smoke test skipped or failed: {e}")


if __name__ == "__main__":
    print("Running offline unit tests...")
    test_parsers_offline()
    test_orchestrator_offline_merge()
    print("OK: offline tests passed.")
    print("\nAttempting live smoke test (non-fatal)...")
    live_smoke_test()
    print("Done.")

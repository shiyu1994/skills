#!/usr/bin/env python3
"""Self-tests for the douban_wom_chart parser.

These tests operate only on stored HTML snippets so they can be run
without network access. They cover typical and corner cases.

Usage (from the skill root environment):

    python scripts/selftest.py

The script exits with code 0 on success and non-zero on failure.
"""

from __future__ import annotations

import sys

from douban_wom_chart import (
    parse_weekly_ranking_from_html,
    _extract_week_section,
    _parse_week_label,
    _parse_weekly_movies,
    WeeklyMovie,
)


# A minimal realistic snippet based on https://movie.douban.com/chart
REALISTIC_SNIPPET = r"""
<h2>一周口碑榜· · · · · · <span class="box_chart_num color-gray">11月28日 更新</span></h2>
<ul class="content" id="listCont2">
    <li class="clearfix">
        <div class="no">1</div>
        <div class="name">
            <a onclick="moreurl(this, {from:'mv_week'})" href="https://movie.douban.com/subject/26817136/">
                疯狂动物城2
            </a>
        </div>
        <span>
            <div class="up">10</div>
        </span>
    </li>
    <li class="clearfix">
        <div class="no">2</div>
        <div class="name">
            <a onclick="moreurl(this, {from:'mv_week'})" href="https://movie.douban.com/subject/36778356/">
                火车梦
            </a>
        </div>
        <span>
            <div class="up">9</div>
        </span>
    </li>
    <li class="clearfix">
        <div class="no">3</div>
        <div class="name">
            <a onclick="moreurl(this, {from:'mv_week'})" href="https://movie.douban.com/subject/37134889/">
                人偶之家
            </a>
        </div>
        <span>
            <div class="up">1</div>
        </span>
    </li>
    <li class="clearfix">
        <div class="no">4</div>
        <div class="name">
            <a onclick="moreurl(this, {from:'mv_week'})" href="https://movie.douban.com/subject/37162020/">
                太空百合战姬
            </a>
        </div>
        <span>
            <div class="up">7</div>
        </span>
    </li>
    <li class="clearfix">
        <div class="no">5</div>
        <div class="name">
            <a onclick="moreurl(this, {from:'mv_week'})" href="https://movie.douban.com/subject/37247238/">
                普通事故
            </a>
        </div>
        <span>
            <div class="up">6</div>
        </span>
    </li>
</ul>
"""


def assert_equal(a, b, msg: str = "") -> None:
    if a != b:
        raise AssertionError(msg or f"Assertion failed: {a!r} != {b!r}")


def test_extract_week_section() -> None:
    # Should find the <ul> even when surrounded by other content
    html = "<html><body>prefix" + REALISTIC_SNIPPET + "suffix</body></html>"
    ul_html = _extract_week_section(html)
    assert "id=\"listCont2\"" in ul_html
    assert ul_html.strip().startswith("<ul")
    assert ul_html.strip().endswith("</ul>")


def test_parse_week_label() -> None:
    html = "<div>before</div>" + REALISTIC_SNIPPET
    label = _parse_week_label(html)
    assert_equal(label, "11月28日 更新")


def test_parse_weekly_movies_basic() -> None:
    movies = _parse_weekly_movies(REALISTIC_SNIPPET)
    assert_equal(len(movies), 5)

    first = movies[0]
    assert isinstance(first, WeeklyMovie)
    assert_equal(first.rank, 1)
    assert_equal(first.title, "疯狂动物城2")
    assert_equal(first.url, "https://movie.douban.com/subject/26817136/")
    assert_equal(first.trend, "+10")

    last = movies[-1]
    assert_equal(last.rank, 5)
    assert_equal(last.title, "普通事故")
    assert_equal(last.trend, "+6")


def test_parse_weekly_ranking_from_html_top5() -> None:
    # Embed snippet in fake full page
    html = f"<html><body>{REALISTIC_SNIPPET}</body></html>"
    ranking = parse_weekly_ranking_from_html(html)
    assert_equal(ranking.week_label, "11月28日 更新")
    assert_equal(len(ranking.movies), 5)
    # Ranks should be sorted
    assert_equal([m.rank for m in ranking.movies], [1, 2, 3, 4, 5])


def test_handles_fewer_than_five_items() -> None:
    short_html = REALISTIC_SNIPPET.replace("<li class=\"clearfix\">", "", 3)  # crude way to reduce items
    movies = _parse_weekly_movies(short_html)
    # At least 2 items should remain
    assert len(movies) >= 2


def test_missing_section_graceful_failure() -> None:
    # When the weekly section is missing, _extract_week_section should raise,
    # which callers are expected to surface as a clear error.
    missing_html = "<html><body><h2>其它榜单</h2></body></html>"
    try:
        _extract_week_section(missing_html)
    except Exception:
        # Expected path: any exception type is acceptable for this unit test
        return
    raise AssertionError("Expected _extract_week_section to fail on missing weekly section")


def run_all_tests() -> None:
    # Keep this list flat for ease of maintenance
    tests = [
        test_extract_week_section,
        test_parse_week_label,
        test_parse_weekly_movies_basic,
        test_parse_weekly_ranking_from_html_top5,
        test_handles_fewer_than_five_items,
        test_missing_section_graceful_failure,
    ]

    for test in tests:
        test()


if __name__ == "__main__":  # pragma: no cover - CLI path
    try:
        run_all_tests()
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"Self-tests failed: {exc}\n")
        raise SystemExit(1)
    else:
        print("All self-tests passed.")
        raise SystemExit(0)

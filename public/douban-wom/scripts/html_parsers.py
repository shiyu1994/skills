#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTML parsing utilities for Douban "一周口碑榜" on the movie chart page.

Designed to be resilient to minor DOM changes.
"""
from __future__ import annotations
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

TARGET_H2_KEYWORD = "一周口碑榜"


def _norm_text(s: str) -> str:
    return (s or "").strip().replace("\xa0", " ")


def find_weekly_section(soup: BeautifulSoup) -> Optional[BeautifulSoup]:
    """Locate the UL list element that contains the weekly word-of-mouth ranking entries.

    Strategy:
    - Find the H2 whose text contains TARGET_H2_KEYWORD
    - Prefer the nearest UL with class "content" within the same parent section/container
    - Fallback: search globally for ULs with id=listCont2 or class=content near that H2
    """
    # 1) Find target h2
    h2_candidates = []
    for h2 in soup.find_all("h2"):
        txt = _norm_text(h2.get_text(" "))
        if TARGET_H2_KEYWORD in txt:
            h2_candidates.append(h2)
    if not h2_candidates:
        return None

    # Prefer the first occurrence
    h2 = h2_candidates[0]

    # 2) Try typical structure: <div class="movie_top" id="ranking"> then <h2>..</h2> then <ul class="content">
    # First look within the same parent container
    parent = h2.find_parent()
    if parent:
        ul = parent.find("ul", class_="content")
        if ul:
            return ul

    # 3) Check next siblings
    sib = h2
    for _ in range(5):  # limit traversal
        sib = sib.next_sibling
        if not sib:
            break
        if getattr(sib, "name", None) == "ul" and ("content" in (sib.get("class") or [])):
            return sib

    # 4) Global fallbacks
    # Some pages use id=listCont2 for the weekly WOM
    ul = soup.find("ul", id="listCont2")
    if ul:
        return ul

    # As last resort, return first UL.content on page
    ul = soup.find("ul", class_="content")
    return ul


def parse_week_label(soup: BeautifulSoup) -> Optional[str]:
    """Extract the week label text e.g., '11月28日 更新'.
    Looks for a <span> inside the H2 containing TARGET_H2_KEYWORD.
    """
    for h2 in soup.find_all("h2"):
        txt = _norm_text(h2.get_text(" "))
        if TARGET_H2_KEYWORD in txt:
            # Prefer span text if present
            span = h2.find("span")
            if span:
                return _norm_text(span.get_text(" "))
            # Otherwise, remove the keyword and return the rest
            cleaned = _norm_text(txt.replace(TARGET_H2_KEYWORD, "")).strip("· .")
            return cleaned or None
    return None


def parse_top_from_ul(ul: BeautifulSoup, limit: int = 5) -> List[Dict[str, str]]:
    """Parse ranking entries from the UL list.

    Each LI is expected to contain:
    - div.no (rank)
    - div.name > a (title + link)
    """
    results: List[Dict[str, str]] = []
    if not ul:
        return results

    for li in ul.find_all("li", recursive=False):
        no = None
        name = None
        href = None
        # rank
        no_div = li.find("div", class_="no")
        if no_div:
            no_txt = _norm_text(no_div.get_text(" "))
            if no_txt.isdigit():
                no = int(no_txt)
        # title + link
        name_div = li.find("div", class_="name")
        if name_div:
            a = name_div.find("a")
            if a:
                name = _norm_text(a.get_text(" "))
                href = a.get("href")
        if no is not None and name and href:
            results.append({"rank": no, "title": name, "url": href})
        if len(results) >= limit:
            break

    # If ranks missing, reassign as 1..N to be robust
    if results and any(r.get("rank") is None for r in results):
        for i, r in enumerate(results, start=1):
            r["rank"] = i
    return results


def parse_weekly_top(html: str, limit: int = 5) -> Dict[str, object]:
    """Parse the weekly WOM top list from raw HTML.

    Returns a dict: { 'week_label': str|None, 'entries': [ {rank, title, url}, ... ] }
    """
    soup = BeautifulSoup(html, "html.parser")
    ul = find_weekly_section(soup)
    entries = parse_top_from_ul(ul, limit=limit)
    label = parse_week_label(soup)
    return {"week_label": label, "entries": entries}

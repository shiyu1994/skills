#!/usr/bin/env python3
"""douban_wom.py

Fetch and parse Douban's weekly word-of-mouth movie ranking (一周口碑电影榜).

Design goals:
- Prefer Douban mobile rexxar JSON endpoints.
- Be tolerant to minor JSON shape changes.
- No user input required; sensible defaults.

Primary data source (as of writing):
  https://m.douban.com/rexxar/api/v2/subject_collection/movie_weekly_best/items

This module contains no Claude/Skill-specific dependencies; it is plain Python.
"""

from __future__ import annotations

import dataclasses
import datetime as _dt
import re
import time
from typing import Any, Dict, List, Optional, Tuple


try:
    import requests  # type: ignore
except Exception:  # pragma: no cover
    requests = None  # type: ignore


BASE = "https://m.douban.com"
API_BASE = f"{BASE}/rexxar/api/v2"
COLLECTION = "movie_weekly_best"

DEFAULT_HEADERS = {
    # Douban can be sensitive to UA/Referer.
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": f"{BASE}/subject_collection/{COLLECTION}",
    "Origin": BASE,
}


@dataclasses.dataclass
class MovieRank:
    rank: int
    title: str
    rating: Optional[float] = None
    good_rate: Optional[float] = None  # 0..1
    year: Optional[int] = None
    countries: List[str] = dataclasses.field(default_factory=list)
    genres: List[str] = dataclasses.field(default_factory=list)
    subject_id: Optional[str] = None
    subject_url: Optional[str] = None


@dataclasses.dataclass
class WeeklyTop5:
    week_label: str
    fetched_at: str
    source: str
    items: List[MovieRank]


class DoubanFetchError(RuntimeError):
    pass


def _now_iso() -> str:
    return _dt.datetime.now(tz=_dt.timezone.utc).astimezone().isoformat(timespec="seconds")


def _to_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        s = x.strip()
        if not s:
            return None
        try:
            return float(s)
        except Exception:
            return None
    return None


def _to_int(x: Any) -> Optional[int]:
    if x is None:
        return None
    if isinstance(x, bool):
        return None
    if isinstance(x, int):
        return x
    if isinstance(x, float):
        if x.is_integer():
            return int(x)
        return None
    if isinstance(x, str):
        s = x.strip()
        if not s:
            return None
        try:
            return int(s)
        except Exception:
            return None
    return None


def _norm_list(x: Any) -> List[str]:
    if x is None:
        return []
    if isinstance(x, list):
        return [str(i).strip() for i in x if str(i).strip()]
    if isinstance(x, str):
        # Sometimes comma/ slash separated.
        parts = re.split(r"[,/\uFF0C]", x)
        return [p.strip() for p in parts if p.strip()]
    return [str(x).strip()] if str(x).strip() else []


def _norm_space_list(s: str) -> List[str]:
    parts = re.split(r"\s+", s.strip())
    return [p for p in parts if p]


def _extract_subject_url(item: Dict[str, Any]) -> Optional[str]:
    # Many possible fields.
    for k in ("url", "share_url", "sharing_url"):
        v = item.get(k)
        if isinstance(v, str) and v.startswith("http"):
            return v
    # Sometimes nested.
    subj = item.get("subject")
    if isinstance(subj, dict):
        for k in ("url", "share_url", "sharing_url"):
            v = subj.get(k)
            if isinstance(v, str) and v.startswith("http"):
                return v
    return None


def _extract_subject_id(item: Dict[str, Any]) -> Optional[str]:
    for k in ("id", "subject_id"):
        v = item.get(k)
        if v is not None:
            return str(v)
    subj = item.get("subject")
    if isinstance(subj, dict) and subj.get("id") is not None:
        return str(subj.get("id"))
    # As a fallback, try to parse from URL.
    url = _extract_subject_url(item)
    if url:
        m = re.search(r"/subject/(\d+)", url)
        if m:
            return m.group(1)
    return None


def _parse_card_subtitle(card_subtitle: str) -> Tuple[Optional[int], List[str], List[str]]:
    """Parse fields from card_subtitle like:

      "2025 / 法国 / 剧情 喜剧 同性 / 导演... / 主演..."

    Returns (year, countries, genres).
    """

    if not card_subtitle or not isinstance(card_subtitle, str):
        return None, [], []

    parts = [p.strip() for p in card_subtitle.split("/")]
    parts = [p for p in parts if p]

    year = _to_int(parts[0]) if parts else None
    countries = _norm_space_list(parts[1]) if len(parts) >= 2 else []
    genres = _norm_space_list(parts[2]) if len(parts) >= 3 else []

    return year, countries, genres


def parse_weekly_items(payload: Dict[str, Any], top_n: int = 5) -> List[MovieRank]:
    """Parse a Douban rexxar subject_collection items payload into MovieRank list."""

    # Common keys seen across rexxar collections:
    items = None
    for k in ("subject_collection_items", "items", "subjects"):
        if isinstance(payload.get(k), list):
            items = payload.get(k)
            break

    # Sometimes nested.
    if items is None and isinstance(payload.get("data"), dict):
        d = payload["data"]
        for k in ("subject_collection_items", "items", "subjects"):
            if isinstance(d.get(k), list):
                items = d.get(k)
                break

    if not isinstance(items, list):
        raise DoubanFetchError("Unexpected payload shape: cannot find items list")

    parsed: List[MovieRank] = []
    for idx, raw in enumerate(items[:top_n]):
        if not isinstance(raw, dict):
            continue

        title = raw.get("title") or raw.get("name")
        if not title and isinstance(raw.get("subject"), dict):
            title = raw["subject"].get("title") or raw["subject"].get("name")
        title = str(title).strip() if title is not None else ""

        # Rank: explicit rank or list position.
        rank = _to_int(raw.get("rank")) or (idx + 1)

        rating = None
        if isinstance(raw.get("rating"), dict):
            rating = _to_float(raw["rating"].get("value"))
        if rating is None:
            rating = _to_float(raw.get("rating"))
        if rating is None and isinstance(raw.get("subject"), dict):
            sr = raw["subject"].get("rating")
            if isinstance(sr, dict):
                rating = _to_float(sr.get("value"))
            else:
                rating = _to_float(sr)

        # good_rate:
        good_rate = _to_float(raw.get("good_rate"))
        if good_rate is None and isinstance(raw.get("subject"), dict):
            good_rate = _to_float(raw["subject"].get("good_rate"))

        # Some rexxar payloads provide good_rating_stats as integer percent.
        if good_rate is None and raw.get("good_rating_stats") is not None:
            grs = _to_float(raw.get("good_rating_stats"))
            if grs is not None:
                good_rate = grs / 100.0

        # Some pages show good_rate as a percent string like "77%".
        if isinstance(raw.get("good_rate"), str) and raw.get("good_rate").strip().endswith("%"):
            try:
                good_rate = float(raw.get("good_rate").strip().rstrip("%")) / 100.0
            except Exception:
                pass

        year = _to_int(raw.get("year"))
        if year is None and isinstance(raw.get("subject"), dict):
            year = _to_int(raw["subject"].get("year"))

        countries = _norm_list(raw.get("countries"))
        if not countries and isinstance(raw.get("country"), str):
            countries = _norm_list(raw.get("country"))
        if not countries and isinstance(raw.get("subject"), dict):
            countries = _norm_list(raw["subject"].get("countries") or raw["subject"].get("country"))

        genres = _norm_list(raw.get("genres"))
        if not genres and isinstance(raw.get("genre"), str):
            genres = _norm_list(raw.get("genre"))
        if not genres and isinstance(raw.get("subject"), dict):
            genres = _norm_list(raw["subject"].get("genres") or raw["subject"].get("genre"))

        # A very common field on rank lists: card_subtitle.
        # Use it as a fallback for year/countries/genres.
        if (year is None or not countries or not genres) and isinstance(raw.get("card_subtitle"), str):
            y2, c2, g2 = _parse_card_subtitle(raw["card_subtitle"])
            year = year if year is not None else y2
            countries = countries or c2
            genres = genres or g2

        parsed.append(
            MovieRank(
                rank=int(rank) if rank else (idx + 1),
                title=title or f"(unknown-{idx+1})",
                rating=rating,
                good_rate=good_rate,
                year=year,
                countries=countries,
                genres=genres,
                subject_id=_extract_subject_id(raw),
                subject_url=_extract_subject_url(raw),
            )
        )

    if len(parsed) < top_n:
        raise DoubanFetchError(f"Parsed only {len(parsed)} items (<{top_n}). Payload shape may have changed.")

    # Ensure ranks 1..top_n even if server does not provide.
    parsed.sort(key=lambda x: x.rank)
    for i, it in enumerate(parsed, start=1):
        it.rank = i

    return parsed


def _guess_week_label(payload: Dict[str, Any]) -> str:
    """Best-effort week label from payload metadata."""
    sc = payload.get("subject_collection")
    if isinstance(sc, dict):
        # Prefer explicit title.
        title = sc.get("title") or sc.get("name")
        title = title.strip() if isinstance(title, str) else None

        updated_at = sc.get("updated_at") or sc.get("update_time")
        # updated_at can be an epoch number or a datetime string like "2026-03-06 16:30:02".
        upd_date: Optional[str] = None
        if isinstance(updated_at, (int, float)):
            dt = _dt.datetime.fromtimestamp(float(updated_at), tz=_dt.timezone.utc).astimezone()
            upd_date = dt.date().isoformat()
        elif isinstance(updated_at, str) and updated_at.strip():
            m = re.match(r"^(\d{4}-\d{2}-\d{2})", updated_at.strip())
            if m:
                upd_date = m.group(1)

        if title and upd_date:
            return f"{title} (updated_at={upd_date})"
        if title:
            return title
        if isinstance(sc.get("description"), str) and sc.get("description").strip():
            return sc.get("description").strip()

    # Sometimes top-level fields.
    for k in ("title", "name", "description"):
        v = payload.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()

    return "weekly"  # fallback


def http_get_json(url: str, params: Optional[Dict[str, Any]] = None, *, timeout: int = 20, retries: int = 3) -> Tuple[Dict[str, Any], str]:
    """GET JSON with basic retry/backoff. Returns (payload, final_url)."""
    if requests is None:
        raise DoubanFetchError("requests is not available in this environment")

    last_err: Optional[Exception] = None
    backoff = 1.0

    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, params=params or {}, headers=DEFAULT_HEADERS, timeout=timeout)
            if r.status_code in (403, 418):
                raise DoubanFetchError(f"HTTP {r.status_code} (blocked/forbidden)")
            r.raise_for_status()

            # Douban sometimes returns text/html on error.
            ctype = (r.headers.get("Content-Type") or "").lower()
            if "json" not in ctype:
                # Still try parse.
                try:
                    payload = r.json()
                except Exception as e:
                    raise DoubanFetchError(f"Non-JSON response Content-Type={ctype}") from e
            else:
                payload = r.json()

            if not isinstance(payload, dict):
                raise DoubanFetchError("JSON payload is not an object")

            return payload, r.url

        except Exception as e:
            last_err = e
            if attempt < retries:
                time.sleep(backoff)
                backoff *= 2
                continue
            break

    raise DoubanFetchError(f"Failed to fetch {url}: {last_err}")


def fetch_weekly_top5(*, date: Optional[str] = None) -> WeeklyTop5:
    """Fetch and parse weekly top-5. If date is provided, it is passed through as a best-effort hint."""
    url = f"{API_BASE}/subject_collection/{COLLECTION}/items"
    params: Dict[str, Any] = {"start": 0, "count": 10}
    if date:
        params["date"] = date

    payload, final_url = http_get_json(url, params=params)
    items = parse_weekly_items(payload, top_n=5)
    week_label = _guess_week_label(payload)

    return WeeklyTop5(week_label=week_label, fetched_at=_now_iso(), source=final_url, items=items)


def fetch_recent_weeks(max_weeks: int = 6) -> List[WeeklyTop5]:
    """Attempt to fetch multiple recent weeks.

    Douban may or may not support history for this rank list.
    Strategy:
    - Always fetch the latest (no date).
    - Then try stepping back by 7 days using ?date=YYYY-MM-DD.
    - Stop when results stop changing (same top-1 subject_id/title repeated).
    """

    latest = fetch_weekly_top5(date=None)
    results: List[WeeklyTop5] = [latest]

    # If the endpoint ignores the date param, older calls will match latest.
    today = _dt.date.today()

    def sig(w: WeeklyTop5) -> str:
        first = w.items[0]
        return f"{first.subject_id}:{first.title}".lower()

    latest_sig = sig(latest)

    for i in range(1, max_weeks):
        d = (today - _dt.timedelta(days=7 * i)).isoformat()
        try:
            wk = fetch_weekly_top5(date=d)
        except DoubanFetchError:
            break

        if sig(wk) == latest_sig:
            # Likely no history; stop.
            break

        # Deduplicate if signature repeats.
        if any(sig(prev) == sig(wk) for prev in results):
            break

        results.append(wk)

    return results


def to_jsonable(weeks: List[WeeklyTop5]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for w in weeks:
        out.append(
            {
                "week_label": w.week_label,
                "fetched_at": w.fetched_at,
                "source": w.source,
                "items": [dataclasses.asdict(it) for it in w.items],
            }
        )
    return out


def format_table(week: WeeklyTop5) -> str:
    rows = []
    rows.append(f"week_label: {week.week_label}")
    rows.append(f"source: {week.source}")
    rows.append("\nRank | Title | Rating | Good% | Year")
    rows.append("---: | --- | ---: | ---: | ---:")
    for it in week.items:
        good = None if it.good_rate is None else f"{it.good_rate*100:.0f}%"
        rating = "" if it.rating is None else f"{it.rating:.1f}"
        year = "" if it.year is None else str(it.year)
        rows.append(f"{it.rank} | {it.title} | {rating} | {good or ''} | {year}")
    return "\n".join(rows)

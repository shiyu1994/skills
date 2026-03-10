# Douban endpoints used by this skill

This skill targets Douban’s mobile web JSON ("rexxar") endpoints.

## Primary endpoint (current weekly list)

- Collection page:
  - https://m.douban.com/subject_collection/movie_weekly_best?type=rank&category=movie&rank_type=weekly

- JSON items endpoint (used by scripts):
  - https://m.douban.com/rexxar/api/v2/subject_collection/movie_weekly_best/items?start=0&count=10

## Notes

- Douban may block requests without a browser-like `User-Agent` and `Referer`.
- Public access may change; scripts implement retries and tolerate minor JSON shape differences.
- History for previous weeks may not be exposed via this endpoint; scripts attempt `?date=YYYY-MM-DD` as a best-effort hint.

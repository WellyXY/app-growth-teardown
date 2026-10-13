#!/usr/bin/env python3
"""Estimate which time zones the reviewers of one language (default English) live in, from the hour
their Google Play reviews were posted.

People mostly write reviews in their local afternoon/evening. We build a "typical day" posting curve
from languages that map to roughly one country (Brazilian Portuguese UTC-3, Indonesian UTC+7,
Vietnamese UTC+7), shift that curve to each candidate time zone, and fit the target language's UTC
hour histogram as a non-negative mix (NNLS). A bootstrap gives a range for each share.

Check the template first: the printed template should be low in the local early morning and peak in
the local evening. Results are time-zone regions, not countries (UTC+5.5 also covers Pakistan,
Bangladesh, Gulf). Never infer location from reviewer names or avatars.

Requires: google-play-scraper numpy scipy  (venv — see references/pitfalls.md)

Usage:
    play_reviews_timezone.py chat.sekai.app --since 2026-07-29
    play_reviews_timezone.py chat.sekai.app --since 2026-07-01 --lang en --json tz.json
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone

try:
    import numpy as np
    from google_play_scraper import Sort, reviews
    from scipy.optimize import nnls
except ImportError:
    sys.exit("Missing packages (google-play-scraper numpy scipy). See references/pitfalls.md for the venv setup.")

TEMPLATES = [("pt", "br", -3), ("id", "id", 7), ("vi", "vn", 7)]
REGIONS = {
    "US/Canada (UTC-6)": -6,
    "UK/Europe/Africa (UTC+1)": 1,
    "India/South Asia (UTC+5.5)": 5.5,
    "Philippines/SE Asia (UTC+8)": 8,
    "Australia (UTC+10)": 10,
}


def utc(dt):
    return datetime.fromtimestamp(dt.timestamp(), timezone.utc)


def fetch_hours(package, lang, country, since, max_pages=40):
    got, token = [], None
    for _ in range(max_pages):
        batch, token = reviews(package, lang=lang, country=country, sort=Sort.NEWEST, count=200,
                               continuation_token=token)
        got += batch
        if not batch or token is None or utc(batch[-1]["at"]) < since:
            break
        time.sleep(0.3)
    hours = [utc(r["at"]).hour for r in got if utc(r["at"]) >= since]
    return np.bincount(hours, minlength=24).astype(float), len(hours)


def to_local(hist_utc, offset):
    return np.array([hist_utc[(h - offset) % 24] for h in range(24)])


def expected_utc(template_local, offset):
    lo = int(np.floor(offset))
    frac = offset - lo
    a = np.array([template_local[(h + lo) % 24] for h in range(24)])
    b = np.array([template_local[(h + lo + 1) % 24] for h in range(24)])
    return (1 - frac) * a + frac * b


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("package")
    ap.add_argument("--since", required=True, help="YYYY-MM-DD (60-90 days of reviews works well)")
    ap.add_argument("--lang", default="en")
    ap.add_argument("--boot", type=int, default=500)
    ap.add_argument("--json")
    args = ap.parse_args()
    since = datetime.fromisoformat(args.since).replace(tzinfo=timezone.utc)

    template = np.zeros(24)
    for lang, country, off in TEMPLATES:
        hist, n = fetch_hours(args.package, lang, country, since)
        print(f"template {lang} (UTC{off:+}): {n} reviews")
        if n >= 50:
            template += to_local(hist, off) / n
    if template.sum() == 0:
        sys.exit("Not enough template reviews; widen --since.")
    template /= template.sum()
    print("template by local hour (%):", " ".join(f"{x * 100:.1f}" for x in template))

    target, n = fetch_hours(args.package, args.lang, "us", since)
    print(f"\ntarget {args.lang}: {n} reviews")
    print("target by UTC hour:", " ".join(str(int(x)) for x in target))
    if n < 200:
        print("Warning: fewer than 200 reviews; shares will be noisy.")

    A = np.column_stack([expected_utc(template, off) for off in REGIONS.values()])
    y = target / target.sum()
    w, _ = nnls(A, y)
    w = w / w.sum()
    fit = A @ w
    r2 = 1 - ((y - fit) ** 2).sum() / ((y - y.mean()) ** 2).sum()

    rng = np.random.default_rng(0)
    boots = []
    for _ in range(args.boot):
        s = rng.multinomial(int(n), y)
        bw, _ = nnls(A, s / s.sum())
        boots.append(bw / bw.sum())
    boots = np.array(boots)
    lo, hi = np.percentile(boots, 10, 0), np.percentile(boots, 90, 0)

    print(f"\nEstimated share of '{args.lang}' reviewers by time-zone region (fit R² = {r2:.2f}):")
    out = {}
    for (name, _), share, a, b in zip(REGIONS.items(), w, lo, hi):
        out[name] = {"share": round(float(share), 3), "p10": round(float(a), 3), "p90": round(float(b), 3)}
        print(f"  {name:30} {share * 100:4.0f}%   (range {a * 100:.0f}-{b * 100:.0f}%)")

    if args.json:
        with open(args.json, "w") as f:
            json.dump({"n": int(n), "r2": round(float(r2), 3), "shares": out,
                       "target_utc_hist": target.tolist(), "template_local": template.tolist()}, f, indent=1)
        print("wrote", args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())

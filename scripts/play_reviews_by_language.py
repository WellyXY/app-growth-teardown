#!/usr/bin/env python3
"""Count recent Google Play reviews per language, per month, to see where an app's users come from
and how that mix shifts over time.

Play reviews can only be filtered by language (the `country` parameter does not change results).
English mixes many countries; split it with play_reviews_timezone.py.

Requires: google-play-scraper  (pip install google-play-scraper, in a venv — see references/pitfalls.md)

Usage:
    play_reviews_by_language.py chat.sekai.app --since 2026-04-01
    play_reviews_by_language.py chat.sekai.app --since 2026-06-01 --langs en es pt id --json langs.json
"""
import argparse
import collections
import json
import sys
import time
from datetime import datetime, timedelta, timezone

try:
    from google_play_scraper import Sort, reviews
except ImportError:
    sys.exit("google-play-scraper is not installed. See references/pitfalls.md for the venv setup.")

DEFAULT_LANGS = [
    ("en", "us"), ("es", "mx"), ("pt", "br"), ("ru", "ru"), ("id", "id"), ("vi", "vn"),
    ("ar", "sa"), ("tr", "tr"), ("fr", "fr"), ("de", "de"), ("it", "it"), ("pl", "pl"),
    ("th", "th"), ("ms", "my"), ("fil", "ph"), ("hi", "in"), ("ja", "jp"), ("ko", "kr"),
    ("zh-TW", "tw"), ("nl", "nl"),
]
COUNTRY_FOR = dict(DEFAULT_LANGS)


def utc(dt):
    # google-play-scraper returns naive datetimes in the machine's local time zone
    return datetime.fromtimestamp(dt.timestamp(), timezone.utc)


def fetch_since(package, lang, country, since, page_size=200, max_pages=60, pause=0.3):
    got, token = [], None
    for _ in range(max_pages):
        batch, token = reviews(package, lang=lang, country=country, sort=Sort.NEWEST,
                               count=page_size, continuation_token=token)
        got += batch
        if not batch or token is None or utc(batch[-1]["at"]) < since:
            break
        time.sleep(pause)
    return [r for r in got if utc(r["at"]) >= since]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("package")
    ap.add_argument("--since", required=True, help="YYYY-MM-DD")
    ap.add_argument("--langs", nargs="+", help="language codes (default: 20 common languages)")
    ap.add_argument("--json")
    args = ap.parse_args()

    since = datetime.fromisoformat(args.since).replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    langs = [(l, COUNTRY_FOR.get(l, "us")) for l in args.langs] if args.langs else DEFAULT_LANGS

    result = {}
    for lang, country in langs:
        try:
            rs = fetch_since(args.package, lang, country, since)
        except Exception as e:
            print(f"{lang:6} ERROR {e}")
            continue
        months = collections.Counter(utc(r["at"]).strftime("%Y-%m") for r in rs)
        last30 = sum(1 for r in rs if utc(r["at"]) >= now - timedelta(days=30))
        result[lang] = {"total": len(rs), "last30": last30, "months": dict(sorted(months.items()))}
        print(f"{lang:6} total={len(rs):>6} last30={last30:>5} {dict(sorted(months.items()))}", flush=True)

    tot30 = sum(v["last30"] for v in result.values()) or 1
    print("\nLast-30-day share by language:")
    for lang, v in sorted(result.items(), key=lambda kv: -kv[1]["last30"]):
        if v["last30"]:
            print(f"  {lang:6} {v['last30'] / tot30 * 100:5.1f}%  ({v['last30']})")

    all_months = sorted({m for v in result.values() for m in v["months"]})
    print("\nMonthly counts:")
    print("  lang   " + " ".join(f"{m:>8}" for m in all_months))
    for lang, v in sorted(result.items(), key=lambda kv: -kv[1]["total"]):
        if v["total"] >= 20:
            print(f"  {lang:6} " + " ".join(f"{v['months'].get(m, 0):>8}" for m in all_months))
    print("\nNote: the newest month is partial. Only text reviews are counted (~20% of all ratings).")

    if args.json:
        with open(args.json, "w") as f:
            json.dump(result, f, indent=1)
        print("wrote", args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())

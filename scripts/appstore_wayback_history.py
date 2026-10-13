#!/usr/bin/env python3
"""Reconstruct an iOS app's rating-count history (one storefront, default US) from Wayback snapshots.

App Store URLs contain the app's name slug, which changes when the app is renamed, so pass every
slug the app has used (current + old names). Find old names from the Play title history
(play_wayback_history.py prints it), news, or the Wayback URL search.

Stdlib only.

Usage:
    appstore_wayback_history.py 6504506653 --slugs sekai-create-remix-play sekai-roleplay-your-own-story
    appstore_wayback_history.py 6504506653 --slugs my-app --country gb --since 2025-06 --json out.json
"""
import argparse
import gzip
import json
import re
import sys
import time
import urllib.request
from datetime import date, datetime

UA = "Mozilla/5.0 (app-growth-teardown research script)"


def http_get(url, timeout=90, retries=3):
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
            while raw[:2] == b"\x1f\x8b":
                raw = gzip.decompress(raw)
            return raw.decode("utf-8", errors="ignore")
        except Exception as e:
            last = e
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"GET failed: {url}: {last}")


def to_number(s):
    s = s.replace(",", "").strip()
    mult = 1
    if s[-1:] in "KkMm":
        mult = 1_000 if s[-1] in "Kk" else 1_000_000
        s = s[:-1]
    return int(float(s) * mult)


def snapshots(app_id, slug, country, since):
    base = f"apps.apple.com/{country}/app/{slug}/id{app_id}"
    url = (f"https://web.archive.org/cdx/search/cdx?url={base}&matchType=prefix&output=txt"
           "&fl=timestamp,original&filter=statuscode:200&collapse=timestamp:6")
    out = []
    for line in http_get(url).splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0][:6] >= since.replace("-", ""):
            # skip localized (?l=xx) and review-tab variants; they render differently
            if "?" in parts[1] and "mt=8" not in parts[1]:
                continue
            out.append(tuple(parts))
    return out


def parse(html):
    m = re.search(r"([\d.,]+[KM]?) Ratings", html)
    if m:
        return to_number(m.group(1))
    m = re.search(r'"(?:userRatingCount|ratingCount)"\s*:\s*"?(\d+)', html)
    return int(m.group(1)) if m else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("app_id")
    ap.add_argument("--slugs", nargs="+", required=True)
    ap.add_argument("--country", default="us")
    ap.add_argument("--since", default="2024-01")
    ap.add_argument("--current", type=int, help="today's rating count from the live page")
    ap.add_argument("--sleep", type=float, default=3.5)
    ap.add_argument("--json")
    args = ap.parse_args()

    snaps = []
    for slug in args.slugs:
        snaps += snapshots(args.app_id, slug, args.country, args.since)
        time.sleep(2)
    by_month = {}
    for ts, orig in sorted(snaps):
        by_month.setdefault(ts[:6], (ts, orig))
    if not by_month:
        print("No snapshots found. Check the slugs (the part of the URL before /id<ID>).")
        return 1

    points = []
    for ts, orig in [by_month[k] for k in sorted(by_month)]:
        try:
            n = parse(http_get(f"https://web.archive.org/web/{ts}id_/{orig}"))
        except RuntimeError:
            n = None
        d = datetime.strptime(ts[:8], "%Y%m%d").date()
        points.append({"date": d.isoformat(), "ratings": n, "url": orig})
        print(f"{d}  ratings={n}")
        time.sleep(args.sleep)
    if args.current:
        last = max((p["ratings"] for p in points if p["ratings"]), default=0)
        if args.current < last:
            print(f"--current {args.current} is below the latest snapshot ({last}); ignoring it.")
        else:
            points.append({"date": date.today().isoformat(), "ratings": args.current, "url": "(live)"})

    good = [p for p in points if p["ratings"]]
    print(f"\nRatings added per 30 days ({args.country.upper()} storefront):")
    periods = []
    for a, b in zip(good, good[1:]):
        days = (date.fromisoformat(b["date"]) - date.fromisoformat(a["date"])).days
        if days <= 0:
            continue
        per30 = (b["ratings"] - a["ratings"]) / days * 30
        periods.append({"from": a["date"], "to": b["date"], "ratings_per_30d": round(per30)})
        print(f"  {a['date']} -> {b['date']} ({days:>3}d): {per30:>7.0f}/30d")

    if args.json:
        with open(args.json, "w") as f:
            json.dump({"snapshots": points, "periods": periods}, f, indent=1)
        print("wrote", args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())

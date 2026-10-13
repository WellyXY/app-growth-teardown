#!/usr/bin/env python3
"""Reconstruct a Google Play app's review-count history from Wayback Machine snapshots and turn it
into a rough monthly-download estimate.

For each month that Wayback archived the Play page, read: listing title, "<N> reviews" header count,
and the download bucket (e.g. "1M+"). Then compute reviews added per 30 days between snapshots and
multiply by an installs-per-review ratio (default 140-160; calibrate per app with download-bucket
jumps or AndroidRank milestones, see references/methods.md section 1).

Stdlib only. Wayback rate-limits, so this sleeps between requests (~1 minute for a year of data).

Usage:
    play_wayback_history.py chat.sekai.app
    play_wayback_history.py chat.sekai.app --since 2025-01 --ratio 120 180 --current 55000 --json out.json
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
            if raw[:2] == b"\x1f\x8b":
                raw = gzip.decompress(raw)
            # some archived bodies are double-gzipped
            if raw[:2] == b"\x1f\x8b":
                raw = gzip.decompress(raw)
            return raw.decode("utf-8", errors="ignore")
        except Exception as e:  # network hiccups / 429
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


def monthly_snapshots(package, since):
    url = (
        "https://web.archive.org/cdx/search/cdx?url=play.google.com/store/apps/details%3Fid%3D"
        f"{package}&matchType=prefix&output=txt&fl=timestamp,original&filter=statuscode:200"
        "&collapse=timestamp:6"
    )
    rows = []
    for line in http_get(url).splitlines():
        parts = line.split()
        if len(parts) != 2:
            continue
        ts, orig = parts
        if ts[:6] < since.replace("-", ""):
            continue
        # prefer plain listing URLs (skip share/campaign variants when the month already has one)
        rows.append((ts, orig))
    by_month = {}
    for ts, orig in rows:
        m = ts[:6]
        plain = orig.endswith(f"id={package}")
        if m not in by_month or (plain and not by_month[m][1].endswith(f"id={package}")):
            by_month[m] = (ts, orig)
    return [by_month[k] for k in sorted(by_month)]


def parse_listing(html):
    title = re.search(r"<title[^>]*>([^<]*)", html)
    reviews = re.search(r"([\d.,]+[KM]?) reviews", html)
    bucket = re.search(r">(\d[\d.,]*[KMB]?\+)<", html)
    return {
        "title": title.group(1).replace(" - Apps on Google Play", "").strip() if title else None,
        "reviews": to_number(reviews.group(1)) if reviews else None,
        "bucket": bucket.group(1) if bucket else None,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("package")
    ap.add_argument("--since", default="2024-01", help="YYYY-MM, earliest snapshot month")
    ap.add_argument("--ratio", nargs=2, type=float, default=[140, 160], metavar=("LOW", "HIGH"),
                    help="installs per review (low high)")
    ap.add_argument("--current", type=int, help="today's review count from the live page, appended as a final point")
    ap.add_argument("--sleep", type=float, default=3.5)
    ap.add_argument("--json", help="write raw results to this file")
    args = ap.parse_args()

    snaps = monthly_snapshots(args.package, args.since)
    if not snaps:
        print("No Wayback snapshots found for", args.package)
        return 1
    print(f"{len(snaps)} monthly snapshots\n")
    points = []
    for ts, orig in snaps:
        try:
            info = parse_listing(http_get(f"https://web.archive.org/web/{ts}id_/{orig}"))
        except RuntimeError as e:
            info = {"title": None, "reviews": None, "bucket": None, "error": str(e)}
        d = datetime.strptime(ts[:8], "%Y%m%d").date()
        points.append({"date": d.isoformat(), **info})
        print(f"{d}  reviews={info['reviews']!s:>8}  downloads={info['bucket']!s:>6}  title={info['title']}")
        time.sleep(args.sleep)

    if args.current:
        last = max((p["reviews"] for p in points if p.get("reviews")), default=0)
        if args.current < last:
            print(f"\n--current {args.current} is below the latest snapshot ({last}); ignoring it.")
        else:
            points.append({"date": date.today().isoformat(), "title": None, "reviews": args.current, "bucket": None})

    good = [p for p in points if p.get("reviews")]
    lo, hi = args.ratio
    print(f"\nReview velocity and estimated monthly downloads (ratio {lo:g}-{hi:g} installs/review):")
    periods = []
    for a, b in zip(good, good[1:]):
        days = (date.fromisoformat(b["date"]) - date.fromisoformat(a["date"])).days
        if days <= 0:
            continue
        per30 = (b["reviews"] - a["reviews"]) / days * 30
        row = {"from": a["date"], "to": b["date"], "days": days, "reviews_per_30d": round(per30),
               "downloads_low": round(per30 * lo), "downloads_high": round(per30 * hi)}
        periods.append(row)
        print(f"  {a['date']} -> {b['date']} ({days:>3}d): +{b['reviews'] - a['reviews']:>7}  "
              f"{per30:>8.0f}/30d  ~{per30 * lo / 1e4:6.1f}-{per30 * hi / 1e4:6.1f} 萬/月")

    titles = []
    for p in points:
        if p.get("title") and (not titles or titles[-1][1] != p["title"]):
            titles.append((p["date"], p["title"]))
    print("\nListing title changes:")
    for d, t in titles:
        print(f"  {d}  {t}")

    if args.json:
        with open(args.json, "w") as f:
            json.dump({"snapshots": points, "periods": periods, "titles": titles}, f, ensure_ascii=False, indent=1)
        print("\nwrote", args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())

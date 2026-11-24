#!/usr/bin/env python3
"""Measure how many views a set of YouTube (ad) videos gains per day.

Cumulative views grouped by publish month badly misstate current ad delivery: an old evergreen ad can
still be gaining hundreds of thousands of views a day. Take two snapshots ~24h apart and diff them.
See references/web-product.md section 4.

Usage:
    youtube_views_delta.py snap ids.txt snap1.json          # ids.txt: one 11-char video id per line
    # ...about a day later...
    youtube_views_delta.py snap ids.txt snap2.json
    youtube_views_delta.py diff snap1.json snap2.json --own "Brand - Ads" "Brand" --cpv 0.005 0.03

--own keeps only videos whose channel name starts with one of the given prefixes (drop KOL videos).
--cpv prints a cost range at low/high cost per view. Stdlib only.
"""
import argparse
import json
import re
import sys
import time
import urllib.request

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0 Safari/537.36")


def read(vid):
    req = urllib.request.Request("https://www.youtube.com/watch?v=" + vid,
                                 headers={"User-Agent": UA, "Accept-Language": "en"})
    with urllib.request.urlopen(req, timeout=30) as r:
        h = r.read().decode("utf-8", errors="ignore")

    def g(p):
        m = re.search(p, h)
        return m.group(1) if m else None

    v, n, title, author = (g(r'"viewCount":"(\d+)"'), g(r'"lengthSeconds":"(\d+)"'),
                           g(r'"title":"((?:[^"\\]|\\.)*)","lengthSeconds"'), g(r'"author":"((?:[^"\\]|\\.)*)"'))
    return {"id": vid, "views": int(v) if v else None, "len": int(n) if n else None,
            "date": g(r'"publishDate":"([^"]{10})'), "unlisted": g(r'"isUnlisted":(true|false)'),
            "title": json.loads('"%s"' % title) if title else None,
            "author": json.loads('"%s"' % author) if author else None, "t": time.time()}


def snap(a):
    rows = []
    for vid in open(a.ids).read().split():
        try:
            rows.append(read(vid))
        except Exception as e:  # network error / removed video
            rows.append({"id": vid, "views": None, "t": time.time(), "err": str(e)[:80]})
        time.sleep(a.pause)
    json.dump(rows, open(a.out, "w"), ensure_ascii=False, indent=1)
    ok = [r for r in rows if r["views"] is not None]
    print(f"{len(ok)}/{len(rows)} readable, {sum(r['views'] for r in ok):,} cumulative views -> {a.out}")


def diff(a):
    old = {r["id"]: r for r in json.load(open(a.a))}
    rows = []
    for r in json.load(open(a.b)):
        o = old.get(r["id"])
        if not o or o["views"] is None or r["views"] is None:
            continue
        if a.own and not (r.get("author") or "").startswith(tuple(a.own)):
            continue
        rows.append(dict(r, gain=r["views"] - o["views"], hours=(r["t"] - o["t"]) / 3600))
    if not rows or min(r["hours"] for r in rows) <= 0:
        sys.exit("no comparable videos (check ids, --own, and that the first file is the older snapshot)")
    total = sum(r["gain"] for r in rows)
    day = sum(r["gain"] * 24 / r["hours"] for r in rows)
    top = sorted(rows, key=lambda r: -r["gain"])
    hrs = sum(r["hours"] for r in rows) / len(rows)
    share = f"{100 * sum(r['gain'] for r in top[:5]) / total:.0f}%" if total else "n/a"
    print(f"{len(rows)} videos, +{total:,} views in {hrs:.1f}h = {day / 1e6:.2f}M/day "
          f"({day * 30 / 1e6:.0f}M per 30 days IF this day is typical); top 5 = {share} of the gain")
    if hrs < 12:
        print("WARNING: gap under 12h; counters update in bursts, wait longer")
    if a.cpv:
        print(f"cost at ${a.cpv[0]}-{a.cpv[1]} per view: ${day * 30 * a.cpv[0]:,.0f} - ${day * 30 * a.cpv[1]:,.0f} per 30 days")
    print("unreadable videos are NOT counted; some gained views are organic")
    for r in top[:a.top]:
        print(f"{r['gain']:>10,} {r['views']:>12,} {r['date']} {r['len']}s {r['id']} {(r['title'] or '')[:70]}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(required=True)
    s = sub.add_parser("snap")
    s.add_argument("ids")
    s.add_argument("out")
    s.add_argument("--pause", type=float, default=1.0)
    s.set_defaults(fn=snap)
    d = sub.add_parser("diff")
    d.add_argument("a")
    d.add_argument("b")
    d.add_argument("--own", nargs="*", default=[])
    d.add_argument("--cpv", nargs=2, type=float)
    d.add_argument("--top", type=int, default=15)
    d.set_defaults(fn=diff)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()

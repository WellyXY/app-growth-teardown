#!/usr/bin/env python3
"""Find which TikTok videos (official account + creators) have been run as TikTok ads.

TikTok's ad library only covers the EU/UK and blocks scripted search; Creative Center Top Ads needs a
login. But every public video page embeds an `itemStruct` JSON with:
    isAd             true -> the video has been paid-promoted (Spark Ads / Promote)
    isCommerce       commercial / branded-content flag
    locationCreated  country the post was made from (e.g. "US")
Scanning the official account plus hashtag creators gives a public, US-inclusive view of TikTok ad use.
See references/methods.md section 7b for how to read the result.

Plain HTTP works where the in-browser fetch gets rate-limited (and later "Access Denied"), so run this
from the shell. Stdlib only.

Input: a JSON list of [user, video_id] pairs, e.g. exported from tiktok_profile_collect.js:
    JSON.stringify([...__tt.values()].map(v => [v.user, v.id]))

Usage:
    tiktok_ad_flags.py pairs.json
    tiktok_ad_flags.py pairs.json --exclude someuser otheruser --json adscan.json --pause 2
"""
import argparse
import json
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0 Safari/537.36")


def fetch(user, vid):
    req = urllib.request.Request(f"https://www.tiktok.com/@{user}/video/{vid}",
                                 headers={"User-Agent": UA, "Accept-Language": "en-US"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="ignore")


def parse(user, vid, html):
    k = html.find('"itemStruct"')
    s = html[k:k + 80000] if k >= 0 else ""

    def field(key):
        m = re.search(r'"%s":("[^"]{0,20}"|\w+)' % key, s)
        return m.group(1).strip('"') if m else "NA"

    def num(key):
        m = re.search(r'"%s":(\d+)' % key, s)
        return int(m.group(1)) if m else 0

    fol = re.search(r'"followerCount":(\d+)', html)
    desc = re.search(r'"desc":"([^"]{0,100})', s)
    return {
        "user": user, "id": vid,
        "date": datetime.fromtimestamp(int(vid) >> 32, timezone.utc).strftime("%Y-%m-%d"),
        "isAd": field("isAd"), "isCommerce": field("isCommerce"), "loc": field("locationCreated"),
        "views": num("playCount"), "likes": num("diggCount"),
        "followers": int(fol.group(1)) if fol else 0,
        "desc": desc.group(1) if desc else "",
    }


def like_rate(rows):
    v = sum(r["views"] for r in rows)
    return round(100 * sum(r["likes"] for r in rows) / v, 1) if v else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pairs", help="JSON file: [[user, video_id], ...]")
    ap.add_argument("--exclude", nargs="*", default=[], help="users to skip (unrelated hashtag noise)")
    ap.add_argument("--pause", type=float, default=2.0, help="seconds between requests")
    ap.add_argument("--json", help="write per-video rows here")
    a = ap.parse_args()

    pairs = [p for p in json.load(open(a.pairs)) if p[0] not in set(a.exclude)]
    rows = []
    for user, vid in pairs:
        try:
            rows.append(parse(user, vid, fetch(user, vid)))
        except Exception as e:  # network error / removed video
            rows.append({"user": user, "id": vid, "isAd": "ERR", "err": str(e)[:80]})
        r = rows[-1]
        print(f"{user:24} {r.get('date', ''):10} isAd={r['isAd']:5} views={r.get('views', '')}", file=sys.stderr)
        time.sleep(a.pause)

    ok = [r for r in rows if r["isAd"] in ("true", "false")]
    na = [r for r in rows if r["isAd"] not in ("true", "false")]
    print(f"\nscanned {len(ok)} ok, {len(na)} without data (rate-limited/removed — rerun later)")
    for label, grp in (("official+creators", ok),):
        ads = [r for r in grp if r["isAd"] == "true"]
        print(f"{label}: {len(ads)}/{len(grp)} flagged isAd")
        print(f"  pooled like rate: ads {like_rate(ads)}%  vs non-ads {like_rate([r for r in grp if r['isAd'] == 'false'])}%")

    by_month = {}
    for r in ok:
        b = by_month.setdefault(r["date"][:7], [0, 0])
        b[0] += 1
        b[1] += r["isAd"] == "true"
    print("\nmonth     videos  isAd")
    for m in sorted(by_month):
        print(f"{m}  {by_month[m][0]:6}  {by_month[m][1]:4}")

    print("\nflagged videos:")
    for r in sorted(ok, key=lambda r: r["date"]):
        if r["isAd"] == "true":
            lr = round(100 * r["likes"] / r["views"], 1) if r["views"] else None
            print(f"  {r['date']}  @{r['user']:22} views={r['views']:>10,}  like%={lr}  followers={r['followers']:,}")

    locs = {}
    for r in ok:
        locs[r["loc"]] = locs.get(r["loc"], 0) + 1
    print("\npost country (locationCreated):", dict(sorted(locs.items(), key=lambda x: -x[1])))

    if a.json:
        json.dump(rows, open(a.json, "w"), ensure_ascii=False, indent=1)
        print(f"wrote {a.json}")


if __name__ == "__main__":
    main()

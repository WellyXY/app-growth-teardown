#!/usr/bin/env python3
"""Decode TikTok video IDs into their UTC posting time.

TikTok video IDs carry the Unix timestamp in their upper 32 bits.

Usage:
    tiktok_id_to_date.py 7667887685398301973 [more ids...]
    tiktok_id_to_date.py https://www.tiktok.com/@user/video/7667887685398301973
"""
import re
import sys
from datetime import datetime, timezone


def id_to_utc(video_id: str) -> datetime:
    return datetime.fromtimestamp(int(video_id) >> 32, timezone.utc)


def main(argv):
    if not argv:
        print(__doc__.strip())
        return 1
    for arg in argv:
        m = re.search(r"(\d{15,})", arg)
        if not m:
            print(f"{arg}\t(not a video id)")
            continue
        vid = m.group(1)
        print(f"{vid}\t{id_to_utc(vid):%Y-%m-%d %H:%M} UTC")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

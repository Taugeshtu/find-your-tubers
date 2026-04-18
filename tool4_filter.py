#!/usr/bin/env python3
"""tool4_filter.py — Filter and rank channels for outreach.

Usage:
    python tool4_filter.py --profiles profiles.json --min-terms 2 --min-views 5000 --max-views 200000 --csv filtered.csv
"""

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path


def median_views(videos: list[dict]) -> float | None:
    counts = [v["views"] for v in videos if v.get("views") is not None]
    return statistics.median(counts) if counts else None


def last_post_date(videos: list[dict]) -> str:
    dates = [v["published_at"] for v in videos if v.get("published_at")]
    return max(dates) if dates else ""


def main():
    parser = argparse.ArgumentParser(description="Filter and rank channels for outreach")
    parser.add_argument("--profiles", default="profiles.json")
    parser.add_argument("--min-terms", type=int, default=2, help="Min seed terms matched")
    parser.add_argument("--min-views", type=int, default=5000, help="Min median views on recent videos")
    parser.add_argument("--max-views", type=int, default=200000, help="Max median views on recent videos")
    parser.add_argument("--csv", default=None, help="Optional CSV export path")
    args = parser.parse_args()

    channels: dict[str, dict] = json.loads(Path(args.profiles).read_text())

    rows = []
    for cid, ch in channels.items():
        videos = ch.get("recent_videos", [])
        med = median_views(videos)
        terms_count = len(ch.get("search_terms", []))
        last_post = last_post_date(videos)

        if terms_count < args.min_terms:
            continue
        if med is None or med < args.min_views or med > args.max_views:
            continue

        rows.append({
            "channel_name": ch["channel_name"],
            "channel_url": ch["channel_url"],
            "subscribers": ch.get("subscribers", 0),
            "seed_terms_matched": terms_count,
            "seed_terms": ", ".join(ch.get("search_terms", [])),
            "median_views": int(med),
            "last_post": last_post,
            "about": (ch.get("about", "") or "")[:120],
        })

    rows.sort(key=lambda r: (-r["seed_terms_matched"], -r["median_views"]))

    # Print table to stdout
    col_widths = {"channel_name": 28, "subscribers": 8, "seed_terms_matched": 6, "median_views": 10, "last_post": 12}
    header = f"{'Channel':<28} {'Subs':>8} {'Terms':>6} {'Med Views':>10} {'Last Post':<12}  URL"
    print(header)
    print("-" * 90)
    for r in rows:
        print(
            f"{r['channel_name'][:28]:<28} "
            f"{r['subscribers']:>8,} "
            f"{r['seed_terms_matched']:>6} "
            f"{r['median_views']:>10,} "
            f"{r['last_post']:<12}  "
            f"{r['channel_url']}"
        )

    print(f"\n{len(rows)} channels pass filters")

    if args.csv:
        out_path = Path(args.csv)
        with out_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
            writer.writeheader()
            writer.writerows(rows)
        print(f"CSV → {out_path}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""tool2_aggregate.py — Deduplicate and merge tool1 output into channels.json.

Usage:
    python tool2_aggregate.py --input output/ --out channels.json
"""

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Aggregate tool1 outputs into a channel index")
    parser.add_argument("--input", default="output/", help="Folder containing tool1 JSON files")
    parser.add_argument("--out", default="channels.json", help="Output file")
    args = parser.parse_args()

    in_dir = Path(args.input)
    files = sorted(in_dir.glob("*.json"))
    if not files:
        raise SystemExit(f"No JSON files found in {in_dir}")

    channels: dict[str, dict] = {}

    for f in files:
        hits = json.loads(f.read_text())
        for hit in hits:
            cid = hit["channel_id"]
            if cid not in channels:
                channels[cid] = {
                    "channel_id": cid,
                    "channel_name": hit["channel_name"],
                    "channel_url": hit["channel_url"],
                    "search_terms": [],
                    "source_files": [],
                    "videos": [],
                }

            entry = channels[cid]

            if hit["search_term"] not in entry["search_terms"]:
                entry["search_terms"].append(hit["search_term"])

            fname = f.name
            if fname not in entry["source_files"]:
                entry["source_files"].append(fname)

            if hit["video_id"] and not any(v["video_id"] == hit["video_id"] for v in entry["videos"]):
                entry["videos"].append({
                    "video_id": hit["video_id"],
                    "video_title": hit["video_title"],
                    "video_views": hit["video_views"],
                    "search_term": hit["search_term"],
                })

    out_path = Path(args.out)
    out_path.write_text(json.dumps(channels, indent=2, ensure_ascii=False))
    print(f"{len(channels)} unique channels → {out_path}")


if __name__ == "__main__":
    main()

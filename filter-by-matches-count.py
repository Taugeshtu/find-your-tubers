#!/usr/bin/env python3
"""filter-by-matches-count.py — Filter channels by how many search terms they matched.

Usage:
    python filter-by-matches-count.py --input channels.json --min-terms 3 --out filtered_channels.json
"""

import argparse
import json
import csv
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Filter channels based on search term match count")
    parser.add_argument("--input", default="channels.json", help="Path to channels.json (tool2 output)")
    parser.add_argument("--min-terms", type=int, default=1, help="Minimum number of search terms matched")
    parser.add_argument("--out", help="Output JSON file path (optional)")
    parser.add_argument("--csv", help="Output CSV file path (optional)")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: {args.input} not found.")
        return

    channels = json.loads(input_path.read_text())
    
    filtered = {}
    for cid, ch in channels.items():
        terms_count = len(ch.get("search_terms", []))
        if terms_count >= args.min_terms:
            filtered[cid] = ch

    # Sort results by match count descending
    sorted_items = sorted(
        filtered.items(), 
        key=lambda x: len(x[1].get("search_terms", [])), 
        reverse=True
    )

    # Print summary table to stdout
    print(f"{'Channel Name':<40} {'Terms':<6} {'URL'}")
    print("-" * 80)
    for cid, ch in sorted_items:
        terms_count = len(ch.get("search_terms", []))
        print(f"{ch['channel_name'][:40]:<40} {terms_count:<6} {ch['channel_url']}")

    print(f"\n{len(filtered)} channels matched {args.min_terms}+ terms (out of {len(channels)} total)")

    if args.out:
        out_path = Path(args.out)
        out_path.write_text(json.dumps(filtered, indent=2, ensure_ascii=False))
        print(f"JSON saved to {args.out}")

    if args.csv:
        csv_path = Path(args.csv)
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            if filtered:
                # Use a subset of fields for the CSV
                fieldnames = ["channel_id", "channel_name", "channel_url", "terms_count", "search_terms"]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for cid, ch in sorted_items:
                    writer.writerow({
                        "channel_id": cid,
                        "channel_name": ch["channel_name"],
                        "channel_url": ch["channel_url"],
                        "terms_count": len(ch.get("search_terms", [])),
                        "search_terms": ", ".join(ch.get("search_terms", []))
                    })
        print(f"CSV saved to {args.csv}")

if __name__ == "__main__":
    main()

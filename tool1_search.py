#!/usr/bin/env python3
"""tool1_search.py — Search YouTube for terms, collect channel hits.

Usage:
    python tool1_search.py --terms search_terms.txt --results 200 --output output/
"""

import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path


def load_api_key() -> str:
    key_path = Path(__file__).parent / "api.key"
    key = key_path.read_text().strip()
    if not key or key.startswith("YOUR_"):
        raise SystemExit("Put your YouTube Data API v3 key in api.key")
    return key


def sanitize_filename(term: str) -> str:
    return re.sub(r"[^\w\-]", "_", term)[:60]


def timestamp_prefix() -> str:
    return datetime.now().strftime("%Y%m%d-%H.%M")


def search_term(youtube, term: str, max_results: int) -> list[dict]:
    hits = []
    page_token = None
    fetched = 0

    while fetched < max_results:
        batch = min(50, max_results - fetched)
        params = {
            "part": "snippet",
            "q": term,
            "type": "video",
            "maxResults": batch,
        }
        if page_token:
            params["pageToken"] = page_token

        response = youtube.search().list(**params).execute()

        for item in response.get("items", []):
            snippet = item["snippet"]
            hits.append({
                "channel_id": snippet["channelId"],
                "channel_name": snippet["channelTitle"],
                "channel_url": f"https://www.youtube.com/channel/{snippet['channelId']}",
                "search_term": term,
                "video_id": item["id"].get("videoId", ""),
                "video_title": snippet["title"],
                "video_views": None,  # populated in a follow-up videos.list call
            })

        fetched += len(response.get("items", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return hits


def enrich_with_views(youtube, hits: list[dict]) -> list[dict]:
    """Batch-fetch view counts for all video IDs in hits."""
    video_ids = [h["video_id"] for h in hits if h["video_id"]]
    views_map = {}

    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i+50]
        response = youtube.videos().list(
            part="statistics",
            id=",".join(batch),
        ).execute()
        for item in response.get("items", []):
            views_map[item["id"]] = int(item["statistics"].get("viewCount", 0))

    for h in hits:
        h["video_views"] = views_map.get(h["video_id"])

    return hits


def main():
    parser = argparse.ArgumentParser(description="Search YouTube, collect channel hits")
    parser.add_argument("--terms", required=True, help="Path to search terms file (one per line)")
    parser.add_argument("--results", type=int, default=200, help="Max results per search term")
    parser.add_argument("--output", default="output/", help="Output folder")
    args = parser.parse_args()

    from googleapiclient.discovery import build  # type: ignore
    api_key = load_api_key()
    youtube = build("youtube", "v3", developerKey=api_key)

    terms = [line.strip() for line in Path(args.terms).read_text().splitlines() if line.strip()]
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    prefix = timestamp_prefix()

    for term in terms:
        print(f"Searching: {term!r}")
        hits = search_term(youtube, term, args.results)
        hits = enrich_with_views(youtube, hits)

        filename = out_dir / f"{prefix}-{sanitize_filename(term)}.json"
        filename.write_text(json.dumps(hits, indent=2, ensure_ascii=False))
        print(f"  → {len(hits)} hits → {filename}")


if __name__ == "__main__":
    main()

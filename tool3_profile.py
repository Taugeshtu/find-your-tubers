#!/usr/bin/env python3
"""tool3_profile.py — Enrich channels with subscriber count, about, and recent video activity.

Usage:
    python tool3_profile.py --channels channels.json --videos 100 --out profiles.json
"""

import argparse
import json
import time
from pathlib import Path


def load_api_key() -> str:
    key_path = Path(__file__).parent / "api.key"
    key = key_path.read_text().strip()
    if not key or key.startswith("YOUR_"):
        raise SystemExit("Put your YouTube Data API v3 key in api.key")
    return key


def fetch_channel_profiles(youtube, channel_ids: list[str]) -> dict[str, dict]:
    profiles = {}
    for i in range(0, len(channel_ids), 50):
        batch = channel_ids[i:i+50]
        response = youtube.channels().list(
            part="snippet,statistics",
            id=",".join(batch),
        ).execute()
        for item in response.get("items", []):
            cid = item["id"]
            snippet = item["snippet"]
            stats = item.get("statistics", {})
            profiles[cid] = {
                "subscribers": int(stats.get("subscriberCount", 0)),
                "created_at": snippet.get("publishedAt", "")[:10],
                "about": snippet.get("description", "").strip(),
            }
    return profiles


def fetch_recent_videos(youtube, channel_id: str, max_videos: int) -> list[dict]:
    videos = []
    page_token = None

    # First: get upload playlist ID for the channel
    resp = youtube.channels().list(part="contentDetails", id=channel_id).execute()
    items = resp.get("items", [])
    if not items:
        return videos
    uploads_playlist = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

    # Then: page through the playlist
    while len(videos) < max_videos:
        batch = min(50, max_videos - len(videos))
        params = {
            "part": "snippet",
            "playlistId": uploads_playlist,
            "maxResults": batch,
        }
        if page_token:
            params["pageToken"] = page_token

        resp = youtube.playlistItems().list(**params).execute()

        video_ids = []
        stubs = []
        for item in resp.get("items", []):
            snippet = item["snippet"]
            vid_id = snippet.get("resourceId", {}).get("videoId", "")
            if vid_id:
                video_ids.append(vid_id)
                stubs.append({
                    "video_id": vid_id,
                    "title": snippet.get("title", ""),
                    "published_at": snippet.get("publishedAt", "")[:10],
                })

        # Enrich with view counts
        if video_ids:
            stats_resp = youtube.videos().list(
                part="statistics",
                id=",".join(video_ids),
            ).execute()
            views_map = {
                item["id"]: int(item["statistics"].get("viewCount", 0))
                for item in stats_resp.get("items", [])
            }
            for stub in stubs:
                stub["views"] = views_map.get(stub["video_id"], 0)
            videos.extend(stubs)

        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    return videos


def main():
    parser = argparse.ArgumentParser(description="Profile channels: subscribers, about, recent videos")
    parser.add_argument("--channels", default="channels.json", help="Path to tool2 output")
    parser.add_argument("--videos", type=int, default=100, help="Recent videos to pull per channel")
    parser.add_argument("--out", default="profiles.json", help="Output file")
    args = parser.parse_args()

    from googleapiclient.discovery import build  # type: ignore
    api_key = load_api_key()
    youtube = build("youtube", "v3", developerKey=api_key)

    channels: dict[str, dict] = json.loads(Path(args.channels).read_text())
    channel_ids = list(channels.keys())

    print(f"Fetching profiles for {len(channel_ids)} channels...")
    profiles = fetch_channel_profiles(youtube, channel_ids)
    for cid, profile in profiles.items():
        channels[cid].update(profile)

    print(f"Fetching recent videos ({args.videos} per channel)...")
    for i, cid in enumerate(channel_ids):
        print(f"  [{i+1}/{len(channel_ids)}] {channels[cid]['channel_name']}")
        try:
            videos = fetch_recent_videos(youtube, cid, args.videos)
            channels[cid]["recent_videos"] = videos
        except Exception as e:
            print(f"    ERROR: {e}")
            channels[cid]["recent_videos"] = []
        time.sleep(0.1)  # light rate limiting

    out_path = Path(args.out)
    out_path.write_text(json.dumps(channels, indent=2, ensure_ascii=False))
    print(f"Done → {out_path}")


if __name__ == "__main__":
    main()

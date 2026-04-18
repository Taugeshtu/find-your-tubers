# TubeScraper

Find YouTube channels that cover games like yours — filter by consistency, viewership, and topic overlap. Built for indie game devs doing outreach.

## Setup

1. Get a YouTube Data API v3 key from [Google Cloud Console](https://console.cloud.google.com/) (free tier: 10,000 units/day)
2. Paste the key into `api.key` (one line, no quotes)
3. `pip install google-api-python-client`

## The Pipeline

```
search_terms.txt
      │
      ▼
tool1_search.py   →   output/YYYYMMDD-HH.MM-<term>.json   (one file per search term per run)
      │
      ▼
tool2_aggregate.py  →  channels.json                       (deduplicated, with provenance)
      │
      ▼
tool3_profile.py    →  profiles.json                       (channel stats + recent video activity)
      │
      ▼
tool4_filter.py     →  (stdout / filtered.csv)             (ranked shortlist for outreach)
```

---

## tool1_search.py — Search → Channel hits

Reads a text file of search terms (one per line, verbatim) and queries YouTube for each. Saves one JSON per search term per run. Re-running is safe — results accumulate in the output folder.

```bash
python tool1_search.py --terms search_terms.txt --results 200 --output output/
```

**Arguments:**
- `--terms` — path to search terms file
- `--results` — how many search results to fetch per term (default: 200; costs ~2 quota units per page of 50)
- `--output` — folder to write results into (created if missing)

**Output file:** `output/YYYYMMDD-HH.MM-<sanitized-term>.json`

Each file is a list of channel hit objects:
```json
[
  {
    "channel_id": "UCxxxxx",
    "channel_name": "SomeChannel",
    "channel_url": "https://www.youtube.com/channel/UCxxxxx",
    "search_term": "dome keeper gameplay",
    "video_id": "yyyyyyy",
    "video_title": "Dome Keeper is INCREDIBLE - Let's Play",
    "video_views": 184000
  }
]
```

---

## tool2_aggregate.py — Aggregate + deduplicate

Reads all `tool1` output files from a folder (or a specific glob) and collapses them into one `channels.json`. Channels that appeared across multiple search terms or multiple runs get merged — the full list of terms and source files is preserved.

```bash
python tool2_aggregate.py --input output/ --out channels.json
```

**Arguments:**
- `--input` — folder containing tool1 output files (scans recursively for `*.json`)
- `--out` — output file path (default: `channels.json`)

**Output:** `channels.json` — one object per channel:
```json
{
  "UCxxxxx": {
    "channel_id": "UCxxxxx",
    "channel_name": "SomeChannel",
    "channel_url": "https://www.youtube.com/channel/UCxxxxx",
    "search_terms": ["dome keeper gameplay", "geodepths let's play"],
    "source_files": ["20260418-22.15-dome_keeper_gameplay.json"],
    "videos": [
      { "video_id": "yyyyyyy", "video_title": "...", "video_views": 184000, "search_term": "dome keeper gameplay" }
    ]
  }
}
```

---

## tool3_profile.py — Pull channel profiles + recent activity

Takes `channels.json` and enriches each channel with: subscriber count, creation date, about/description, and their last N videos (title, views, publish date). Rate-limited to stay within quota. Fine to run overnight.

```bash
python tool3_profile.py --channels channels.json --videos 100 --out profiles.json
```

**Arguments:**
- `--channels` — path to tool2 output
- `--videos` — how many recent videos to pull per channel (default: 100)
- `--out` — output file (default: `profiles.json`)

**Output:** same structure as `channels.json` with added fields per channel:
```json
{
  "UCxxxxx": {
    "...": "...(all tool2 fields)...",
    "subscribers": 48200,
    "created_at": "2018-03-11",
    "about": "I play indie games and survival games...",
    "recent_videos": [
      {
        "video_id": "zzzzzzz",
        "title": "This Mining Game is WILD",
        "views": 22000,
        "published_at": "2026-03-15"
      }
    ]
  }
}
```

---

## tool4_filter.py — Ranked shortlist

Reads `profiles.json`, applies filters and scoring, prints a ranked table (and optionally a CSV) ready for outreach. This is where you tune thresholds.

```bash
python tool4_filter.py --profiles profiles.json --min-terms 2 --min-views 5000 --max-views 200000 --csv filtered.csv
```

**Arguments:**
- `--profiles` — path to tool3 output
- `--min-terms` — minimum number of seed search terms a channel must have appeared in (default: 2)
- `--min-views` — minimum median view count on recent videos
- `--max-views` — maximum median view count (to filter out giants)
- `--csv` — optional CSV export path

**Output columns:** Channel name, URL, subscribers, seed terms matched, median views (recent), last post date, about snippet.

---

## Quota estimate

For 10 seed terms × 200 results + 100 channels × 100 videos:

| Operation | Units |
|---|---|
| 10 searches × 4 pages × 100 units | 4,000 |
| 100 channel profiles (tool3) | ~300 |
| 100 × 100 videos list calls | ~200 |
| **Total** | **~4,500 / 10,000 daily limit** |

Fits comfortably in one day's free quota. If you have more channels, split tool3 across two nights.

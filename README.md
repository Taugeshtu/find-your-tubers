# FindYourTubers

Find YouTube channels that cover games like yours — filter by consistency, viewership, and topic overlap. Built for indie game devs doing outreach.

## Setup

### 1. Get a YouTube Data API v3 key

1. Go to [console.cloud.google.com](https://console.cloud.google.com/) and sign in with your Google account.
2. Create a new project (top-left dropdown → "New Project"). Name it anything — e.g. `find-your-tubers`.
3. In the left sidebar, go to **APIs & Services → Library**.
4. Search for **"YouTube Data API v3"** and click Enable.
5. Go to **APIs & Services → Credentials**.
6. Click **"+ Create Credentials" → API key**. Copy the key shown.
7. (Optional but recommended) Click "Edit API key" → under "API restrictions", select "Restrict key" → pick "YouTube Data API v3". This limits blast radius if the key leaks.
8. Paste the key into a file called `api.key` next to these scripts (one line, no quotes, no spaces).

Free tier gives you **10,000 quota units per day**. This tool's typical full run costs ~4,500 units (see Quota section below).

### 2. Install the Python dependency

```bash
pip install google-api-python-client
```

Python 3.10+ required.

---

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
      ├──▶ filter.py  →  (stdout / filtered.csv)           (optional: ranked shortlist before report)
      │
      ▼
tool4_report.py     →  report.html                         (interactive dashboard, open in browser)
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

**Search terms file format** — one phrase per line, written exactly as you'd type it into YouTube:

```
dome keeper gameplay
geodepths let's play
mining incremental idle game
```

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

Reads all `tool1` output files from a folder and collapses them into one `channels.json`. Channels that appeared across multiple search terms or multiple runs get merged — the full list of terms and source files is preserved.

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

Takes `channels.json` and enriches each channel with subscriber count, creation date, about/description, and their last N videos (title, views, publish date). Rate-limited to stay within quota. Fine to run overnight.

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

## filter.py — Ranked shortlist (optional pre-report step)

Reads `profiles.json`, applies numeric filters, and prints a ranked table to stdout. Useful for quickly culling a large channel list before opening the full report, or for piping into a CSV.

```bash
python filter.py --profiles profiles.json --min-terms 2 --min-views 5000 --max-views 200000 --csv filtered.csv
```

**Arguments:**
- `--profiles` — path to tool3 output
- `--min-terms` — minimum matched search terms (default: 2)
- `--min-views` — minimum median view count on recent videos
- `--max-views` — maximum median view count (filter out giants)
- `--csv` — optional CSV export path

**Output columns:** Channel name, URL, subscribers, seed terms matched, median views, last post date, about snippet. Sorted by terms matched descending, then median views descending.

---

## tool4_report.py — Interactive HTML dashboard

Reads `profiles.json` and generates a self-contained `report.html`. Open it in any browser — no server needed.

```bash
python tool4_report.py --profiles profiles.json --out report.html
```

**Arguments:**
- `--profiles` — path to tool3 output
- `--out` — output file (default: `report.html`)

**What the report shows:**
- Sortable table: channel name, subscribers, median views, matched terms, last post date
- Click any row to expand — see which search terms matched and which specific videos triggered the hit, with view-count colored links
- Hover the channel name for the channel's About text
- Hover the median views for a 90-day upload activity bar chart + recent video list sorted newest-first
- View counts color-coded by rarity (gray → white → green → blue → purple → gold)
- Dead channels (no post in 90 days) dimmed automatically

**Filters in the header:**
- Subscriber range (min / max)
- Median views range (min / max)
- Minimum matched terms count
- Tag pills — click to require that term be matched
- ⭐ Starred Only toggle

**Export starred** — the "↓ Export starred" button downloads a `.md` file:
```
ChannelName: https://youtube.com/channel/UCxxxxx
Subs: 48,200; median views: 22.0k
Terms matched: dome keeper gameplay, geodepths let's play
```

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

#!/usr/bin/env python3
"""tool4_report.py — Generate a self-contained HTML report from profiles.json.

Usage:
    python tool4_report.py --profiles profiles.json --out report.html
"""

import argparse
import json
import statistics
from datetime import date
from pathlib import Path


def fmt_views(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}k"
    return str(n)


def median_views(videos: list) -> int | None:
    counts = [v["views"] for v in videos if v.get("views")]
    return int(statistics.median(counts)) if counts else None


def last_post(videos: list) -> str:
    dates = [v["published_at"] for v in videos if v.get("published_at")]
    return max(dates) if dates else ""


def build_data_blob(channels: dict) -> dict:
    today = date.today().isoformat()

    rows = []
    for cid, ch in channels.items():
        recent = ch.get("recent_videos", [])
        med = median_views(recent)
        lp = last_post(recent)

        rows.append({
            "id": cid,
            "name": ch.get("channel_name", ""),
            "url": ch.get("channel_url", ""),
            "subscribers": ch.get("subscribers", 0),
            "about": ch.get("about", ""),
            "search_terms": ch.get("search_terms", []),
            "matched_videos": ch.get("videos", []),
            "median_views": med,
            "last_post": lp,
            "recent_videos": [
                {
                    "title": v.get("title", ""),
                    "views": v.get("views", 0),
                    "published_at": v.get("published_at", ""),
                }
                for v in recent
            ],
        })

    rows.sort(key=lambda r: (-len(r["search_terms"]), -(r["median_views"] or 0)))

    return {"today": today, "channels": rows}


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>TubeScraper Report</title>
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
    font-family: system-ui, sans-serif;
    font-size: 14px;
    background: #0f0f13;
    color: #e0e0e0;
}

/* ── View count color bands (Diablo rarity) ── */
.vc-gray   { color: #888; }
.vc-white  { color: #e0e0e0; }
.vc-green  { color: #4caf50; }
.vc-blue   { color: #5b9cf6; }
.vc-purple { color: #b06ef3; }
.vc-gold   { color: #f5c518; }

/* ── Sticky titlebar ── */
#header {
    position: sticky;
    top: 0;
    z-index: 200;
    background: #1a1a22;
    border-bottom: 1px solid #333;
    padding: 0 16px;
    height: auto;
    min-height: 36px;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px 16px;
}
#header-title {
    font-size: 14px;
    font-weight: 600;
    color: #aaa;
    white-space: nowrap;
    padding: 8px 0;
}
#header-date {
    font-size: 12px;
    color: #555;
    white-space: nowrap;
}

/* ── Filter bar ── */
#filters {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px 12px;
    padding: 6px 0;
    flex: 1;
    justify-content: flex-end;
}
.filter-group {
    display: flex;
    align-items: center;
    gap: 4px;
}
.filter-label {
    font-size: 11px;
    color: #666;
    white-space: nowrap;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}
.filter-input {
    background: #0f0f13;
    border: 1px solid #333;
    border-radius: 4px;
    color: #ccc;
    font-size: 12px;
    padding: 2px 6px;
    width: 68px;
    outline: none;
}
.filter-input:focus { border-color: #555; }
.filter-input.wide { width: 50px; }

/* tag pills */
.tag-pill {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: #1e1e2e;
    border: 1px solid #333;
    border-radius: 12px;
    padding: 2px 8px;
    font-size: 11px;
    color: #888;
    cursor: pointer;
    user-select: none;
    transition: background 0.1s, border-color 0.1s, color 0.1s;
    white-space: nowrap;
}
.tag-pill input { display: none; }
.tag-pill.active {
    background: #252540;
    border-color: #5b9cf6;
    color: #9bc8ff;
}

/* tag pill group — wraps onto multiple lines */
#tag-filter-group {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    max-width: 520px;
}

/* starred-only toggle */
#btn-starred {
    background: #1e1e2e;
    border: 1px solid #333;
    border-radius: 4px;
    color: #888;
    font-size: 12px;
    padding: 3px 10px;
    cursor: pointer;
    white-space: nowrap;
    transition: background 0.1s, color 0.1s, border-color 0.1s;
}
#btn-starred.active {
    background: #2a2a10;
    border-color: #f5c518;
    color: #f5c518;
}

/* export button */
#btn-export {
    background: #1a2a1a;
    border: 1px solid #2a5a2a;
    border-radius: 4px;
    color: #5abf5a;
    font-size: 12px;
    padding: 3px 10px;
    cursor: pointer;
    white-space: nowrap;
    transition: background 0.1s;
}
#btn-export:hover { background: #223522; }

/* ── Table wrapper ── */
#wrap { padding: 0 16px 40px; }

table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
}

thead th {
    position: sticky;
    top: var(--header-h, 36px);
    background: #1a1a22;
    text-align: left;
    padding: 7px 10px;
    font-size: 11px;
    font-weight: 600;
    color: #666;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    border-bottom: 1px solid #333;
    white-space: nowrap;
    cursor: pointer;
    user-select: none;
    z-index: 10;
}
thead th:hover { color: #ccc; }
thead th.sort-asc::after  { content: " ▲"; }
thead th.sort-desc::after { content: " ▼"; }

/* column widths */
.col-star { width: 28px; text-align: center; }
.col-name { min-width: 160px; }
.col-subs { width: 80px; text-align: right; }
.col-med  { width: 90px;  text-align: right; }
.col-terms{ min-width: 140px; }
.col-last { width: 96px; }

tbody tr.channel-row {
    border-bottom: 1px solid #1e1e1e;
    cursor: pointer;
    transition: background 0.08s;
}
tbody tr.channel-row:hover { background: #1c1c26; }
tbody tr.channel-row.expanded { background: #1c1c26; }

tbody tr.detail-row { display: none; }
tbody tr.detail-row.open { display: table-row; }
tbody tr.detail-row > td {
    padding: 4px 10px 12px 36px;
    background: #1c1c26;
    border-bottom: 1px solid #252530;
}

td { padding: 7px 10px; vertical-align: middle; }

/* ── Channel name ── */
.ch-name a {
    color: #c9c9e8;
    text-decoration: none;
    font-weight: 500;
    cursor: help;
}
.ch-name a:hover { text-decoration: underline; }

/* ── Terms (collapsed) ── */
.terms-collapsed { color: #7070a0; font-size: 13px; line-height: 1.6; }
tr.expanded .terms-collapsed { display: none; }

/* ── Expanded detail grid ── */
.detail-grid {
    display: grid;
    grid-template-columns: minmax(160px, max-content) 1fr;
    gap: 4px 16px;
    align-items: start;
}
.detail-term {
    font-size: 12px;
    color: #8080b0;
    padding: 3px 0;
    white-space: nowrap;
}
.detail-vids {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 8px;
    padding: 3px 0;
}
.vid-chip {
    font-size: 12px;
    text-decoration: none;
    font-variant-numeric: tabular-nums;
}
.vid-chip:hover { text-decoration: underline; }
.vid-sep {
    color: #333;
    font-size: 12px;
    align-self: center;
}

/* ── Star ── */
.star { font-size: 15px; color: #333; cursor: pointer; transition: color 0.12s; }
.star:hover { color: #888; }
.star.on { color: #f5c518; }

/* ── Views cell trigger ── */
.med-cell { cursor: pointer; border-bottom: 1px dashed #444; }

/* ── Popups (shared base) ── */
.popup {
    position: fixed;
    display: none;
    z-index: 999;
    background: #12121e;
    border: 1px solid #3a3a50;
    border-radius: 7px;
    box-shadow: 0 10px 40px #0009;
    pointer-events: auto;
}

/* recent-videos popup */
#popup-videos {
    width: 440px;
    max-height: 500px;
    overflow-y: auto;
    padding: 12px;
}

/* about popup */
#popup-about {
    padding: 10px 14px;
    max-width: 340px;
    font-size: 13px;
    color: #b0b0c8;
    line-height: 1.55;
}

/* ── Bar chart ── */
.tt-chart-wrap {
    position: relative;
    height: 88px;
    margin-bottom: 10px;
    border-bottom: 1px solid #333;
    padding-bottom: 4px;
}
.tt-chart {
    display: flex;
    align-items: flex-end;
    height: 80px;
    gap: 1px;
}
.tt-bar {
    flex: 1;
    min-width: 1px;
    border-radius: 1px 1px 0 0;
    transition: opacity 0.1s;
}
.tt-bar:hover { opacity: 0.75; }
.tt-ymax {
    position: absolute;
    top: 0; left: 2px;
    font-size: 10px;
    color: #555;
    pointer-events: none;
}

/* ── Video list in popup ── */
.tt-videos { list-style: none; }
.tt-videos li {
    padding: 3px 0;
    font-size: 13px;
    color: #c0c0d8;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.tt-views { margin-right: 5px; font-variant-numeric: tabular-nums; }

/* ── Dead channel ── */
tr.dead td { opacity: 0.38; }

/* ── Hidden by filter ── */
tr.filtered-out { display: none !important; }
</style>
</head>
<body>

<div id="header">
  <span id="header-title">TubeScraper — <span id="channel-count"></span> channels</span>
  <span id="header-date"></span>
  <div id="filters">
    <div class="filter-group">
      <span class="filter-label">Subs</span>
      <input class="filter-input" id="f-subs-min" type="number" min="0" placeholder="min" title="Min subscribers">
      <span class="filter-label">–</span>
      <input class="filter-input" id="f-subs-max" type="number" min="0" placeholder="max" title="Max subscribers">
    </div>
    <div class="filter-group">
      <span class="filter-label">Views</span>
      <input class="filter-input" id="f-views-min" type="number" min="0" placeholder="min" title="Min median views">
      <span class="filter-label">–</span>
      <input class="filter-input" id="f-views-max" type="number" min="0" placeholder="max" title="Max median views">
    </div>
    <div class="filter-group">
      <span class="filter-label">Min terms</span>
      <input class="filter-input wide" id="f-min-terms" type="number" min="1" placeholder="1" title="Minimum matched terms">
    </div>
    <div class="filter-group" id="tag-filter-group">
      <!-- tag pills injected by JS -->
    </div>
    <button id="btn-starred">⭐ Starred</button>
    <button id="btn-export">↓ Export starred</button>
  </div>
</div>

<div id="wrap">
<table id="tbl">
<thead>
  <tr>
    <th class="col-star">⭐</th>
    <th class="col-name"  data-col="name">Channel</th>
    <th class="col-subs"  data-col="subscribers">Subs</th>
    <th class="col-med"   data-col="median_views" title="Median views across recent videos">Views</th>
    <th class="col-terms" data-col="terms">Terms</th>
    <th class="col-last"  data-col="last_post">Last post</th>
  </tr>
</thead>
<tbody id="tbody"></tbody>
</table>
</div>

<div id="popup-videos" class="popup"></div>
<div id="popup-about"  class="popup"></div>

<script>
const DATA = /*DATA_PLACEHOLDER*/null/*END_DATA*/;

const NINETY_DAYS_MS = 90 * 24 * 60 * 60 * 1000;
const today = new Date(DATA.today);
const windowStart = new Date(today.getTime() - NINETY_DAYS_MS);

// ── View count → color class ──
function vcClass(n) {
    if (n == null || n < 1500)  return 'vc-gray';
    if (n < 9000)               return 'vc-white';
    if (n < 20000)              return 'vc-green';
    if (n < 50000)              return 'vc-blue';
    if (n < 120000)             return 'vc-purple';
    return 'vc-gold';
}

function fmtViews(n) {
    if (n == null) return '—';
    if (n >= 1e6) return (n/1e6).toFixed(1) + 'M';
    if (n >= 1e3) return (n/1e3).toFixed(1) + 'k';
    return String(n);
}
function fmtSubs(n) {
    if (!n) return '0';
    if (n >= 1e6) return (n/1e6).toFixed(2) + 'M';
    if (n >= 1e3) return (n/1e3).toFixed(0) + 'k';
    return String(n);
}
function fmtSubsFull(n) {
    if (!n) return '0';
    return n.toLocaleString();
}
function spanV(n) {
    return `<span class="${vcClass(n)}">${fmtViews(n)}</span>`;
}
function escHtml(s) {
    return (s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ── Sort ──
let sortCol = 'terms', sortDir = -1;
function sortValue(ch, col) {
    if (col === 'name')         return ch.name.toLowerCase();
    if (col === 'subscribers')  return ch.subscribers || 0;
    if (col === 'terms')        return ch.search_terms.length;
    if (col === 'median_views') return ch.median_views || 0;
    if (col === 'last_post')    return ch.last_post || '';
    return 0;
}
function sortedChannels() {
    return [...DATA.channels].sort((a, b) => {
        const av = sortValue(a, sortCol), bv = sortValue(b, sortCol);
        return av < bv ? sortDir : av > bv ? -sortDir : 0;
    });
}

const starred = new Set();

// ── Filter state ──
let filterStarredOnly = false;
let activeTags = new Set(); // empty = all pass

function getFilterValues() {
    const subsMin  = parseInt(document.getElementById('f-subs-min').value)  || 0;
    const subsMax  = parseInt(document.getElementById('f-subs-max').value)  || Infinity;
    const viewsMin = parseInt(document.getElementById('f-views-min').value) || 0;
    const viewsMax = parseInt(document.getElementById('f-views-max').value) || Infinity;
    const minTerms = parseInt(document.getElementById('f-min-terms').value) || 1;
    return { subsMin, subsMax, viewsMin, viewsMax, minTerms };
}

function channelPasses(ch) {
    const { subsMin, subsMax, viewsMin, viewsMax, minTerms } = getFilterValues();
    if (filterStarredOnly && !starred.has(ch.id)) return false;
    const subs = ch.subscribers || 0;
    if (subs < subsMin || subs > subsMax) return false;
    const views = ch.median_views || 0;
    if (views < viewsMin || views > viewsMax) return false;
    if (ch.search_terms.length < minTerms) return false;
    if (activeTags.size > 0) {
        const hasTag = ch.search_terms.some(t => activeTags.has(t));
        if (!hasTag) return false;
    }
    return true;
}

function applyFilters() {
    let visible = 0;
    document.querySelectorAll('tr.channel-row').forEach(tr => {
        const ch = DATA.channels.find(c => c.id === tr.dataset.id);
        const pass = ch && channelPasses(ch);
        tr.classList.toggle('filtered-out', !pass);
        const detail = document.querySelector(`tr.detail-row[data-id="${tr.dataset.id}"]`);
        if (detail) detail.classList.toggle('filtered-out', !pass);
        if (pass) visible++;
    });
    document.getElementById('channel-count').textContent = visible;
}

// ── Slug from video title ──
const STOP_WORDS = new Set(['the','and','for','with','this','that','from','have',
    'are','was','were','will','been','has','had','not','but','what','all','can',
    'its','your','our','their','about','into','than','then','when','which','who',
    'how','they','them','these','those','there','here','more','also','just','some',
    'like','would','could','should','very','well','even','back','only','being',
    'after','before','both','between','through','during','because','while','where']);

function slugFromTitle(title) {
    const words = title.split(/\s+/)
        .map(w => w.replace(/[^a-z0-9]/gi, '').toLowerCase())
        .filter(w => w.length >= 2 && !STOP_WORDS.has(w));
    return words.slice(0, 4).join('-') || 'video';
}

// ── Bar chart ──
function barColor(views) {
    if (views < 1500)   return '#555';
    if (views < 9000)   return '#999';
    if (views < 20000)  return '#4caf50';
    if (views < 50000)  return '#5b9cf6';
    if (views < 120000) return '#b06ef3';
    return '#f5c518';
}

function buildChart(videos) {
    const buckets = {};
    for (const v of videos) {
        const d = new Date(v.published_at);
        if (d < windowStart || d > today) continue;
        const idx = Math.floor((d - windowStart) / (24*60*60*1000));
        if (!buckets[idx]) buckets[idx] = { views: 0, title: v.title };
        else buckets[idx].title = '(multiple)';
        buckets[idx].views += v.views;
    }
    const maxViews = Math.max(...Object.values(buckets).map(b => b.views), 1);
    let bars = '';
    for (let i = 0; i < 90; i++) {
        const b = buckets[i];
        if (!b) { bars += `<div class="tt-bar" style="height:0"></div>`; continue; }
        const h = Math.max(3, Math.round((b.views / maxViews) * 76));
        const col = barColor(b.views);
        bars += `<div class="tt-bar" style="height:${h}px;background:${col}" title="${fmtViews(b.views)} — ${escHtml(b.title)}"></div>`;
    }
    const yLabel = spanV(maxViews);
    return `<div class="tt-chart-wrap"><div class="tt-ymax">${yLabel}</div><div class="tt-chart">${bars}</div></div>`;
}

function buildVideosPopup(ch) {
    const chart = buildChart(ch.recent_videos);
    // sort by date desc (most recent first)
    const sorted = ch.recent_videos.slice().sort((a, b) => {
        if (a.published_at > b.published_at) return -1;
        if (a.published_at < b.published_at) return 1;
        return 0;
    }).slice(0, 40);
    const items = sorted
        .map(v => `<li><span class="tt-views ${vcClass(v.views)}">[${fmtViews(v.views)}👁]</span>${escHtml(v.title)}</li>`)
        .join('');
    return chart + `<ul class="tt-videos">${items}</ul>`;
}

// ── Popup management ──
let hideTimers = {};

function showPopup(popup, content, anchorEl) {
    clearTimeout(hideTimers[popup.id]);
    popup.innerHTML = content;
    popup.style.display = 'block';
    placePopup(popup, anchorEl);
}

function scheduleHide(popup, delay = 120) {
    hideTimers[popup.id] = setTimeout(() => { popup.style.display = 'none'; }, delay);
}

function placePopup(popup, anchorEl) {
    const r = anchorEl.getBoundingClientRect();
    const pw = popup.offsetWidth || 440;
    const ph = popup.offsetHeight || 200;
    let x = r.left;
    let y = r.bottom + 4;
    if (x + pw > window.innerWidth - 8) x = window.innerWidth - pw - 8;
    if (y + ph > window.innerHeight - 8) y = r.top - ph - 4;
    popup.style.left = x + 'px';
    popup.style.top  = y + 'px';
}

// ── Tag filter pills setup ──
function buildTagPills() {
    const allTerms = new Set();
    DATA.channels.forEach(ch => ch.search_terms.forEach(t => allTerms.add(t)));
    const container = document.getElementById('tag-filter-group');
    if (allTerms.size === 0) { container.style.display = 'none'; return; }
    container.innerHTML = '';
    for (const term of [...allTerms].sort()) {
        const pill = document.createElement('label');
        pill.className = 'tag-pill';
        pill.title = term;
        pill.innerHTML = `<input type="checkbox"><span>${escHtml(term)}</span>`;
        pill.querySelector('input').addEventListener('change', e => {
            if (e.target.checked) activeTags.add(term);
            else activeTags.delete(term);
            pill.classList.toggle('active', e.target.checked);
            applyFilters();
        });
        container.appendChild(pill);
    }
}

// ── Export starred as markdown ──
function exportStarred() {
    const starredChannels = DATA.channels.filter(ch => starred.has(ch.id));
    if (starredChannels.length === 0) { alert('No starred channels to export.'); return; }
    const lines = starredChannels.map(ch => {
        const terms = ch.search_terms.join(', ');
        return [
            `${ch.name}: ${ch.url}`,
            `Subs: ${fmtSubsFull(ch.subscribers)}; median views: ${fmtViews(ch.median_views)}`,
            `Terms matched: ${terms}`,
        ].join('\n');
    });
    const md = lines.join('\n\n');
    const blob = new Blob([md], { type: 'text/markdown' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `tubescraper-starred-${DATA.today}.md`;
    a.click();
}

// ── Render ──
function render() {
    const tbody = document.getElementById('tbody');
    tbody.innerHTML = '';
    const channels = sortedChannels();

    for (const ch of channels) {
        const isStarred = starred.has(ch.id);
        const isDead = ch.last_post && new Date(ch.last_post) < windowStart;
        const termsCollapsed = ch.search_terms.join('; ');

        const tr = document.createElement('tr');
        tr.className = 'channel-row' + (isDead ? ' dead' : '');
        tr.dataset.id = ch.id;
        tr.innerHTML = `
          <td class="col-star"><span class="star ${isStarred?'on':''}" data-id="${ch.id}">★</span></td>
          <td class="col-name ch-name" data-id="${ch.id}">
            <a href="${ch.url}" target="_blank" rel="noopener" onclick="event.stopPropagation()">${escHtml(ch.name)}</a>
          </td>
          <td class="col-subs ${vcClass(ch.subscribers)}">${fmtSubs(ch.subscribers)}</td>
          <td class="col-med"><span class="med-cell ${vcClass(ch.median_views)}" data-id="${ch.id}">${fmtViews(ch.median_views)}</span></td>
          <td class="col-terms"><span class="terms-collapsed">${escHtml(termsCollapsed)}</span></td>
          <td class="col-last">${ch.last_post || '—'}</td>
        `;
        tbody.appendChild(tr);

        // detail row — two-column grid: term label | vid chips
        const gridRows = ch.search_terms.map(t => {
            const vids = ch.matched_videos.filter(v => v.search_term === t);
            const chips = vids.map((v, i) => {
                const slug = slugFromTitle(v.video_title);
                const url = `https://www.youtube.com/watch?v=${v.video_id}`;
                const chip = `<a class="vid-chip ${vcClass(v.video_views)}" href="${url}" target="_blank" title="${escHtml(v.video_title)}" onclick="event.stopPropagation()">[${fmtViews(v.video_views)}] ${escHtml(slug)}</a>`;
                return i < vids.length - 1 ? chip + `<span class="vid-sep">|</span>` : chip;
            }).join('');
            return `<div class="detail-term">${escHtml(t)}</div><div class="detail-vids">${chips || '<span style="color:#444">—</span>'}</div>`;
        }).join('');
        const trDetail = document.createElement('tr');
        trDetail.className = 'detail-row';
        trDetail.dataset.id = ch.id;
        trDetail.innerHTML = `<td colspan="6"><div class="detail-grid">${gridRows}</div></td>`;
        tbody.appendChild(trDetail);
    }

    updateSortHeaders();
    attachEvents();
    applyFilters();
}

function updateSortHeaders() {
    document.querySelectorAll('thead th').forEach(th => {
        th.classList.remove('sort-asc','sort-desc');
        if (th.dataset.col === sortCol)
            th.classList.add(sortDir === -1 ? 'sort-desc' : 'sort-asc');
    });
}

function attachEvents() {
    const ppVideos = document.getElementById('popup-videos');
    const ppAbout  = document.getElementById('popup-about');

    [ppVideos, ppAbout].forEach(pp => {
        pp.addEventListener('mouseenter', () => clearTimeout(hideTimers[pp.id]));
        pp.addEventListener('mouseleave', () => scheduleHide(pp, 80));
    });

    // expand/collapse rows
    document.querySelectorAll('tr.channel-row').forEach(tr => {
        tr.addEventListener('click', e => {
            if (e.target.classList.contains('star')) return;
            if (e.target.tagName === 'A') return;
            const detail = document.querySelector(`tr.detail-row[data-id="${tr.dataset.id}"]`);
            tr.classList.toggle('expanded');
            detail.classList.toggle('open');
        });
    });

    // stars
    document.querySelectorAll('.star').forEach(el => {
        el.addEventListener('click', e => {
            e.stopPropagation();
            starred.has(el.dataset.id) ? starred.delete(el.dataset.id) : starred.add(el.dataset.id);
            el.classList.toggle('on');
        });
    });

    // about popup on channel name
    document.querySelectorAll('.ch-name').forEach(el => {
        const ch = DATA.channels.find(c => c.id === el.dataset.id);
        if (!ch?.about) return;
        el.addEventListener('mouseenter', () => showPopup(ppAbout, escHtml(ch.about).replace(/\n/g,'<br>'), el));
        el.addEventListener('mouseleave', () => scheduleHide(ppAbout));
    });

    // videos popup on median views
    document.querySelectorAll('.med-cell').forEach(el => {
        const ch = DATA.channels.find(c => c.id === el.dataset.id);
        if (!ch?.recent_videos?.length) return;
        el.addEventListener('mouseenter', () => showPopup(ppVideos, buildVideosPopup(ch), el));
        el.addEventListener('mouseleave', () => scheduleHide(ppVideos));
    });
}

// ── Sort header clicks ──
document.querySelectorAll('thead th[data-col]').forEach(th => {
    th.addEventListener('click', () => {
        sortCol === th.dataset.col ? (sortDir *= -1) : (sortCol = th.dataset.col, sortDir = -1);
        render();
    });
});

// ── Header height → thead top ──
function syncHeaderHeight() {
    const h = document.getElementById('header').offsetHeight;
    document.documentElement.style.setProperty('--header-h', h + 'px');
}

// ── Init ──
document.getElementById('header-date').textContent = DATA.today;

buildTagPills();

['f-subs-min','f-subs-max','f-views-min','f-views-max','f-min-terms'].forEach(id => {
    document.getElementById(id).addEventListener('input', applyFilters);
});

document.getElementById('btn-starred').addEventListener('click', () => {
    filterStarredOnly = !filterStarredOnly;
    document.getElementById('btn-starred').classList.toggle('active', filterStarredOnly);
    applyFilters();
});

document.getElementById('btn-export').addEventListener('click', exportStarred);

render();
syncHeaderHeight();
new ResizeObserver(syncHeaderHeight).observe(document.getElementById('header'));
</script>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description="Generate HTML report from profiles.json")
    parser.add_argument("--profiles", default="profiles.json")
    parser.add_argument("--out", default="report.html")
    args = parser.parse_args()

    channels = json.loads(Path(args.profiles).read_text())
    blob = build_data_blob(channels)

    html = HTML_TEMPLATE.replace(
        "/*DATA_PLACEHOLDER*/null/*END_DATA*/",
        json.dumps(blob, ensure_ascii=False)
    )

    Path(args.out).write_text(html, encoding="utf-8")
    print(f"Report → {args.out}  ({len(blob['channels'])} channels)")


if __name__ == "__main__":
    main()

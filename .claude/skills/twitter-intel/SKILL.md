---
name: twitter-intel
description: "Twitter keyword intelligence — search, monitor, and analyze tweet trends over time. Triggers on 'twitter intel', 'tweet search', 'monitor keyword', 'twitter trend', '/twitter-intel', 'track topic on twitter'."
tags:
  - twitter
  - intelligence
  - search
  - monitoring
  - trends
---

# Twitter Intel — Keyword Search & Trend Monitor

Search Twitter by keyword, collect high-engagement tweets, analyze trends over time, and generate structured reports. Powered by `rnet_twitter.py` GraphQL search (no browser automation needed).

---

## Architecture

```
Phase 1: On-demand Search (user-triggered)
  User says "search OpenAI on twitter" -> search -> filter -> report

Phase 2: Keyword Monitoring (cron-driven)
  Config defines keywords -> scheduled search -> diff with last run -> alert on new high-engagement tweets

Phase 3: Trend Analysis (on-demand or weekly)
  Aggregate saved searches -> group by week -> detect topic shifts -> generate narrative
```

---

## Prerequisites

```python
# Install rnet
pip install "rnet>=3.0.0rc20" --pre

# Required: rnet_twitter.py + cookies
# - rnet_twitter.py (included in this repo, has search_tweets method)
# - twitter_cookies.json (auth_token + ct0, valid ~2 weeks)
```

**Cookie refresh**: When search returns 403, cookies need refresh. Get new `auth_token` + `ct0` from Chrome DevTools -> Application -> Cookies -> x.com.

---

## Phase 1: On-demand Search

When user says "search [keyword] on twitter", "twitter intel [topic]", "find tweets about [X]":

### Step 1 — Run Search

```python
import asyncio
from rnet_twitter import RnetTwitterClient

async def search(query, count=200):
    client = RnetTwitterClient()
    client.load_cookies("twitter_cookies.json")
    tweets = await client.search_tweets(query, count=count, product="Top")
    return tweets
```

**Search modes:**

| Mode | `product=` | Use case |
|------|-----------|----------|
| High-engagement | `"Top"` | Find influential tweets, content analysis |
| Real-time | `"Latest"` | Monitor breaking discussions, live tracking |

**Useful Twitter search operators:**

| Operator | Example | Effect |
|----------|---------|--------|
| `lang:en` | `OpenAI lang:en` | English only |
| `since:` / `until:` | `since:2026-01-24 until:2026-02-24` | Date range |
| `-filter:replies` | `OpenAI -filter:replies` | Original tweets only |
| `min_faves:N` | `min_faves:50` | Minimum likes (only works with Latest) |
| `from:` | `from:karpathy` | Specific author |
| `"exact"` | `"AI agent"` | Exact phrase |

### Step 2 — Filter & Enrich

After raw search, filter for quality:

```python
# Filter: relevant + has engagement
filtered = [
    t for t in tweets
    if keyword.lower() in t["text"].lower()  # actually mentions keyword
    and (t["favorite_count"] >= 10 or t["retweet_count"] >= 5)  # has engagement
    and not t["is_reply"]  # original tweets preferred
]
```

### Step 3 — Report

Output a structured summary:

```
## Twitter Intel: [keyword]
**Period:** [date range] | **Tweets found:** N | **After filter:** N

### Top Tweets (by engagement)
1. @author (X likes, Y RTs, Z views) — date
   "tweet text..."
   [link]

2. ...

### Key Themes
- Theme 1: [description] (N tweets)
- Theme 2: [description] (N tweets)

### Notable Authors
| Author | Followers | Tweets in set | Total engagement |
|--------|-----------|---------------|-----------------|
```

---

## Phase 2: Keyword Monitoring (Cron)

### Config File

```json
{
  "monitors": [
    {
      "id": "my-product-en",
      "query": "MyProduct lang:en -filter:replies",
      "product": "Top",
      "count": 100,
      "min_likes": 10,
      "alert_threshold": 100,
      "enabled": true
    },
    {
      "id": "competitor-mentions",
      "query": "CompetitorName OR \"brand consistency\" lang:en",
      "product": "Latest",
      "count": 50,
      "min_likes": 5,
      "alert_threshold": 50,
      "enabled": true
    }
  ]
}
```

### State File

```json
{
  "my-product-en": {
    "last_run": "2026-02-24T12:00:00Z",
    "last_tweet_ids": ["id1", "id2", "..."],
    "total_collected": 450
  }
}
```

### Cron Workflow

1. Read config -> iterate enabled monitors
2. For each monitor:
   - Run `search_tweets(query, count, product)`
   - Filter by `min_likes`
   - Diff against `last_tweet_ids` -> find NEW tweets only
   - If any new tweet has `favorite_count >= alert_threshold` -> immediate alert
   - Save all new tweets to daily file `{monitor_id}/YYYY-MM-DD.json`
   - Update state file
3. Send summary notification (if there are new notable tweets)

---

## Phase 3: Trend Analysis

When user says "analyze twitter trend for [keyword]", "twitter trend report":

### Workflow

1. Load all saved daily files from `{monitor_id}/`
2. Group tweets by week
3. For each week, extract:
   - Total tweet count + total engagement
   - Top 5 tweets by likes
   - Dominant themes (use LLM to categorize)
   - New authors that appeared
   - Sentiment shift
4. Generate a week-by-week narrative

### Output Format

```markdown
## Trend Report: [keyword]
**Period:** Week 1 (Jan 24-26) to Week 5 (Feb 17-23)
**Total tweets:** N | **Total engagement:** X likes, Y RTs

### Week-by-Week Evolution

#### Week 1 (Jan 24-26): [Theme title]
- Dominant narrative: ...
- Top tweet: @author — "..."
- Key signal: ...

#### Week 2 (Jan 27-Feb 2): [Theme title]
...

### Trend Shifts Detected
1. [Shift description] — happened in Week X
2. ...

### Top Authors Across Period
| Author | Appearances | Total Likes | First seen |
```

---

## Commands

| User Says | Agent Does |
|-----------|-----------|
| `/twitter-intel [keyword]` | Search + filter + report (Top, 200 tweets) |
| `/twitter-intel "[phrase]" --latest` | Search Latest mode |
| `monitor "[keyword]" on twitter` | Add to monitoring config |
| `twitter intel status` | Show all active monitors + last run |
| `twitter trend report [keyword]` | Analyze saved data, generate trend narrative |
| `refresh twitter cookies` | Guide user through cookie refresh |

---

## Technical Notes

- **SearchTimeline requires POST** (GET returns 404) — this is handled by `rnet_twitter.py`
- **GraphQL query IDs rotate** — if search returns 404, re-extract the SearchTimeline ID from `https://abs.twimg.com/responsive-web/client-web/main.*.js`
- **User data path** (2026-02): `screen_name` is now at `core.user_results.result.core.screen_name` (not `.legacy`)
- **Rate limits**: ~300 requests/15min window. With 20 tweets per page, 200 tweets = 10 requests. Safe for cron every 4 hours.
- **Cookie lifetime**: `auth_token` expires after ~2 weeks. Monitor for 403 errors.

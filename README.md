# Claude Skill: Twitter/X Automation

Three Claude Code skills for Twitter/X — account growth, keyword intelligence, and content strategy. Powered by `rnet` (Rust HTTP client that bypasses Cloudflare).

## Skills

| Skill | Purpose | Key Feature |
|-------|---------|-------------|
| **twitter-cultivate** | Account growth | Health metrics, shadowban check, unfollow recommendations, algorithm-optimized posting |
| **twitter-intel** | Keyword search & monitoring | Search 200+ tweets by keyword, filter by engagement, trend analysis over time |
| **twitter-x-gtm** | Content strategy | Hook formulas, content mix, thread templates, event content playbook |

## How It Works

Unlike most Twitter automation tools that use official API keys ($100/mo+) or headless browsers (easily detected), this uses:

1. **`rnet`** — Rust HTTP client with Chrome TLS fingerprint emulation. Twitter's Cloudflare can't tell it apart from a real browser.
2. **Twitter GraphQL API** — The same internal API that twitter.com uses. No API key needed, just your browser cookies.
3. **`rnet_twitter.py`** — Lightweight async Python wrapper included in this repo.

### What `rnet_twitter.py` Can Do

```python
from rnet_twitter import RnetTwitterClient

client = RnetTwitterClient()
client.load_cookies("twitter_cookies.json")

# Search tweets by keyword
tweets = await client.search_tweets("AI agents", count=200, product="Top")

# Get user profile
user = await client.get_user_by_screen_name("elonmusk")

# Get user's recent tweets
tweets = await client.get_user_tweets(user["rest_id"], count=20)

# Post a tweet
await client.create_tweet("Hello world!")

# Reply to a tweet
await client.create_tweet("Great point!", reply_to="1234567890")

# Like a tweet
await client.favorite_tweet("1234567890")

# Delete a tweet
await client.delete_tweet("1234567890")
```

## Installation

### Option 1: Claude Code (recommended)

```bash
# Add as a skill source
claude skills add PHY041/claude-skill-twitter
```

Or manually: copy the `.claude/skills/` folder into your project's `.claude/skills/` directory.

### Option 2: OpenClaw

Copy skill folders to your OpenClaw skills directory:

```bash
# Clone the repo
git clone https://github.com/PHY041/claude-skill-twitter.git
cd claude-skill-twitter

# Copy skills to OpenClaw
cp -r .claude/skills/twitter-cultivate ~/.openclaw/skills/
cp -r .claude/skills/twitter-intel ~/.openclaw/skills/
cp -r .claude/skills/twitter-x-gtm ~/.openclaw/skills/
```

### Option 3: Manual

Copy `rnet_twitter.py` and the SKILL.md files you need into your project.

## Optional GetXAPI Backend

The default path uses `rnet_twitter.py` with local browser cookies. If you
prefer API-key based access for research agents, monitors, or shared team
workflows, this repo also includes `getxapi_backend.py`. It exposes the same
async methods used in the examples:

- `search_tweets(query, count, product)`
- `get_user_by_screen_name(screen_name)`
- `get_user_tweets(user_id, count)`
- `create_tweet(text, reply_to=None)`
- `favorite_tweet(tweet_id)`
- `delete_tweet(tweet_id)`

Configure:

```bash
export GETXAPI_API_KEY="..."
export GETXAPI_BASE_URL="https://api.getxapi.com"
```

Then swap the import in scripts that need the managed backend:

```python
from getxapi_backend import GetXAPIClient

client = GetXAPIClient()
tweets = await client.search_tweets("AI agents", count=50, product="Top")
```

Write actions stay off by default. Enable them only for explicit posting,
replying, liking, or deletion workflows:

```bash
export GETXAPI_ACCOUNT="@your_account"
export GETXAPI_ENABLE_ACTIONS=true
```

## Prerequisites

### 1. Install rnet

```bash
pip install "rnet>=3.0.0rc20" --pre
```

> `rnet` is a Rust-based HTTP client with TLS fingerprint emulation. It's what lets us bypass Cloudflare without a real browser.

### 2. Get Twitter Cookies

You need two cookies from a logged-in Twitter/X session:

1. Open Chrome and go to [x.com](https://x.com) (make sure you're logged in)
2. Open DevTools (F12) -> Application -> Cookies -> `https://x.com`
3. Find and copy these two values:
   - `auth_token` — your session token
   - `ct0` — CSRF token
4. Create `twitter_cookies.json`:

```json
[
  {"name": "auth_token", "value": "paste_your_auth_token_here"},
  {"name": "ct0", "value": "paste_your_ct0_here"}
]
```

> Cookies expire after ~2 weeks. When you start getting 403 errors, repeat these steps to refresh.

### 3. Verify Setup

```python
import asyncio
from rnet_twitter import RnetTwitterClient

async def test():
    client = RnetTwitterClient()
    client.load_cookies("twitter_cookies.json")
    user = await client.get_user_by_screen_name("elonmusk")
    print(f"@{user.get('screen_name')} — {user.get('followers_count')} followers")

asyncio.run(test())
```

## Quick Start

### Search Tweets (twitter-intel)

```
You: search "AI agents" on twitter
Claude: [runs search, filters by engagement, generates report]

You: twitter trend report for "OpenAI"
Claude: [analyzes saved data, generates week-by-week narrative]
```

### Account Health Check (twitter-cultivate)

```
You: check my twitter health @myhandle
Claude: [analyzes ratio, estimates TweepCred, checks shadowban, recommends unfollows]
```

### Content Strategy (twitter-x-gtm)

```
You: write a thread about my new product launch
Claude: [researches viral patterns, adapts with your voice, delivers thread + schedule]
```

## Technical Notes

- **SearchTimeline requires POST** — Twitter's GraphQL search endpoint returns 404 for GET requests. This is handled automatically by `rnet_twitter.py`.
- **GraphQL query IDs rotate** — Twitter periodically changes endpoint IDs. If search breaks with 404, extract the new SearchTimeline ID from `https://abs.twimg.com/responsive-web/client-web/main.*.js` and update `ENDPOINTS["SearchTimeline"]` in `rnet_twitter.py`.
- **Rate limits** — ~300 requests per 15-minute window. 200 tweets = ~10 requests. Safe for regular use.
- **Cookie format** — Same JSON format as twikit (list of `{name, value}` dicts), so existing cookie files work.

## Why Not Use...

| Alternative | Problem |
|-------------|---------|
| **Twitter API v2** | $100/mo for Basic, search is Premium-only ($5,000/mo) |
| **Twikit** | Dead since Nov 2025 — Cloudflare 403 blocks all httpx-based requests |
| **Playwright/Puppeteer** | Detectable via `navigator.webdriver`, rate-limited |
| **Selenium** | Same detection issues as Playwright |
| **Nitter** | Shut down (Twitter blocked all instances) |

`rnet` bypasses Cloudflare at the TLS fingerprint level (C++ emulation, not JavaScript patches), making it indistinguishable from a real Chrome browser.

## File Structure

```
claude-skill-twitter/
├── README.md
├── LICENSE
├── rnet_twitter.py                   # Core: async Twitter GraphQL client
├── twitter_cookies.example.json      # Template for cookie file
└── .claude/
    └── skills/
        ├── twitter-cultivate/        # Account growth & health
        │   └── SKILL.md
        ├── twitter-intel/            # Keyword search & monitoring
        │   └── SKILL.md
        └── twitter-x-gtm/           # Content strategy & templates
            └── SKILL.md
```

## Related Projects

- [claude-skill-reddit](https://github.com/PHY041/claude-skill-reddit) — Reddit automation skills (AppleScript + Chrome)
- [claude-skill-devto](https://github.com/PHY041/claude-skill-devto) — DEV.to publishing skill
- [claude-agent-skills](https://github.com/PHY041/claude-agent-skills) — Full collection of 14+ Claude Code skills

## License

MIT

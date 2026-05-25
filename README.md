# dibi8 Auto Publisher

Automatically publishes articles from [dibi8.com](https://dibi8.com) to multiple social media platforms on a scheduled basis — with built-in anti-ban protections.

## Anti-Ban Safety Features

| Feature | Description |
|---------|-------------|
| **Startup jitter** | Random 0-50 min delay on each run — post time is fully random within each hour window |
| **Random skip** | 15% chance to skip a run entirely — irregular posting looks human |
| **Per-platform daily caps** | Twitter: 6/day (paid), Facebook: 4/day, Reddit: 2/day, Dev.to: 3/day |
| **Minimum intervals** | Twitter 2h, Facebook 3h, Reddit 8h, Dev.to 4h |
| **Inter-platform delays** | 1-5 min random wait between posting to different platforms |
| **Content variation** | Different post format/template per platform, random hashtags, varied hooks |
| **Shuffled platform order** | Platforms are published in random order each run |
| **Token validation** | Credentials are checked before publishing; expired tokens logged |
| **Retry with backoff** | Exponential backoff on rate-limit errors (not blind retry) |
| **Reddit-specific** | Subreddit rotation, duplicate URL detection, varied title prefixes |
| **User-Agent rotation** | Random browser UA for web scraping |
| **Weighted article selection** | Newer articles are more likely to be picked |

## Features

- **RSS-based scraping** — fetches articles from dibi8.com's RSS feed (257+ articles)
- **Multi-platform publishing** — Twitter/X (paid), Facebook, Reddit, **Dev.to**
- **HN Submit Helper** — weekly Tuesday 14:00 UTC, generates `data/hn-recommendations-YYYY-MM-DD.md` with 3 candidates × 3 title variants × 1-click submit URLs
- **Smart scheduling** — runs every hour during business hours in both Asia and US timezones
- **Duplicate prevention** — tracks published articles per platform in `data/published.json`
- **Auto-reset** — when all articles have been published, resets and starts cycling again
- **Graceful degradation** — unconfigured platforms are silently skipped
- **SEO-safe** — Dev.to posts use `canonical_url` back to dibi8 (no duplicate content penalty)

## V2 Upgrade (2026-05-25)

Why removed/changed:

| Platform | 2026 Reality | Decision |
|----------|--------------|----------|
| ⛔ Medium | API closed to new tokens since 2025-01-01 | Removed |
| ⛔ LinkedIn | Marketing Developer Platform requires verified company + $699+/mo | Removed |
| 💰 Twitter/X | Free tier killed 2026-02; URL post = $0.20 each | Opt-in only (`TWITTER_PAID_MODE_CONFIRMED=true`) |
| 🆕 Dev.to | Free REST API, 30 req/min, developer audience | Added |
| 💀 Hashnode | 2026 起 API 转 Pro plan (测试时发现) | Removed |
| 🆕 HN Helper | Weekly recommendation md with 1-click submit URLs | Added |

## Schedule

| Region | Local Time | UTC |
|--------|-----------|-----|
| Asia (UTC+8) | 09:00 – 17:00 | 01:00 – 09:00 |
| US (UTC-5) | 09:00 – 17:00 | 14:00 – 22:00 |

The workflow runs **every hour** during these windows = **18 cron triggers/day**.
With random skips (~15%) and rate limits, actual posts per platform are much lower.

## Quick Start

1. **Fork/clone** this repository
2. **Set up API keys** — follow [API_SETUP_GUIDE.md](./API_SETUP_GUIDE.md)
3. **Add secrets** to your GitHub repository settings
4. The GitHub Action will start running automatically on schedule

### Manual Run

```bash
pip install -r requirements.txt

# Disable delays for local testing
export STARTUP_JITTER_MAX=0
export INTER_PLATFORM_DELAY_MIN=0
export INTER_PLATFORM_DELAY_MAX=0
export RANDOM_SKIP_PROBABILITY=0

# Set platform credentials
export TWITTER_API_KEY="..."
# ... (see API_SETUP_GUIDE.md for all variables)

python run.py
```

## Project Structure

```
├── .github/workflows/
│   └── auto-publish.yml     # GitHub Actions scheduled workflow
├── src/
│   ├── config.py            # Configuration & environment variables
│   ├── scraper.py           # RSS feed parser & article metadata scraper
│   ├── scheduler.py         # Main orchestrator with safety controls
│   ├── safety.py            # Rate limiting, daily caps, cooldowns, jitter
│   ├── content.py           # Content variation engine (per-platform formatting)
│   ├── publishers/
│   │   ├── twitter.py       # Twitter/X via Tweepy + paid-mode opt-in (2026-02 free tier killed)
│   │   ├── facebook.py      # Facebook Page via Graph API + token expiry detection
│   │   ├── reddit.py        # Reddit via PRAW + duplicate detection + subreddit rotation
│   │   └── devto.py         # Dev.to via Forem REST API + canonical_url SEO-safe
│   └── helpers/
│       └── hn_submit.py     # Weekly HN submit recommendation generator
├── data/
│   ├── published.json       # Tracks published article URLs per platform
│   ├── rate_limits.json     # Tracks daily post counts and last-post timestamps
│   └── hn-recommendations-YYYY-MM-DD.md  # Weekly HN candidates (1-click submit URLs)
├── requirements.txt
├── API_SETUP_GUIDE.md       # Step-by-step API key setup guide
└── README.md
```

## Configuration

All configuration is via environment variables (or GitHub Secrets).

### Anti-Ban Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `STARTUP_JITTER_MAX` | `3000` | Max random startup delay in seconds (0-50 min, covers full hour) |
| `INTER_PLATFORM_DELAY_MIN` | `60` | Min delay between platform posts (seconds) |
| `INTER_PLATFORM_DELAY_MAX` | `300` | Max delay between platform posts (seconds) |
| `RANDOM_SKIP_PROBABILITY` | `0.15` | Probability (0-1) to skip a run entirely |

### Platform Credentials

| Platform | Required Secrets |
|----------|-----------------|
| Twitter/X (opt-in, paid) | `TWITTER_API_KEY`, `TWITTER_API_SECRET`, `TWITTER_ACCESS_TOKEN`, `TWITTER_ACCESS_SECRET`, **`TWITTER_PAID_MODE_CONFIRMED=true`** |
| Facebook | `FACEBOOK_PAGE_ID`, `FACEBOOK_ACCESS_TOKEN` |
| Reddit | `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USERNAME`, `REDDIT_PASSWORD`, `REDDIT_SUBREDDITS` |
| Dev.to | `DEVTO_API_KEY` |

### Reddit Multi-Subreddit

Set `REDDIT_SUBREDDITS` to a comma-separated list to rotate between subreddits:

```
REDDIT_SUBREDDITS=artificial,MachineLearning,OpenSource,selfhosted
```

## Avoiding Account Bans: Best Practices

1. **Start slow** — Don't enable all platforms at once. Start with Dev.to (lowest risk, real audience) and add Reddit/Facebook after observing 1-2 weeks.
2. **Engage manually** — Especially on Reddit, make sure your account has genuine activity (comments, upvotes) beyond auto-posts. **Required: 100+ comment karma + 7-30 day account age before first self-promo post.**
3. **Monitor logs** — Check GitHub Actions logs regularly for warnings about rate limits or expired tokens.
4. **Facebook Page tokens** — Use a Page Access Token (60-day refresh needed) rather than a User Access Token.
5. **Reddit karma** — Build up account karma before enabling auto-posting. Low-karma accounts are flagged more easily.
6. **Twitter is paid** — Twitter/X free tier killed 2026-02. Each URL-containing post costs ~$0.20. Only enable `TWITTER_PAID_MODE_CONFIRMED=true` if you've budgeted for it (~$12/month at default daily caps).
7. **Dev.to canonical URLs** — Always set canonical_url back to dibi8.com (built-in) to avoid SEO duplicate-content penalty.

## License

MIT

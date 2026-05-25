"""Configuration for the auto-publisher."""

import os

# dibi8.com RSS feed
RSS_FEED_URL = "https://dibi8.com/index.xml"
SITE_BASE_URL = "https://dibi8.com"

# Published articles tracking file
PUBLISHED_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "published.json")

# Number of articles to publish per run (per platform)
ARTICLES_PER_RUN = 1

# Hashtags to include in posts (fallback pool)
DEFAULT_HASHTAGS = ["#AI", "#OpenSource", "#DevTools", "#MachineLearning", "#LLM"]

# --- Safety: Anti-Ban Settings ---
# Add random startup delay (0 to this many seconds) to avoid exact cron timing
STARTUP_JITTER_MAX = int(os.environ.get("STARTUP_JITTER_MAX", "3000"))  # 50 min
# Delay between posting to different platforms (seconds)
INTER_PLATFORM_DELAY_MIN = int(os.environ.get("INTER_PLATFORM_DELAY_MIN", "60"))
INTER_PLATFORM_DELAY_MAX = int(os.environ.get("INTER_PLATFORM_DELAY_MAX", "300"))
# Skip publishing randomly (probability 0-1) to appear less regular
RANDOM_SKIP_PROBABILITY = float(os.environ.get("RANDOM_SKIP_PROBABILITY", "0.15"))

# --- Twitter/X — REMOVED 2026-05-26 ---
# 原因: 2026-02 起 X 砍 free tier 走 Pay-Per-Use, 带 URL 推 $0.20/条,
# dibi8 当前 ROI 不划算. 改 home-hermes/x-manual-posts/ 手动发推工作流, $0 成本.

# --- Facebook ---
FACEBOOK_PAGE_ID = os.environ.get("FACEBOOK_PAGE_ID", "")
FACEBOOK_ACCESS_TOKEN = os.environ.get("FACEBOOK_ACCESS_TOKEN", "")

# --- LinkedIn — REMOVED 2026-05-25 V2 upgrade ---
# 原因: Marketing Developer Platform 申请门槛极高 (需 verified company page +
# 法人验证 + 数周审核 + 大概率被拒), 即使过了起步 $699/月。个人开发者无解。

# --- Medium — REMOVED 2026-05-25 V2 upgrade ---
# 原因: 2025-01-01 起 Medium 不再发放新 integration tokens, 新用户拿不到 API。

# --- Reddit ---
REDDIT_CLIENT_ID = os.environ.get("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET", "")
REDDIT_USERNAME = os.environ.get("REDDIT_USERNAME", "")
REDDIT_PASSWORD = os.environ.get("REDDIT_PASSWORD", "")
REDDIT_SUBREDDITS = os.environ.get(
    "REDDIT_SUBREDDITS",
    os.environ.get("REDDIT_SUBREDDIT", "artificial"),
)

# --- Dev.to (V2 upgrade 2026-05-25) ---
# API: https://developers.forem.com/api
# 申请: https://dev.to/settings/extensions → API Keys → Generate
# Rate limit: 30 req/min (友好)
# 关键: canonical_url 必填,告诉 Google 原文在 dibi8 (防 SEO duplicate content)
DEVTO_API_KEY = os.environ.get("DEVTO_API_KEY", "")

# --- Hashnode — REMOVED 2026-05-25 V2 (测试时发现) ---
# 原因: 2026 起 gql.hashnode.com 转 Pro plan 才能用 API,免费版死。

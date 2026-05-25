"""Anti-ban safety controls: rate limiting, daily caps, cooldowns, and jitter."""

import json
import logging
import random
import time
from datetime import datetime, timezone
from pathlib import Path

from . import config

logger = logging.getLogger(__name__)

RATE_LIMITS_FILE = Path(config.PUBLISHED_FILE).parent / "rate_limits.json"

# Per-platform daily posting caps (conservative to avoid bans)
# 2026-05-25 V2 upgrade: 移除 medium/linkedin/hashnode (API 死/付费), 加 devto
DAILY_CAPS = {
    "twitter": 6,    # 含 URL post $0.20/次 (2026-02 起付费),建议主人审慎开启
    "facebook": 4,   # Pages can post more, but 4 is natural
    "reddit": 2,     # Reddit heavily penalizes frequent self-promotion
    "devto": 3,      # Dev.to 友好,但仍要节制保持质量
}

# Minimum hours between posts on the same platform
MIN_HOURS_BETWEEN = {
    "twitter": 2,
    "facebook": 3,
    "reddit": 8,
    "devto": 4,
}


def _load_rate_data() -> dict:
    try:
        with open(RATE_LIMITS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_rate_data(data: dict) -> None:
    RATE_LIMITS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(RATE_LIMITS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def record_post(platform: str) -> None:
    """Record that a post was made on this platform right now."""
    data = _load_rate_data()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if platform not in data:
        data[platform] = {"posts_today": [], "last_post": ""}

    platform_data = data[platform]

    # Clean old entries (keep only today's)
    platform_data["posts_today"] = [
        ts for ts in platform_data.get("posts_today", [])
        if ts.startswith(today)
    ]

    now_iso = datetime.now(timezone.utc).isoformat()
    platform_data["posts_today"].append(now_iso)
    platform_data["last_post"] = now_iso
    data[platform] = platform_data
    _save_rate_data(data)


def can_post(platform: str) -> tuple[bool, str]:
    """Check if posting is allowed right now. Returns (allowed, reason)."""
    data = _load_rate_data()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    now = datetime.now(timezone.utc)

    platform_data = data.get(platform, {})

    # Check daily cap
    today_posts = [
        ts for ts in platform_data.get("posts_today", [])
        if ts.startswith(today)
    ]
    cap = DAILY_CAPS.get(platform, 3)
    if len(today_posts) >= cap:
        return False, f"Daily cap reached ({len(today_posts)}/{cap})"

    # Check minimum interval
    last_post_str = platform_data.get("last_post", "")
    if last_post_str:
        try:
            last_post = datetime.fromisoformat(last_post_str)
            min_hours = MIN_HOURS_BETWEEN.get(platform, 2)
            hours_since = (now - last_post).total_seconds() / 3600
            if hours_since < min_hours:
                return False, f"Too soon (last post {hours_since:.1f}h ago, min {min_hours}h)"
        except ValueError:
            pass

    return True, "OK"


def human_delay(min_seconds: int = 30, max_seconds: int = 180) -> None:
    """Sleep a random interval to appear more human between platform posts."""
    delay = random.randint(min_seconds, max_seconds)
    logger.info("Human delay: waiting %d seconds before next action", delay)
    time.sleep(delay)


def jitter_delay() -> None:
    """Add a small random startup delay (0-15 min) to avoid exact cron timing."""
    delay = random.randint(0, 900)
    logger.info("Startup jitter: waiting %d seconds (%.1f min)", delay, delay / 60)
    time.sleep(delay)

"""Twitter/X publisher using Tweepy with anti-ban protections."""

import logging
import time

import tweepy

from .. import config
from ..scraper import Article
from ..content import format_twitter
from ..safety import can_post, record_post

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


def is_configured() -> bool:
    """检查 Twitter credentials + 主人显式确认付费模式 (V2 upgrade 2026-05-25)。

    2026-02-06 起 X API 取消免费 tier, 新用户必须 pay-per-use:
      - 含 URL 的 post: $0.20/次  ← dibi8 推广必含 URL
      - 当前 daily cap 6 → 月度 ~$12 USD

    必须设置环境变量 TWITTER_PAID_MODE_CONFIRMED=true 才会真发,
    否则即使 credentials 齐全也 skip (防止意外烧钱)。
    """
    has_creds = all([
        config.TWITTER_API_KEY,
        config.TWITTER_API_SECRET,
        config.TWITTER_ACCESS_TOKEN,
        config.TWITTER_ACCESS_SECRET,
    ])
    paid_confirmed = __import__("os").environ.get("TWITTER_PAID_MODE_CONFIRMED", "").lower() == "true"
    if has_creds and not paid_confirmed:
        logger.warning(
            "⚠️ Twitter credentials 存在但 TWITTER_PAID_MODE_CONFIRMED=true 未设置。"
            " X API 2026-02 起 pay-per-use, 含 URL post $0.20/次 (月度 ~$12)。"
            " 设置环境变量 TWITTER_PAID_MODE_CONFIRMED=true 才会真发,否则 skip。"
        )
        return False
    return has_creds


def validate_credentials() -> tuple[bool, str]:
    """Verify Twitter credentials are still valid."""
    if not is_configured():
        return False, "Not configured"
    try:
        client = tweepy.Client(
            consumer_key=config.TWITTER_API_KEY,
            consumer_secret=config.TWITTER_API_SECRET,
            access_token=config.TWITTER_ACCESS_TOKEN,
            access_token_secret=config.TWITTER_ACCESS_SECRET,
        )
        me = client.get_me()
        if me.data:
            return True, f"Authenticated as @{me.data.username}"
        return False, "Could not verify identity"
    except tweepy.errors.Unauthorized:
        return False, "EXPIRED/INVALID: Twitter credentials are unauthorized"
    except Exception as exc:
        return False, f"Validation error: {exc}"


def publish(article: Article) -> bool:
    """Post an article to Twitter/X with retry and rate-limit awareness."""
    if not is_configured():
        logger.warning("Twitter not configured, skipping")
        return False

    allowed, reason = can_post("twitter")
    if not allowed:
        logger.info("Twitter rate limit: %s", reason)
        return False

    tweet_text = format_twitter(article)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            client = tweepy.Client(
                consumer_key=config.TWITTER_API_KEY,
                consumer_secret=config.TWITTER_API_SECRET,
                access_token=config.TWITTER_ACCESS_TOKEN,
                access_token_secret=config.TWITTER_ACCESS_SECRET,
            )
            client.create_tweet(text=tweet_text)
            record_post("twitter")
            logger.info("Successfully posted to Twitter: %s", article.title)
            return True

        except tweepy.errors.TooManyRequests:
            wait = 60 * (2 ** attempt)
            logger.warning("Twitter rate limited, waiting %ds (attempt %d/%d)", wait, attempt, MAX_RETRIES)
            time.sleep(wait)

        except tweepy.errors.Forbidden as exc:
            logger.error("Twitter forbidden (possible duplicate or policy violation): %s", exc)
            return False

        except tweepy.errors.Unauthorized:
            logger.error("Twitter credentials expired or revoked")
            return False

        except Exception:
            if attempt == MAX_RETRIES:
                logger.exception("Failed to post to Twitter after %d attempts", MAX_RETRIES)
                return False
            wait = 30 * (2 ** attempt)
            logger.warning("Twitter error, retrying in %ds (attempt %d/%d)", wait, attempt, MAX_RETRIES)
            time.sleep(wait)

    return False

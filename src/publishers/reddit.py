"""Reddit publisher using PRAW with anti-ban protections.

Reddit is the most ban-sensitive platform. Key rules:
- Never post the same link to multiple subreddits simultaneously
- Keep self-promotion well below 10% of total activity
- Rotate subreddits, don't always post to the same one
- Limit to 2 posts/day maximum
- Vary titles to avoid spam filter pattern detection
"""

import logging
import random
import time

import praw
import praw.exceptions

from .. import config
from ..scraper import Article
from ..content import format_reddit_title
from ..safety import can_post, record_post

logger = logging.getLogger(__name__)

MAX_RETRIES = 2


def is_configured() -> bool:
    return all([
        config.REDDIT_CLIENT_ID,
        config.REDDIT_CLIENT_SECRET,
        config.REDDIT_USERNAME,
        config.REDDIT_PASSWORD,
    ])


def _get_subreddits() -> list[str]:
    """Parse comma-separated subreddit list and pick one randomly."""
    raw = config.REDDIT_SUBREDDITS
    subs = [s.strip() for s in raw.split(",") if s.strip()]
    return subs if subs else ["artificial"]


def validate_credentials() -> tuple[bool, str]:
    """Verify Reddit credentials are still valid."""
    if not is_configured():
        return False, "Not configured"
    try:
        reddit = praw.Reddit(
            client_id=config.REDDIT_CLIENT_ID,
            client_secret=config.REDDIT_CLIENT_SECRET,
            username=config.REDDIT_USERNAME,
            password=config.REDDIT_PASSWORD,
            user_agent="dibi8-auto-publisher/2.0",
        )
        user = reddit.user.me()
        if user:
            karma = user.link_karma + user.comment_karma
            return True, f"Authenticated as u/{user.name} (karma: {karma})"
        return False, "Could not verify identity"
    except Exception as exc:
        return False, f"Validation error: {exc}"


def publish(article: Article) -> bool:
    """Post an article link to a random subreddit with safety checks."""
    if not is_configured():
        logger.warning("Reddit not configured, skipping")
        return False

    allowed, reason = can_post("reddit")
    if not allowed:
        logger.info("Reddit rate limit: %s", reason)
        return False

    subreddits = _get_subreddits()
    target_sub = random.choice(subreddits)
    title = format_reddit_title(article)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            reddit = praw.Reddit(
                client_id=config.REDDIT_CLIENT_ID,
                client_secret=config.REDDIT_CLIENT_SECRET,
                username=config.REDDIT_USERNAME,
                password=config.REDDIT_PASSWORD,
                user_agent="dibi8-auto-publisher/2.0",
            )

            subreddit = reddit.subreddit(target_sub)

            # Check if the URL was already submitted to this subreddit
            for submission in subreddit.search(f"url:{article.url}", limit=1):
                logger.info("Article already posted to r/%s, skipping", target_sub)
                return False

            subreddit.submit(title=title, url=article.url)
            record_post("reddit")
            logger.info("Successfully posted to Reddit r/%s: %s", target_sub, article.title)
            return True

        except praw.exceptions.RedditAPIException as exc:
            for error in exc.items:
                if error.error_type == "RATELIMIT":
                    wait_match = error.message
                    logger.warning("Reddit rate limited: %s", wait_match)
                    time.sleep(600)
                    continue
                if error.error_type == "ALREADY_SUB":
                    logger.info("Article already submitted to r/%s", target_sub)
                    return False
                logger.error("Reddit API error: %s - %s", error.error_type, error.message)
            if attempt == MAX_RETRIES:
                return False

        except Exception:
            if attempt == MAX_RETRIES:
                logger.exception("Failed to post to Reddit after %d attempts", MAX_RETRIES)
                return False
            wait = 60 * (2 ** attempt)
            logger.warning("Reddit error, retrying in %ds", wait)
            time.sleep(wait)

    return False

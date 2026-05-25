"""Main scheduler with anti-ban protections.

Safety features:
- Startup jitter (0-15 min random delay to avoid exact cron timing)
- Random skip (15% chance to skip a run entirely, looks more human)
- Inter-platform delays (1-5 min between posting to different platforms)
- Per-platform daily caps and minimum intervals
- Token validation before publishing
- Shuffled platform order each run
"""

import logging
import random
import sys

from . import config
from .scraper import get_unpublished_article, save_published
# V2 upgrade 2026-05-25: 移除 linkedin/medium (token 无解) + hashnode (Pro 才能 API),
# 加 devto (海外程序员核心 + 免费 + canonical 友好)
# 2026-05-26: 移除 twitter (Pay-Per-Use $0.20/带URL推, ROI 不划算, 改手动)
from .publishers import facebook, reddit, devto
from .safety import jitter_delay, human_delay

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

PLATFORMS = [
    ("facebook", facebook),
    ("reddit", reddit),
    ("devto", devto),
]


def _validate_all_credentials() -> None:
    """Check all configured platform credentials and warn about expiring tokens."""
    logger.info("--- Credential validation ---")
    for name, publisher in PLATFORMS:
        if not publisher.is_configured():
            continue
        valid, msg = publisher.validate_credentials()
        if valid:
            logger.info("  %s: %s", name, msg)
        else:
            logger.warning("  %s: %s", name, msg)


def run() -> None:
    """Run one publish cycle with all anti-ban protections."""
    logger.info("=== Starting publish cycle ===")

    # 1. Random startup jitter to avoid posting at exact cron times
    if config.STARTUP_JITTER_MAX > 0:
        jitter_delay()

    # 2. Random skip: ~15% chance to skip this run entirely (looks more human)
    if random.random() < config.RANDOM_SKIP_PROBABILITY:
        logger.info("Random skip triggered (probability %.0f%%). Exiting.", config.RANDOM_SKIP_PROBABILITY * 100)
        return

    # 3. Validate credentials (warn about expired tokens)
    _validate_all_credentials()

    # 4. Shuffle platform order each run (avoids predictable patterns)
    platforms = list(PLATFORMS)
    random.shuffle(platforms)

    results: dict[str, bool] = {}
    skipped: list[str] = []

    for platform_name, publisher in platforms:
        if not publisher.is_configured():
            continue

        article = get_unpublished_article(platform_name)
        if article is None:
            logger.warning("No article available for %s", platform_name)
            continue

        logger.info("Publishing to %s: %s", platform_name, article.title)
        success = publisher.publish(article)
        results[platform_name] = success

        if success:
            save_published(platform_name, article.url)
            logger.info("Published and recorded: %s -> %s", article.url, platform_name)
        elif success is False and platform_name not in results:
            skipped.append(platform_name)

        # 5. Human delay between platforms (1-5 min)
        human_delay(
            config.INTER_PLATFORM_DELAY_MIN,
            config.INTER_PLATFORM_DELAY_MAX,
        )

    # Summary
    logger.info("=== Publish cycle complete ===")
    for platform_name, success in results.items():
        status = "OK" if success else "FAILED/RATE-LIMITED"
        logger.info("  %s: %s", platform_name, status)

    if skipped:
        logger.info("  Skipped (rate limited): %s", ", ".join(skipped))

    if not results:
        logger.info("  No platforms published this cycle.")


if __name__ == "__main__":
    run()

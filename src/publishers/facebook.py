"""Facebook Page publisher using Graph API with anti-ban protections."""

import logging
import time

import requests

from .. import config
from ..scraper import Article
from ..content import format_facebook
from ..safety import can_post, record_post

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


def is_configured() -> bool:
    return all([config.FACEBOOK_PAGE_ID, config.FACEBOOK_ACCESS_TOKEN])


def validate_credentials() -> tuple[bool, str]:
    """Verify Facebook Page token is still valid."""
    if not is_configured():
        return False, "Not configured"
    try:
        url = f"https://graph.facebook.com/v19.0/{config.FACEBOOK_PAGE_ID}"
        resp = requests.get(url, params={"access_token": config.FACEBOOK_ACCESS_TOKEN}, timeout=15)
        if resp.status_code == 200:
            name = resp.json().get("name", "Unknown Page")
            return True, f"Authenticated for page: {name}"
        if resp.status_code == 190 or "expired" in resp.text.lower():
            return False, "EXPIRED: Facebook Page token has expired. Regenerate it."
        return False, f"Facebook API error: {resp.status_code}"
    except Exception as exc:
        return False, f"Validation error: {exc}"


def publish(article: Article) -> bool:
    """Post an article to a Facebook Page with retry logic."""
    if not is_configured():
        logger.warning("Facebook not configured, skipping")
        return False

    allowed, reason = can_post("facebook")
    if not allowed:
        logger.info("Facebook rate limit: %s", reason)
        return False

    message = format_facebook(article)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            url = f"https://graph.facebook.com/v19.0/{config.FACEBOOK_PAGE_ID}/feed"
            payload = {
                "message": message,
                "link": article.url,
                "access_token": config.FACEBOOK_ACCESS_TOKEN,
            }
            resp = requests.post(url, data=payload, timeout=30)

            if resp.status_code == 200:
                record_post("facebook")
                logger.info("Successfully posted to Facebook: %s", article.title)
                return True

            error_data = resp.json().get("error", {})
            error_code = error_data.get("code", 0)

            # Token expired
            if error_code in (190, 102):
                logger.error("Facebook token expired. Please regenerate.")
                return False

            # Rate limited
            if error_code in (4, 32, 613):
                wait = 60 * (2 ** attempt)
                logger.warning("Facebook rate limited, waiting %ds", wait)
                time.sleep(wait)
                continue

            # Spam detected
            if error_code == 368:
                logger.error("Facebook flagged post as spam. Stopping.")
                return False

            resp.raise_for_status()

        except Exception:
            if attempt == MAX_RETRIES:
                logger.exception("Failed to post to Facebook after %d attempts", MAX_RETRIES)
                return False
            wait = 30 * (2 ** attempt)
            logger.warning("Facebook error, retrying in %ds", wait)
            time.sleep(wait)

    return False

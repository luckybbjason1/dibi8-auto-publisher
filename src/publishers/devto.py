"""Dev.to publisher using Forem REST API with anti-ban protections.

V2 upgrade 2026-05-25: 加入 Tribe 体系 — dev.to 是 dibi8 海外程序员受众核心平台。

API docs: https://developers.forem.com/api/v1#tag/articles/operation/createArticle
Rate limit: 30 req/min (友好)
关键点:
- canonical_url 必填 — 告诉 Google 原文在 dibi8 (防 SEO duplicate content)
- tags 最多 4 个, lowercase, no hyphens
- published=true 直接发布 (false 是 draft)
"""

import logging
import time

import requests

from .. import config
from ..scraper import Article
from ..content import format_devto_markdown, normalize_devto_tags
from ..safety import can_post, record_post

logger = logging.getLogger(__name__)

API_URL = "https://dev.to/api/articles"
MAX_RETRIES = 3


def is_configured() -> bool:
    return bool(config.DEVTO_API_KEY)


def validate_credentials() -> tuple[bool, str]:
    """Verify Dev.to API key is still valid."""
    if not is_configured():
        return False, "Not configured"
    try:
        headers = {"api-key": config.DEVTO_API_KEY}
        resp = requests.get("https://dev.to/api/users/me", headers=headers, timeout=15)
        if resp.status_code == 200:
            user = resp.json()
            return True, f"Authenticated as @{user.get('username', 'unknown')}"
        if resp.status_code == 401:
            return False, "EXPIRED/INVALID: Dev.to API key unauthorized"
        return False, f"Validation error: HTTP {resp.status_code}"
    except Exception as exc:
        return False, f"Validation error: {exc}"


def publish(article: Article) -> bool:
    """Publish article to Dev.to with canonical_url back to dibi8."""
    if not is_configured():
        logger.warning("Dev.to not configured, skipping")
        return False

    allowed, reason = can_post("devto")
    if not allowed:
        logger.info("Dev.to rate limit: %s", reason)
        return False

    body_markdown = format_devto_markdown(article)
    tags = normalize_devto_tags(article.tags)

    payload = {
        "article": {
            "title": article.title[:128],  # dev.to 标题 max 128
            "body_markdown": body_markdown,
            "tags": tags[:4],              # max 4 tags
            "canonical_url": article.url,  # ← SEO 关键: 原文在 dibi8
            "published": True,
            "description": article.description[:140] if article.description else "",
        }
    }

    headers = {
        "api-key": config.DEVTO_API_KEY,
        "Content-Type": "application/json",
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(API_URL, json=payload, headers=headers, timeout=30)
            if resp.status_code in (200, 201):
                record_post("devto")
                published_url = resp.json().get("url", "")
                logger.info("Successfully posted to Dev.to: %s → %s", article.title, published_url)
                return True

            if resp.status_code == 429:
                wait = 60 * (2 ** attempt)
                logger.warning("Dev.to rate limited, waiting %ds (attempt %d/%d)", wait, attempt, MAX_RETRIES)
                time.sleep(wait)
                continue

            if resp.status_code == 401:
                logger.error("Dev.to API key expired/revoked")
                return False

            logger.error("Dev.to publish failed: HTTP %d %s", resp.status_code, resp.text[:300])
            if attempt == MAX_RETRIES:
                return False

        except requests.RequestException as exc:
            if attempt == MAX_RETRIES:
                logger.exception("Failed to post to Dev.to after %d attempts", MAX_RETRIES)
                return False
            wait = 30 * (2 ** attempt)
            logger.warning("Dev.to network error %s, retrying in %ds (attempt %d/%d)", exc, wait, attempt, MAX_RETRIES)
            time.sleep(wait)

    return False

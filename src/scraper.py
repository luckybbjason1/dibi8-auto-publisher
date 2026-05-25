"""Scrape articles from dibi8.com via RSS feed and page metadata."""

import xml.etree.ElementTree as ET
import random
import json
import re
import logging
from dataclasses import dataclass
from typing import Optional

import requests
from bs4 import BeautifulSoup

from . import config

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
]


def _get_session() -> requests.Session:
    """Create a requests session with a random User-Agent."""
    session = requests.Session()
    session.headers.update({"User-Agent": random.choice(USER_AGENTS)})
    return session


@dataclass
class Article:
    title: str
    url: str
    description: str
    og_image: str
    pub_date: str
    category: str
    tags: list[str]


def fetch_rss_articles() -> list[dict]:
    """Fetch all articles from the dibi8.com RSS feed."""
    logger.info("Fetching RSS feed from %s", config.RSS_FEED_URL)
    session = _get_session()
    resp = session.get(config.RSS_FEED_URL, timeout=30)
    resp.raise_for_status()

    root = ET.fromstring(resp.text)
    articles = []
    for item in root.findall(".//item"):
        title_el = item.find("title")
        link_el = item.find("link")
        pub_date_el = item.find("pubDate")
        if title_el is None or link_el is None:
            continue
        articles.append({
            "title": title_el.text or "",
            "url": link_el.text or "",
            "pub_date": pub_date_el.text if pub_date_el is not None else "",
        })

    logger.info("Found %d articles in RSS feed", len(articles))
    return articles


def scrape_article_meta(url: str) -> dict:
    """Scrape og:description and og:image from an article page."""
    logger.info("Scraping metadata from %s", url)
    session = _get_session()
    try:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("Failed to fetch %s: %s", url, exc)
        return {"description": "", "og_image": "", "category": "", "tags": []}

    soup = BeautifulSoup(resp.text, "lxml")

    og_desc = ""
    meta_desc = soup.find("meta", attrs={"property": "og:description"})
    if meta_desc and meta_desc.get("content"):
        og_desc = meta_desc["content"]
    if not og_desc:
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            og_desc = meta_desc["content"]

    og_image = ""
    meta_img = soup.find("meta", attrs={"property": "og:image"})
    if meta_img and meta_img.get("content"):
        og_image = meta_img["content"]

    category = _extract_category(url)
    tags = _extract_tags(soup)

    return {
        "description": og_desc,
        "og_image": og_image,
        "category": category,
        "tags": tags,
    }


def _extract_category(url: str) -> str:
    """Extract category from URL path like /resources/ai-tools/..."""
    match = re.search(r"/(resources|collections)/([^/]+)/", url)
    if match:
        return match.group(2).replace("-", " ").title()
    return "AI Tools"


def _extract_tags(soup: BeautifulSoup) -> list[str]:
    """Extract keywords from meta tags."""
    meta_kw = soup.find("meta", attrs={"name": "keywords"})
    if meta_kw and meta_kw.get("content"):
        return [t.strip() for t in meta_kw["content"].split(",") if t.strip()]
    return []


def load_published(platform: str) -> list[str]:
    """Load list of published article URLs for a platform."""
    try:
        with open(config.PUBLISHED_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get(platform, [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_published(platform: str, url: str) -> None:
    """Mark an article URL as published for a platform."""
    try:
        with open(config.PUBLISHED_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}

    if platform not in data:
        data[platform] = []

    if url not in data[platform]:
        data[platform].append(url)

    with open(config.PUBLISHED_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_unpublished_article(platform: str) -> Optional[Article]:
    """Get a random unpublished article for the given platform.

    Prefers newer articles (weighted random) to keep content fresh.
    """
    all_articles = fetch_rss_articles()
    published = load_published(platform)

    unpublished = [a for a in all_articles if a["url"] not in published]

    if not unpublished:
        logger.info("All articles have been published on %s. Resetting.", platform)
        try:
            with open(config.PUBLISHED_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}
        data[platform] = []
        with open(config.PUBLISHED_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        unpublished = all_articles

    if not unpublished:
        logger.warning("No articles found at all")
        return None

    # Weighted random: newer articles (earlier in list) are more likely to be picked
    weights = list(range(len(unpublished), 0, -1))
    chosen = random.choices(unpublished, weights=weights, k=1)[0]
    meta = scrape_article_meta(chosen["url"])

    return Article(
        title=chosen["title"],
        url=chosen["url"],
        description=meta["description"],
        og_image=meta["og_image"],
        pub_date=chosen["pub_date"],
        category=meta["category"],
        tags=meta["tags"],
    )

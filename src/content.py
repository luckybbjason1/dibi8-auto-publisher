"""Content variation engine: generate platform-specific post variants to avoid spam detection."""

import random
import logging

from .scraper import Article

logger = logging.getLogger(__name__)

# Category-specific hashtag pools
HASHTAG_POOLS = {
    "ai-tools": ["#AI", "#AITools", "#OpenSource", "#DevTools", "#ArtificialIntelligence",
                  "#GenerativeAI", "#TTS", "#StableDiffusion", "#ComfyUI", "#ImageGen"],
    "llm-frameworks": ["#LLM", "#LangChain", "#OpenSource", "#AI", "#MachineLearning",
                        "#NLP", "#GPT", "#FineTuning", "#RAG", "#AIAgents"],
    "dev-utils": ["#DevTools", "#OpenSource", "#Developer", "#Automation", "#CLI",
                  "#Productivity", "#Coding", "#WebScraping", "#SelfHosted", "#Tools"],
    "data-science": ["#DataScience", "#Analytics", "#QuantTrading", "#Python",
                     "#MachineLearning", "#Visualization", "#BigData", "#AI", "#Stats"],
    "collections": ["#AI", "#TechStack", "#OpenSource", "#SelfHosted", "#DevOps",
                    "#AITools", "#Developer", "#Tutorial", "#Guide", "#2026"],
}

# TWITTER_TEMPLATES 移除 2026-05-26 — 走手动发推工作流

# Hook phrases (used by Facebook/Reddit)
HOOKS = [
    "Just discovered this",
    "This is worth a look",
    "Really useful open-source tool",
    "Great resource for developers",
    "Interesting AI project",
    "Check this out",
    "Open source gem",
    "Solid developer tool",
    "Useful for AI projects",
    "Building with AI? Check this",
]

EMOJIS = ["🔥", "🚀", "⚡", "💡", "🛠️", "🤖", "📦", "✨", "🎯", "📌"]

# Facebook / LinkedIn templates (longer format)
LONG_TEMPLATES = [
    "{title}\n\n{description}\n\n👉 {url}\n\n{hashtags}",
    "{hook}\n\n{title}\n\n{description}\n\nRead more: {url}\n\n{hashtags}",
    "{emoji} {title}\n\n{description}\n\nFull guide: {url}\n\n{hashtags}",
    "{description}\n\n{title}\n\n{url}\n\n{hashtags}",
]

LONG_HOOKS = [
    "Sharing a useful open-source resource:",
    "Found a great AI tool worth checking out:",
    "This open-source project caught my attention:",
    "For developers working with AI:",
    "Useful resource for the AI community:",
    "Great open-source find:",
]

# Medium intro paragraph templates
MEDIUM_INTROS = [
    "If you're working with AI tools, this one is worth your time.",
    "The open-source AI ecosystem keeps growing. Here's a tool that stands out.",
    "Looking for the right tool for your AI workflow? This might be it.",
    "Open-source projects like this make AI development more accessible.",
    "Here's a practical guide to a tool that's gaining traction in the dev community.",
]

# Reddit title prefixes (to make it less spammy)
REDDIT_PREFIXES = [
    "",  # no prefix
    "[Resource] ",
    "[Open Source] ",
    "[Guide] ",
    "[Tool] ",
]


def _get_category_from_url(url: str) -> str:
    """Extract category slug from URL."""
    for cat in HASHTAG_POOLS:
        if f"/{cat}/" in url or url.startswith(f"https://dibi8.com/{cat}"):
            return cat
    if "/collections/" in url:
        return "collections"
    return "ai-tools"


def pick_hashtags(article: Article, count: int = 3) -> str:
    """Pick random hashtags based on article category."""
    category = _get_category_from_url(article.url)
    pool = HASHTAG_POOLS.get(category, HASHTAG_POOLS["ai-tools"])
    selected = random.sample(pool, min(count, len(pool)))
    return " ".join(selected)


# format_twitter() 移除 2026-05-26 — Twitter Pay-Per-Use ROI 不划算, 改手动发推


def format_facebook(article: Article) -> str:
    """Generate a varied Facebook post."""
    template = random.choice(LONG_TEMPLATES)
    hashtags = pick_hashtags(article, count=random.randint(3, 5))
    hook = random.choice(LONG_HOOKS)
    emoji = random.choice(EMOJIS)

    return template.format(
        title=article.title,
        description=article.description[:400],
        url=article.url,
        hashtags=hashtags,
        hook=hook,
        emoji=emoji,
    )


# V2 upgrade 2026-05-25: format_linkedin / format_medium_html / format_hashnode 都已移除 (平台死)
# 替换为 format_devto_markdown


# Dev.to intro 模板 (markdown, 开发者友好语调)
DEVTO_INTROS = [
    "Sharing an open-source tool I came across in the dibi8 directory:",
    "Found this in the open-source AI tooling space — worth a look:",
    "Adding to my watchlist of AI dev tools. Quick rundown:",
    "Open-source AI ecosystem keeps shipping interesting things. Today's pick:",
    "Curated find from dibi8.com — open-source, production-relevant:",
]


def format_devto_markdown(article: Article) -> str:
    """Generate Dev.to article markdown body.

    Dev.to 受众 = 开发者 → 技术语调, 含 GitHub repo 引用 (如有),
    canonical_url 在 frontmatter 之外 (API 层处理)。
    """
    intro = random.choice(DEVTO_INTROS)
    desc = article.description or ""

    body = f"""{intro}

## {article.title}

{desc}

**Read the full breakdown on dibi8:** [{article.url}]({article.url})

---

> This is a curated highlight from [dibi8.com](https://dibi8.com) — open-source AI tools directory, hand-edited, 4 languages. The full article (with comparisons, setup guide, and code samples) lives on dibi8."""
    return body


def normalize_devto_tags(tags: list[str]) -> list[str]:
    """Dev.to tag rules: lowercase, no hyphens, alphanumeric only, max 4."""
    out = []
    for t in tags:
        if not t:
            continue
        # 移除空格 / 连字符 / 非字母数字
        clean = "".join(c for c in t.lower() if c.isalnum())
        if clean and len(clean) <= 30 and clean not in out:
            out.append(clean)
        if len(out) >= 4:
            break
    return out or ["ai", "opensource", "devtools"]


# Hashnode formatters 已移除 (2026-05-25): API 转 Pro plan,免费版死。


def format_reddit_title(article: Article) -> str:
    """Generate a varied Reddit submission title."""
    prefix = random.choice(REDDIT_PREFIXES)
    return f"{prefix}{article.title}"

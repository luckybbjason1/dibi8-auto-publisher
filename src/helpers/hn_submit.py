"""Hacker News 半自动提交助手 (V2 upgrade 2026-05-25)

HN 没有官方提交 API (反 spam 设计)。本助手不真发,而是:
1. 从 dibi8 RSS 选 top 3 HN-friendly 文章 (按主题类型 + 内容深度)
2. 为每篇生成 3 个候选标题 (按 HN 最佳实践: factual / specific / no clickbait)
3. 生成 1-click submit URLs (HN 自动 prefill)
4. 输出 markdown 推荐文件 → 主人查 GitHub repo,点 1 个 URL 即可在浏览器一键提交

最佳提交时间: US Pacific 6-8am 周二-周四 (= UTC 14:00-16:00)
GitHub Action 应该在 UTC 14:00 周二跑本 helper。

参考: https://news.ycombinator.com/newsguidelines.html
"""

import logging
import random
import re
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

from ..scraper import fetch_rss_articles, scrape_article_meta, _get_session  # noqa: F401

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "data"
HN_SUBMIT_URL = "https://news.ycombinator.com/submitlink"


# HN 标题模式 (factual + specific + 数字 + 不 clickbait)
TITLE_PATTERNS = [
    "{title}",  # 原标题, dibi8 文章标题本来就 HN-friendly
    "Show HN: {title}",  # 仅当 dibi8 article 是 launch / new tool 时
    "{base_title} ({stars}★ on GitHub)",  # 数字增强
    "{base_title}: A {category} comparison",
    "Why {keyword} matters in 2026: {base_title}",
]


def _is_hn_friendly(title: str, url: str) -> bool:
    """判断文章主题是否适合 HN (技术深度 / 开源 / 新工具 / 对比分析)。"""
    hn_keywords = [
        "open-source", "open source", "framework", "agent", "llm", "mcp",
        "rust", "go ", "python", "comparison", "vs ", "benchmark",
        "self-host", "production", "stack", "guide", "tutorial",
        "deep-dive", "deep dive", "architecture", "memory", "skills",
    ]
    title_lower = title.lower()
    return any(kw in title_lower for kw in hn_keywords)


def _generate_title_variants(article_title: str, stars: int, category: str) -> list[str]:
    """为 1 篇文章生成 3 个 HN 候选标题。"""
    base = re.sub(r"\s*--\s*", " — ", article_title).strip()
    base = re.sub(r"\s+", " ", base)

    # 提取 "base title" (去掉副标题)
    base_short = base.split(":")[0] if ":" in base else base
    base_short = base_short.split("—")[0].strip() if "—" in base_short else base_short.strip()

    keyword = ""
    for kw in ["LLM", "Agent", "MCP", "RAG", "AI Coding"]:
        if kw.lower() in base.lower():
            keyword = kw
            break

    variants = []
    # 1. 原标题
    variants.append(base[:80])

    # 2. Show HN (仅当主题适合)
    if "show " not in base.lower() and ("launch" in base.lower() or "new " in base.lower() or "build" in base.lower()):
        variants.append(f"Show HN: {base_short[:70]}")
    elif stars > 50000:
        variants.append(f"{base_short[:60]} ({stars:,}★ on GitHub)")
    else:
        variants.append(f"{base_short[:80]}")

    # 3. 关键词强化
    if keyword:
        variants.append(f"Why {keyword.lower()} matters in 2026: {base_short[:60]}")
    else:
        cat_clean = category.replace("-", " ").title() if category else "Open-Source AI"
        variants.append(f"{base_short[:60]}: A {cat_clean} comparison")

    return variants


def _generate_submit_url(title: str, url: str) -> str:
    """生成 HN 1-click prefill submit URL。"""
    return f"{HN_SUBMIT_URL}?u={urllib.parse.quote(url, safe='')}&t={urllib.parse.quote(title)}"


def select_top_candidates(n: int = 3) -> list[dict]:
    """从 RSS 选 N 篇 HN-friendly 文章作为本周提交候选。"""
    articles = fetch_rss_articles()
    if not articles:
        logger.warning("No articles from RSS, skipping HN recommendation")
        return []

    # 过滤 HN-friendly (按标题关键词)
    friendly = [a for a in articles if _is_hn_friendly(a["title"], a["url"])]
    # fallback: 没匹配就用最新的
    if not friendly:
        friendly = articles[:n]

    # 取前 N 篇 (RSS 已按时间倒序)
    selected = friendly[:n]

    candidates = []
    for art in selected:
        meta = scrape_article_meta(art["url"])
        stars = 0
        # 试从 meta scrape stars (dibi8 meta 含 GitHub 星数)
        # 简化: 不强求, 默认 0
        category = meta.get("category", "")

        variants = _generate_title_variants(art["title"], stars, category)
        candidates.append({
            "article_title": art["title"],
            "article_url": art["url"],
            "description": meta.get("description", ""),
            "category": category,
            "title_variants": variants,
            "submit_urls": [_generate_submit_url(v, art["url"]) for v in variants],
        })

    return candidates


def generate_recommendation_md(candidates: list[dict]) -> str:
    """生成 HN 推荐 markdown 文件内容。"""
    date_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    lines = [
        f"# Hacker News 提交推荐 — {date_iso}",
        "",
        "> 自动从 dibi8 RSS 选出本周 HN-friendly 文章 + 3 个候选标题 + 1-click 提交 URL",
        "> 主人查看本文件 → 选 1 篇 → 点 1 个 submit URL → 浏览器一键提交",
        "",
        "## ⏰ 最佳提交时间",
        "",
        "**US Pacific 6-8am 周二-周四** (= UTC 14:00-16:00, JST 23:00-01:00)",
        "",
        "前 1 小时 vote 数决定能否进 HN 第一页, 错过黄金窗口 = 第二页死亡。",
        "",
        "## HN 提交礼仪 (重要)",
        "",
        "- ❌ 不要请朋友/亲戚帮 upvote (HN 反作弊会检测同 IP / 同时间段 upvote 集中)",
        "- ❌ 提交后不要立刻去其他社交平台同步推 (会被识别为 cross-platform spam)",
        "- ✅ 提交后专心在 HN 评论里回答问题 (前 30 min 评论 = 显著加分)",
        "- ✅ Title 要 factual,不 clickbait",
        "- ✅ 1 周内不要重复提交相似主题",
        "",
        "---",
        "",
    ]

    if not candidates:
        lines.append("⚠️ 本周无 HN-friendly 候选 (RSS 抓取失败或文章主题不匹配)。")
        return "\n".join(lines)

    for i, c in enumerate(candidates, 1):
        lines.append(f"## 候选 {i}: {c['article_title']}")
        lines.append("")
        lines.append(f"**dibi8 原文**: {c['article_url']}")
        lines.append("")
        if c['description']:
            lines.append(f"**摘要**: {c['description'][:300]}")
            lines.append("")
        if c['category']:
            lines.append(f"**Category**: `{c['category']}`")
            lines.append("")
        lines.append("### 3 个候选标题 (点 URL 一键提交)")
        lines.append("")
        for j, (title, sub_url) in enumerate(zip(c['title_variants'], c['submit_urls']), 1):
            lines.append(f"**{j}.** {title}")
            lines.append("")
            lines.append(f"→ [一键提交]({sub_url})")
            lines.append("")
        lines.append("---")
        lines.append("")

    lines.append("")
    lines.append(f"_本文件由 src/helpers/hn_submit.py 在 {date_iso} 自动生成_")
    return "\n".join(lines)


def run() -> Path:
    """生成本周 HN 推荐 markdown 并写入 data/hn-recommendations-YYYY-MM-DD.md。"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    date_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    output_path = OUTPUT_DIR / f"hn-recommendations-{date_iso}.md"

    candidates = select_top_candidates(n=3)
    md = generate_recommendation_md(candidates)
    output_path.write_text(md, encoding="utf-8")
    logger.info("HN recommendations written to %s (%d candidates)", output_path, len(candidates))
    return output_path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    p = run()
    print(f"\n✓ HN recommendations: {p}")

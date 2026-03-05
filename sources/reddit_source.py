import logging
import time
from typing import TypedDict

import feedparser
import requests

logger = logging.getLogger(__name__)

SUBREDDITS = ["ClaudeAI", "ChatGPT", "LocalLLaMA", "webdev"]
KEYWORDS = [
    "token limit",
    "api cost",
    "context window",
    "claude expensive",
    "gpt bill",
    "token waste",
    "token usage",
    "tokens",
]
USER_AGENT = "TokalatorBot/1.0 (token management research; contact: tokalator.dev)"


class Opportunity(TypedDict):
    id: str
    source: str
    subreddit: str
    title: str
    url: str
    body: str
    author: str
    matched_keyword: str
    created_utc: str


def fetch_opportunities() -> list[Opportunity]:
    results: list[Opportunity] = []
    for subreddit in SUBREDDITS:
        try:
            posts = _fetch_subreddit(subreddit)
            results.extend(posts)
            time.sleep(1)
        except Exception as e:
            logger.error("Failed to fetch r/%s: %s", subreddit, e)
    logger.info("Reddit: found %d opportunities across %d subreddits", len(results), len(SUBREDDITS))
    return results


def _fetch_subreddit(subreddit: str) -> list[Opportunity]:
    url = f"https://www.reddit.com/r/{subreddit}/new/.rss?limit=25"
    # feedparser doesn't support custom headers directly; use requests to fetch raw XML
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=15)
    response.raise_for_status()
    feed = feedparser.parse(response.text)

    opportunities = []
    for entry in feed.entries:
        text = f"{entry.get('title', '')} {entry.get('summary', '')}".lower()
        matched = _match_keyword(text)
        if not matched:
            continue

        post_id = _extract_post_id(entry.get("id", entry.get("link", "")))
        if not post_id:
            continue

        body = _strip_html(entry.get("summary", ""))[:500]
        opportunities.append(
            Opportunity(
                id=f"reddit_{post_id}",
                source="reddit",
                subreddit=f"r/{subreddit}",
                title=entry.get("title", "(no title)"),
                url=entry.get("link", ""),
                body=body,
                author=entry.get("author", "unknown"),
                matched_keyword=matched,
                created_utc=entry.get("published", ""),
            )
        )
    return opportunities


def _match_keyword(text: str) -> str:
    for kw in KEYWORDS:
        if kw in text:
            return kw
    return ""


def _extract_post_id(entry_id: str) -> str:
    # Reddit RSS <id> looks like: https://www.reddit.com/r/ClaudeAI/comments/abc123/...
    parts = entry_id.rstrip("/").split("/")
    try:
        comments_idx = parts.index("comments")
        return f"t3_{parts[comments_idx + 1]}"
    except (ValueError, IndexError):
        return ""


def _strip_html(html: str) -> str:
    import re
    return re.sub(r"<[^>]+>", "", html).strip()

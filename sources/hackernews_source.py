import logging
import time
from datetime import datetime, timezone, timedelta
from typing import TypedDict

import requests

logger = logging.getLogger(__name__)

ALGOLIA_URL = "https://hn.algolia.com/api/v1/search_by_date"
QUERIES = [
    "token limit OR context window OR token cost",
    "LLM cost OR Claude expensive OR API billing OR GPT expensive",
]
MIN_POINTS = 2
LOOKBACK_HOURS = 7  # Slightly wider than the 6h cron to catch boundary items


class Opportunity(TypedDict):
    id: str
    source: str
    subreddit: str  # empty for HN
    title: str
    url: str
    body: str
    author: str
    matched_keyword: str
    created_utc: str


def fetch_opportunities() -> list[Opportunity]:
    since_ts = int((datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)).timestamp())
    seen_ids: set[str] = set()
    results: list[Opportunity] = []

    for query in QUERIES:
        try:
            items = _fetch_query(query, since_ts)
            for item in items:
                if item["id"] not in seen_ids:
                    seen_ids.add(item["id"])
                    results.append(item)
            time.sleep(0.5)
        except Exception as e:
            logger.error("HN query failed (%r): %s", query, e)

    logger.info("HN: found %d opportunities", len(results))
    return results


def _fetch_query(query: str, since_ts: int) -> list[Opportunity]:
    params = {
        "query": query,
        "tags": "story,comment",
        "numericFilters": f"created_at_i>{since_ts}",
        "hitsPerPage": 20,
    }
    resp = requests.get(ALGOLIA_URL, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    results = []
    for hit in data.get("hits", []):
        points = hit.get("points") or hit.get("story_points") or 0
        if points < MIN_POINTS:
            continue

        obj_id = str(hit.get("objectID", ""))
        if not obj_id:
            continue

        title = hit.get("title") or hit.get("story_title") or "(HN comment)"
        body = (hit.get("story_text") or hit.get("comment_text") or "")[:500]
        url = hit.get("url") or f"https://news.ycombinator.com/item?id={obj_id}"
        created = hit.get("created_at", "")

        results.append(
            Opportunity(
                id=f"hn_{obj_id}",
                source="hackernews",
                subreddit="",
                title=title,
                url=url,
                body=body,
                author=hit.get("author", "unknown"),
                matched_keyword=query.split(" OR ")[0],
                created_utc=created,
            )
        )
    return results

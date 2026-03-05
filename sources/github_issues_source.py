import logging
from datetime import datetime, timezone, timedelta
from typing import TypedDict

import requests

logger = logging.getLogger(__name__)

GITHUB_SEARCH_URL = "https://api.github.com/search/issues"
TARGET_REPOS = [
    "anthropics/claude-code",
    "getcursor/cursor",
    "microsoft/vscode",
]
KEYWORDS = ["token", "cost", "expensive", "context window", "billing", "token limit"]
LOOKBACK_HOURS = 25  # Issues are slower-moving; check last 25h


class Opportunity(TypedDict):
    id: str
    source: str
    subreddit: str  # repo name for GitHub
    title: str
    url: str
    body: str
    author: str
    matched_keyword: str
    created_utc: str


def fetch_opportunities(github_token: str) -> list[Opportunity]:
    since = (datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    results: list[Opportunity] = []
    seen_ids: set[str] = set()

    for repo in TARGET_REPOS:
        for keyword in KEYWORDS:
            try:
                items = _search_issues(repo, keyword, since, headers)
                for item in items:
                    if item["id"] not in seen_ids:
                        seen_ids.add(item["id"])
                        results.append(item)
            except requests.HTTPError as e:
                if e.response is not None and e.response.status_code == 404:
                    logger.warning("Repo not found or private, skipping: %s", repo)
                    break  # Skip remaining keywords for this repo
                logger.error("GitHub API error for %s/%s: %s", repo, keyword, e)
            except Exception as e:
                logger.error("GitHub fetch failed for %s/%s: %s", repo, keyword, e)

    logger.info("GitHub: found %d opportunities", len(results))
    return results


def _search_issues(
    repo: str, keyword: str, since: str, headers: dict
) -> list[Opportunity]:
    query = f"{keyword} repo:{repo} is:issue is:open created:>{since}"
    params = {"q": query, "per_page": 10, "sort": "created", "order": "desc"}
    resp = requests.get(GITHUB_SEARCH_URL, params=params, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    results = []
    owner, repo_name = repo.split("/", 1)
    for item in data.get("items", []):
        number = item.get("number", 0)
        body = (item.get("body") or "")[:600]
        results.append(
            Opportunity(
                id=f"github_{owner}_{repo_name}_{number}",
                source="github",
                subreddit=repo,
                title=item.get("title", "(no title)"),
                url=item.get("html_url", ""),
                body=body,
                author=item.get("user", {}).get("login", "unknown"),
                matched_keyword=keyword,
                created_utc=item.get("created_at", ""),
            )
        )
    return results

"""
Tokalator Listening Agent
Monitors Reddit, HN, and GitHub Issues for token/cost pain points,
generates Claude draft replies, and sends Telegram notifications.

Usage:
    python -m agents.listening_agent

Environment variables required:
    ANTHROPIC_API_KEY    — Claude API key
    TELEGRAM_BOT_TOKEN   — Telegram bot token (from @BotFather)
    TELEGRAM_CHAT_ID     — Your Telegram chat/user ID
    GITHUB_TOKEN         — GitHub personal access token

Optional:
    DRY_RUN=true         — Print to stdout instead of sending Telegrams
"""

import asyncio
import logging
import os
import sys
from dataclasses import dataclass, field

from dotenv import load_dotenv

# Load .env for local development (no-op in GitHub Actions where env vars are set directly)
load_dotenv()

from sources import reddit_source, hackernews_source, github_issues_source
from processors.deduplicator import Deduplicator
from processors.reply_generator import generate_draft_reply
from notifiers.telegram_notifier import send_opportunity, send_run_summary

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

MAX_PER_RUN = 5  # Cap opportunities per run to control Claude API cost


@dataclass
class RunConfig:
    anthropic_api_key: str
    telegram_bot_token: str
    telegram_chat_id: str
    github_token: str
    dry_run: bool = False

    @classmethod
    def from_env(cls) -> "RunConfig":
        missing = []
        for var in ["ANTHROPIC_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "GITHUB_TOKEN"]:
            if not os.environ.get(var):
                missing.append(var)
        if missing:
            logger.error("Missing required environment variables: %s", ", ".join(missing))
            sys.exit(1)

        return cls(
            anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
            telegram_bot_token=os.environ["TELEGRAM_BOT_TOKEN"],
            telegram_chat_id=os.environ["TELEGRAM_CHAT_ID"],
            github_token=os.environ["GITHUB_TOKEN"],
            dry_run=os.environ.get("DRY_RUN", "false").lower() == "true",
        )


@dataclass
class RunStats:
    source_counts: dict = field(default_factory=lambda: {"reddit": 0, "hackernews": 0, "github": 0})
    sent: int = 0


async def main() -> None:
    config = RunConfig.from_env()

    if config.dry_run:
        logger.info("=== DRY RUN MODE — no Telegram messages will be sent ===")

    dedup = Deduplicator()
    dedup.load()

    # Fetch from all sources; failures are isolated per-source
    all_opportunities: list[dict] = []
    stats = RunStats()

    logger.info("Fetching from Reddit...")
    try:
        reddit_opps = reddit_source.fetch_opportunities()
        all_opportunities.extend(reddit_opps)
        stats.source_counts["reddit"] = len(reddit_opps)
    except Exception as e:
        logger.error("Reddit source failed entirely: %s", e)

    logger.info("Fetching from Hacker News...")
    try:
        hn_opps = hackernews_source.fetch_opportunities()
        all_opportunities.extend(hn_opps)
        stats.source_counts["hackernews"] = len(hn_opps)
    except Exception as e:
        logger.error("HN source failed entirely: %s", e)

    logger.info("Fetching from GitHub Issues...")
    try:
        gh_opps = github_issues_source.fetch_opportunities(config.github_token)
        all_opportunities.extend(gh_opps)
        stats.source_counts["github"] = len(gh_opps)
    except Exception as e:
        logger.error("GitHub source failed entirely: %s", e)

    logger.info(
        "Total raw opportunities: %d (Reddit: %d, HN: %d, GitHub: %d)",
        len(all_opportunities),
        stats.source_counts["reddit"],
        stats.source_counts["hackernews"],
        stats.source_counts["github"],
    )

    # Filter to only new opportunities
    new_opportunities = [opp for opp in all_opportunities if not dedup.is_seen(opp["id"])]
    logger.info("%d new (unseen) opportunities after dedup", len(new_opportunities))

    # Cap per run
    if len(new_opportunities) > MAX_PER_RUN:
        logger.info("Capping to %d opportunities (was %d)", MAX_PER_RUN, len(new_opportunities))
        new_opportunities = new_opportunities[:MAX_PER_RUN]

    # Process each opportunity
    for opp in new_opportunities:
        logger.info("Processing: [%s] %s", opp["source"], opp["title"][:80])

        draft = generate_draft_reply(opp, config.anthropic_api_key)

        if config.dry_run:
            _print_dry_run(opp, draft)
        else:
            sent = await send_opportunity(
                config.telegram_bot_token,
                config.telegram_chat_id,
                opp,
                draft,
            )
            if sent:
                stats.sent += 1

        # Always mark as seen (even in dry-run) so we don't re-process on the next real run
        # Exception: in dry-run mode, don't mark so we can re-test with same posts
        if not config.dry_run:
            dedup.mark_seen(opp["id"])

    # Send run summary
    if not config.dry_run:
        await send_run_summary(
            config.telegram_bot_token,
            config.telegram_chat_id,
            stats.source_counts,
            stats.sent,
        )
        dedup.save()

    logger.info("Run complete. Sent: %d/%d new opportunities.", stats.sent, len(new_opportunities))


def _print_dry_run(opp: dict, draft: str) -> None:
    separator = "=" * 60
    print(f"\n{separator}")
    print(f"[DRY RUN] Source: {opp['source']} | {opp.get('subreddit', '')}")
    print(f"Title:   {opp['title']}")
    print(f"Author:  {opp['author']}")
    print(f"URL:     {opp['url']}")
    print(f"Keyword: {opp['matched_keyword']}")
    print(f"\nPost excerpt:\n{opp['body'][:300]}")
    print(f"\nDraft reply:\n{draft}")
    print(separator)


if __name__ == "__main__":
    asyncio.run(main())

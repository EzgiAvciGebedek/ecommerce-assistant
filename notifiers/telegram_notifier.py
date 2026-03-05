import asyncio
import html
import logging

from telegram import Bot
from telegram.constants import ParseMode

logger = logging.getLogger(__name__)

TELEGRAM_MAX_CHARS = 4096

SOURCE_EMOJIS = {
    "reddit": "🟠",
    "hackernews": "🟡",
    "github": "⚫",
}


async def send_opportunity(
    bot_token: str,
    chat_id: str,
    opportunity: dict,
    draft_reply: str,
) -> bool:
    source = opportunity.get("source", "unknown")
    source_emoji = SOURCE_EMOJIS.get(source, "🔵")
    subreddit = opportunity.get("subreddit", "")
    title = opportunity.get("title", "(no title)")
    author = opportunity.get("author", "unknown")
    url = opportunity.get("url", "")
    body = opportunity.get("body", "")
    keyword = opportunity.get("matched_keyword", "")
    created_utc = opportunity.get("created_utc", "")

    message = _build_message(
        source_emoji=source_emoji,
        source=source.upper(),
        subreddit=subreddit,
        title=title,
        author=author,
        keyword=keyword,
        body=body,
        url=url,
        draft_reply=draft_reply,
        created_utc=created_utc,
    )

    try:
        bot = Bot(token=bot_token)
        await bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
        logger.info("Sent Telegram notification for: %s", title[:60])
        return True
    except Exception as e:
        logger.error("Telegram send failed for %r: %s", title[:60], e)
        return False


async def send_run_summary(
    bot_token: str,
    chat_id: str,
    counts: dict,
    total_sent: int,
) -> None:
    reddit_count = counts.get("reddit", 0)
    hn_count = counts.get("hackernews", 0)
    github_count = counts.get("github", 0)

    if total_sent == 0:
        text = (
            "✅ <b>Listening Agent ran</b>\n\n"
            f"Reddit: {reddit_count} · HN: {hn_count} · GitHub: {github_count}\n"
            "No new opportunities this cycle."
        )
    else:
        text = (
            f"✅ <b>Run complete — {total_sent} new opportunit{'y' if total_sent == 1 else 'ies'} sent</b>\n\n"
            f"🟠 Reddit: {reddit_count} · 🟡 HN: {hn_count} · ⚫ GitHub: {github_count}"
        )

    try:
        bot = Bot(token=bot_token)
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        logger.error("Failed to send run summary: %s", e)


def _build_message(
    source_emoji: str,
    source: str,
    subreddit: str,
    title: str,
    author: str,
    keyword: str,
    body: str,
    url: str,
    draft_reply: str,
    created_utc: str,
) -> str:
    context_label = subreddit if subreddit else source

    # Escape HTML special chars for user-generated content
    esc_title = html.escape(title)
    esc_author = html.escape(author)
    esc_keyword = html.escape(keyword)
    esc_context = html.escape(context_label)
    esc_draft = html.escape(draft_reply)
    esc_created = html.escape(created_utc[:19] if created_utc else "")

    # Body gets truncated dynamically to fit message limit
    separator = "━" * 20
    header = (
        f"🎯 <b>New Opportunity — {source_emoji} {esc_context}</b>\n\n"
        f"📌 <b>{esc_title}</b>\n"
        f"👤 {esc_author} · 🔑 \"{esc_keyword}\"\n\n"
    )
    footer = (
        f"\n\n{separator}\n"
        f"✍️ <b>DRAFT REPLY (copy-paste ready):</b>\n\n"
        f"{esc_draft}\n\n"
        f"{separator}\n"
        f"🕐 Detected: {esc_created} UTC"
    )
    link_line = f"🔗 <a href=\"{url}\">View Original Post</a>\n"

    # Calculate how many body chars we can fit
    body_prefix = "<b>Post excerpt:</b>\n<i>"
    body_suffix = "</i>\n\n"
    fixed_len = len(header) + len(body_prefix) + len(body_suffix) + len(link_line) + len(footer)
    available = TELEGRAM_MAX_CHARS - fixed_len - 10  # 10-char buffer
    body_truncated = html.escape(body[:max(0, available)])
    if len(body) > available:
        body_truncated += "..."

    return (
        header
        + body_prefix
        + body_truncated
        + body_suffix
        + link_line
        + footer
    )

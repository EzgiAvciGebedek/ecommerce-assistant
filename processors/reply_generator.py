import logging
import time

import anthropic

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 400
TEMPERATURE = 0.7
MAX_RETRIES = 2

SYSTEM_PROMPT = """You are helping Vahid Faraji, a solo developer based in Istanbul, Turkey, \
write replies to online posts about AI token costs and context management.

Vahid built Tokalator — a VS Code extension that helps developers optimize their \
Claude/GPT API usage, reduce token waste, and understand their context window \
consumption in real time.

Vahid's writing voice:
- Direct and technical — gets to the point fast, no fluff
- Shares specific numbers when possible ("reduced my prompt tokens by 40%")
- Speaks from personal experience as someone who was frustrated by the same problem \
before building the solution
- Never comes across as salesy or spammy — leads with genuinely helpful info
- Mentions Tokalator naturally, only when it's directly relevant
- Has a slight "builder sharing what works" energy — collegial, not authoritative
- Does not use phrases like "Great question!" or "I totally agree!"
- Keeps replies to 150-250 words max — readable on mobile

Rules:
- NEVER fabricate specific statistics you don't have
- ALWAYS lead with actual value/insight before mentioning Tokalator
- If the post is a question, answer it directly first
- Include a brief, non-pushy mention of Tokalator as "something I built to solve \
exactly this" — never as a hard sell
- End with something that invites conversation, not a CTA
- Do NOT use markdown formatting in the reply (no bold, no headers, no bullet points \
with asterisks) — plain text only"""

USER_PROMPT_TEMPLATE = """Platform: {source}{subreddit_context}
Post title: {title}
Post author: {author}
Post content: {body}
Matched keyword: {matched_keyword}

Write a reply in Vahid's voice. The reply should:
1. Acknowledge the specific pain point the person mentioned
2. Share a concrete insight or solution (from Vahid's experience building Tokalator)
3. Mention Tokalator briefly and naturally — only if it directly solves their problem
4. Be 150-250 words, conversational, plain text (no markdown)

Return ONLY the reply text. No intro, no explanation, just the reply."""


def generate_draft_reply(opportunity: dict, api_key: str) -> str:
    source = opportunity.get("source", "unknown")
    subreddit = opportunity.get("subreddit", "")
    subreddit_context = f" ({subreddit})" if subreddit else ""

    prompt = USER_PROMPT_TEMPLATE.format(
        source=source,
        subreddit_context=subreddit_context,
        title=opportunity.get("title", ""),
        author=opportunity.get("author", ""),
        body=opportunity.get("body", "")[:400],
        matched_keyword=opportunity.get("matched_keyword", ""),
    )

    client = anthropic.Anthropic(api_key=api_key)

    for attempt in range(MAX_RETRIES):
        try:
            message = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text.strip()
        except anthropic.RateLimitError:
            if attempt < MAX_RETRIES - 1:
                logger.warning("Rate limited by Claude API, waiting 60s...")
                time.sleep(60)
            else:
                logger.error("Rate limit exceeded after %d attempts", MAX_RETRIES)
        except anthropic.APIError as e:
            logger.error("Claude API error: %s", e)
            break

    return "[Draft generation failed — review the post and reply manually]"

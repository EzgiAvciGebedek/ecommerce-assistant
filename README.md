# Tokalator Agentic Marketing — Week 1: Listening Agent

Monitors Reddit, Hacker News, and GitHub Issues for token/cost pain points, generates Claude draft replies in Vahid's voice, and sends them to Telegram for quick review and posting.

## How it works

```
GitHub Actions cron (every 6h)
    └─> listening_agent.py
          ├─> Reddit RSS (r/ClaudeAI, r/ChatGPT, r/LocalLLaMA, r/webdev)
          ├─> HN Algolia API
          ├─> GitHub Issues (claude-code, cursor, vscode)
          ├─> Dedup against seen_posts.json
          ├─> Claude Sonnet generates draft reply
          └─> Telegram notification → you copy-paste and post
```

Your daily job: open Telegram, see 0-5 opportunities with ready-to-post drafts, pick the best ones, post in 10 minutes.

## Setup

### 1. Get your Telegram Chat ID

1. Message [@userinfobot](https://t.me/userinfobot) on Telegram
2. It will reply with your user ID — that's your `TELEGRAM_CHAT_ID`

### 2. Set GitHub Actions secrets

In your GitHub repo: **Settings → Secrets and variables → Actions → New repository secret**

| Secret | Value |
|---|---|
| `ANTHROPIC_API_KEY` | Your Claude API key (`sk-ant-...`) |
| `TELEGRAM_BOT_TOKEN` | Your bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | Your Telegram user ID from step 1 |

`GITHUB_TOKEN` is automatically provided by GitHub Actions — no action needed.

### 3. Local development

```bash
cd agentic-marketing
cp .env.example .env
# Fill in your real credentials in .env

pip install -r requirements.txt

# Test without sending Telegram messages
DRY_RUN=true python -m agents.listening_agent
```

### 4. Deploy

Push to GitHub. The workflow at `.github/workflows/listening-agent.yml` will:
- Run automatically every 6 hours (00:00, 06:00, 12:00, 18:00 UTC)
- Send Telegram notifications for new opportunities
- Commit the updated dedup state back to the repo

To trigger manually: GitHub → Actions → "Tokalator Listening Agent" → Run workflow

## What you get in Telegram

Each message looks like:

```
🎯 New Opportunity — 🟠 r/ClaudeAI

📌 Claude API is destroying my budget — any tips?
👤 u/devguy2024 · 🔑 "api cost"

Post excerpt:
I'm spending $200/month on Claude API calls...

🔗 View Original Post

━━━━━━━━━━━━━━━━━━━━

✍️ DRAFT REPLY (copy-paste ready):

The system prompt re-sending issue is one of the biggest sources
of token waste...

━━━━━━━━━━━━━━━━━━━━
🕐 Detected: 2026-03-05T14:32:00 UTC
```

At the end of each run you'll also get a summary:
```
✅ Run complete — 3 new opportunities sent
🟠 Reddit: 2 · 🟡 HN: 1 · ⚫ GitHub: 0
```

This confirms the agent is alive even when there's nothing new.

## Configuration

Edit constants at the top of each source file to adjust:
- **Keywords**: `KEYWORDS` in `sources/reddit_source.py`
- **Subreddits**: `SUBREDDITS` in `sources/reddit_source.py`
- **Max per run**: `MAX_PER_RUN` in `agents/listening_agent.py` (default: 5)
- **Dedup window**: `MAX_AGE_DAYS` in `processors/deduplicator.py` (default: 14 days)

## File structure

```
agentic-marketing/
├── agents/
│   └── listening_agent.py      # Main orchestrator — entry point
├── sources/
│   ├── reddit_source.py        # Reddit RSS polling
│   ├── hackernews_source.py    # HN Algolia API
│   └── github_issues_source.py # GitHub Issues API
├── processors/
│   ├── deduplicator.py         # JSON-based dedup state manager
│   └── reply_generator.py      # Claude draft generation
├── notifiers/
│   └── telegram_notifier.py    # Telegram message sender
├── state/
│   └── seen_posts.json         # Dedup state (auto-updated by bot)
├── requirements.txt
└── .env.example
```

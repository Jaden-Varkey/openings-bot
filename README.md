# openings-bot 📬

[![watch internships](https://github.com/Jaden-Varkey/openings-bot/actions/workflows/watch.yml/badge.svg)](https://github.com/Jaden-Varkey/openings-bot/actions/workflows/watch.yml)
[![License](https://img.shields.io/github/license/Jaden-Varkey/openings-bot)](LICENSE)
![Python](https://img.shields.io/badge/python-3.12-blue)

Get an **email + Telegram** alert the moment a company you're watching opens a
new **internship or job application** matching your keywords.

It polls the **official public job-board APIs** (Greenhouse, Lever, Ashby,
SmartRecruiters, Workday) — the same endpoints those career sites use to load
their own listings. No scraping, no login, no getting blocked. It runs for free
and keeps checking every few minutes even while your computer is off, and your
company list never touches the repo.

## How it works

1. You list the companies to watch and the keywords to match (e.g. `intern`, or
   a specific role) — kept private, never committed.
2. It calls each company's public API and keeps only the titles you care about.
3. The first time it sees a company it quietly records what's already open, so
   you don't get spammed with the backlog. After that, only **newly posted**
   jobs trigger an alert.
4. It sends one message per channel and remembers what it's seen for next time.

## Quick start

Try it on your own machine first — no accounts or secrets needed:

```bash
pip install -r requirements.txt
cp companies.example.yaml companies.yaml    # create your config file
python -m watcher.webapp                    # locally manage your tracked companies
python -m watcher.main --dry-run            # test fetching jobs without sending alerts
```

`--dry-run` fetches the real listings and prints what it found and what *would*
notify — without sending anything or saving state. Once the output looks right,
set up notifications and let it run for real.

## Configure companies

The easiest way to add companies to your watch list is by using the included **local web app**. It automatically detects the company's job board (Greenhouse, Lever, Ashby, etc.) and seamlessly updates your configuration file.

1. **Start the web app:**
   ```bash
   python -m watcher.webapp
   ```
2. **Open your browser** to `http://127.0.0.1:8765`.
3. **Search for a company** (e.g., "Cloudflare") and click Search. The app will intelligently probe public ATS APIs to find the correct job board.
4. **Click Add**. It gets saved to your local `companies.yaml` file. You can also quickly remove companies from here.
5. **Update GitHub**: Click the "Copy for GitHub" button, head over to your GitHub repository, and paste the contents into your `COMPANIES_YAML` secret so your live bot tracks them.

*(Note: Workday and custom sites can't be auto-detected by name. For those, you can manually add them to `companies.yaml`. Check `companies.example.yaml` for advanced settings like customizing keywords per company).*

> **Tip:** Some large employers (like Amazon) use custom, bot-protected career sites that can't be polled directly. For those, use the **`github_list`** platform which reads a community-maintained listings file on GitHub (see `companies.example.yaml`).

## Notifications

Set up **email, Telegram, or both** — whichever you configure gets used. Provide
these as environment variables locally, or as repository **Secrets** for the
hosted version (Settings → Secrets and variables → Actions).

| Setting | What it is |
|---------|------------|
| `COMPANIES_YAML` | your whole company list, pasted as YAML (keeps it out of the repo) |
| `EMAIL_USER` | the Gmail address that sends the alert |
| `EMAIL_APP_PASSWORD` | a Gmail **App Password** (16 chars), not your login password |
| `EMAIL_TO` | where to send alerts (optional; defaults to `EMAIL_USER`) |
| `TELEGRAM_BOT_TOKEN` | from `@BotFather` |
| `TELEGRAM_CHAT_ID` | your chat id (from `@userinfobot`) |

**Gmail App Password:** turn on 2-Step Verification, then create one at
<https://myaccount.google.com/apppasswords>.
**Telegram:** message `@BotFather` → `/newbot` for the token, send your bot a
message, then get your chat id from `@userinfobot`.

Check both channels work:

```bash
python -m watcher.main --test-notify
```

## Run it for real

Two ways to keep it running around the clock:

**GitHub Actions (zero setup).** Fork/clone this into your own repo, add the
Secrets above, then open the Actions tab → **watch internships** → **Run
workflow**. It then runs on a schedule automatically. Scheduled runs are
best-effort and can be delayed a few minutes — fine for most people.

**Always-on VM (tighter timing).** For punctual checks, run it under `cron` on
any free Linux VM (e.g. Oracle Cloud or Google Cloud always-free):

```bash
git clone <your-repo-url> openings-bot && cd openings-bot
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp companies.example.yaml companies.yaml    # your companies
cp .env.example .env && chmod 600 .env      # your email/telegram secrets
chmod +x run.sh
( crontab -l 2>/dev/null; echo "*/2 * * * * $PWD/run.sh >> $PWD/cron.log 2>&1" ) | crontab -
```

State lives in `state/seen.json` on disk. The first run seeds silently; after
that only genuinely new postings alert.

## Privacy

Nothing personal is stored in the repo. Your company list lives only in the
`COMPANIES_YAML` Secret (or your local gitignored `companies.yaml`); credentials
are encrypted Secrets, masked in logs. On a public repo the workflow sets
`REDACT_LOGS=1`, so the run logs show only a hash per company and match counts —
never names, titles, or URLs. Full details go to your email only.

## CLI reference

```
python -m watcher.main [options]
  --dry-run        fetch + print only; no notify, no state write
  --test-notify    send a hello to every configured channel, then exit
  --seed           re-baseline all companies silently (after editing your list)
  --config PATH    path to companies.yaml
  --state PATH     path to state/seen.json
```

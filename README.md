# openings-bot

Get an **email + Telegram** alert the moment a chosen company opens a new
**SWE/SDE internship** application.

It polls the **official public job-board JSON APIs** (Greenhouse, Lever, Ashby,
SmartRecruiters, Workday) — the same endpoints those career sites use to render
their own pages. No HTML scraping, no auth, no IP bans. It runs free on
**GitHub Actions** every ~5 minutes, even when your computer is off — and your
company list never touches the repo (see [Privacy](#privacy)).

## How it works

1. Reads your company list (from the `COMPANIES_YAML` Secret in CI, or a local
   `companies.yaml` when testing) — which companies + which platform + keywords.
2. Calls each company's public API and keeps only titles matching your keywords
   (default: contains a software-engineering term **and** "intern", minus
   senior/staff/etc.).
3. Diffs against the seen-state. **The first time** it sees a company it records
   all current matches silently (so you aren't spammed with the backlog); after
   that, only *newly appeared* postings trigger an alert.
4. Sends one batched message per channel, then saves the updated state (kept in
   the GitHub Actions cache, never committed to the repo).

**Where it runs:** entirely on GitHub's servers via Actions — *not* your laptop.
So it keeps checking every ~5 minutes whether your machine is asleep, off, on a
different network, or in another country. Your laptop is only used for optional
local testing.

## Quick start (local test, no secrets needed)

```bash
cd openings-bot
python -m pip install -r requirements.txt
cp companies.example.yaml companies.yaml   # then edit companies.yaml
python -m watcher.main --dry-run
```

This fetches the real APIs and prints what it found and what *would* notify —
verify your company tokens and keywords here first. `--dry-run` never writes
state and never sends messages.

### Verify it works (before trusting your real list)

Your real `companies.yaml` targets Summer **2027**; this early in the cycle few
2027 postings exist, so a dry-run of it is legitimately quiet and doesn't prove
much. Two quick checks exercise the machinery against known-good data:

```bash
# 1. Matching logic — offline, deterministic (18 real + edge-case titles):
python -m pytest tests/ -q            # or: python tests/test_filters.py

# 2. Full fetch->filter->match pipeline against LIVE data. Point --config at a
#    small local file listing a company that has open postings right now (and,
#    if testing off-cycle, relax the year filter so current postings show up):
python -m watcher.main --dry-run --config companies.local.yaml --state /tmp/test-state.json
```

The second command should print a healthy count of matches. If both pass,
fetching and matching are sound. (Any `companies*.yaml` file stays local — it's
gitignored, so your list never reaches the repo.)

## Configure companies

Your list is defined in YAML. The committed `companies.example.yaml` is just a
template — copy it to `companies.yaml` (gitignored) for local testing, and paste
the same content into the `COMPANIES_YAML` Secret for the live Action.

```yaml
companies:
  - name: ExampleCo
    platform: greenhouse      # greenhouse|lever|ashby|smartrecruiters|workday|github_list
    token: exampleco          # the company slug from the careers URL
```

Some large employers run JS apps / anti-bot defenses on bespoke career sites that
can't be polled directly. Instead, the **`github_list`** platform reads a
bot-maintained community internship list on GitHub that already aggregates them
(allowed and effectively rate-limit-free):

```yaml
  - name: Bespoke sites (community GitHub list)
    platform: github_list
    url: https://raw.githubusercontent.com/<owner>/<repo>/<branch>/path/to/listings.json
    companies: [CompanyA, CompanyB]   # omit to watch ALL in the list
```

Finding the `token` (slug): open the company's careers page and read the URL.

| Platform        | Careers URL looks like                  | token |
|-----------------|-----------------------------------------|-------|
| greenhouse      | `boards.greenhouse.io/EXAMPLE`          | `EXAMPLE` |
| lever           | `jobs.lever.co/EXAMPLE`                 | `EXAMPLE` |
| ashby           | `jobs.ashbyhq.com/EXAMPLE`              | `EXAMPLE` |
| smartrecruiters | `jobs.smartrecruiters.com/EXAMPLE`      | `EXAMPLE` |

Per-company keyword overrides are optional:

```yaml
  - name: SomeCo
    platform: greenhouse
    token: someco
    keywords:
      include: ["software", "data"]   # replaces only the include list
```

### Adding a Workday company

Workday needs four values you grab once from your browser:

1. Open the company's Workday careers page (URL contains `myworkdayjobs.com`).
2. Open DevTools (F12) → **Network** tab → filter **Fetch/XHR**.
3. Search or scroll the jobs; find the request whose URL ends in **`/jobs`**,
   like: `https://TENANT.wd1.myworkdayjobs.com/wday/cxs/TENANT/SITE/jobs`
4. Copy the pieces into `companies.yaml`:

```yaml
  - name: Some Workday Co
    platform: workday
    tenant: TENANT     # e.g. the subdomain before .wdN.myworkdayjobs.com
    dc: wd1            # the wdN segment (wd1, wd3, wd5, ...)
    site: SITE         # the career-site id from the URL path
    # searchText: intern   # optional server-side filter (default "intern")
```

## Notifications setup (for real alerts)

Set these as environment variables locally, or as **GitHub repository Secrets**
for the Action (Settings → Secrets and variables → Actions → New secret).

| Secret | What it is |
|--------|------------|
| `COMPANIES_YAML` | your entire company list, pasted as YAML (keeps it out of the public repo) |
| `EMAIL_USER` | the Gmail address that sends the alert |
| `EMAIL_APP_PASSWORD` | a Gmail **App Password** (16 chars), *not* your login password |
| `EMAIL_TO` | where to deliver alerts (optional; defaults to `EMAIL_USER`) |
| `TELEGRAM_BOT_TOKEN` | from `@BotFather` |
| `TELEGRAM_CHAT_ID` | your chat id |

You can configure **either or both** channels — whatever's set is used.

**Gmail App Password:** enable 2-Step Verification on your Google account, then
go to <https://myaccount.google.com/apppasswords>, create one, and use the
16-character value as `EMAIL_APP_PASSWORD`.

**Telegram:**
1. Message `@BotFather`, send `/newbot`, follow prompts → it gives you the
   **bot token**.
2. Send any message to your new bot (so it can message you back).
3. Get your **chat id**: message `@userinfobot`, or open
   `https://api.telegram.org/bot<TOKEN>/getUpdates` and read `result[].message.chat.id`.

**Smoke-test both channels:**

```bash
python -m watcher.main --test-notify
```

## Deploy on a free always-on VM (recommended — meets the ≤5-min target)

GitHub Actions' scheduler drifts 5–30 min, so to actually *guarantee* detection
within 5 minutes the poller runs on a small always-free Linux VM under **system
cron** (punctual to the second). Worst case at `*/2` is ~2.5 min, and even a
single missed tick still lands under 5.

Pick any free always-on Linux VM, e.g. **Oracle Cloud Always Free** (genuinely
free forever) or **Google Cloud e2-micro Always Free** (US regions). Then, on the
VM (Ubuntu/Debian shown):

```bash
# 1. python + git
sudo apt update && sudo apt install -y python3 python3-venv git

# 2. get the code
git clone <your-repo-url> openings-bot && cd openings-bot

# 3. deps in a venv
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# 4. your list + secrets — both stay on the VM, never committed
cp companies.example.yaml companies.yaml       # then edit your companies
cp .env.example .env && chmod 600 .env         # then edit EMAIL_*/TELEGRAM_*

# 5. sanity checks
.venv/bin/python -m watcher.main --dry-run      # parse + print, no send
set -a && . ./.env && set +a
.venv/bin/python -m watcher.main --test-notify  # confirm email/telegram

# 6. schedule it punctually (see deploy/crontab.example for the staggered option)
chmod +x run.sh
( crontab -l 2>/dev/null; echo "*/2 * * * * $PWD/run.sh >> $PWD/cron.log 2>&1" ) | crontab -
```

State lives in `state/seen.json` on the VM disk (durable across reboots). Tail
`cron.log` to watch runs. The first run seeds silently; after that only genuinely
new postings alert. Because it's your own box, `companies.yaml` and `.env` simply
live on disk (no GitHub Secret needed) — keep `.env` at `chmod 600`.

## Alternative: GitHub Actions (zero setup, but NO timing guarantee)

Simpler to stand up, but scheduled runs are best-effort and **routinely delayed
5–30 min** — fine if you don't need the strict 5-minute ceiling.

1. Create a **public** repo (unlimited free Actions minutes). `companies.yaml`,
   `state/` and `.env` are gitignored, so only generic code is pushed.
2. Add Secrets (Settings → Secrets and variables → Actions): `COMPANIES_YAML`
   plus one notification channel's secrets.
3. Actions tab → **watch internships** → **Run workflow**. First run seeds state.

> GitHub auto-pauses schedules after 60 days with no commits; re-enable from the
> Actions tab if you ever go that long untouched.

## Privacy

Nothing personal is ever stored in the repo:

- **Company list** → lives only in the encrypted `COMPANIES_YAML` Secret (and
  your local, gitignored `companies.yaml`). The repo holds just the template.
- **Seen-state** → persisted in the **GitHub Actions cache**, not committed, so
  company names never appear in git history (a public commit history of names
  could otherwise be brute-forced even if hashed).
- **Credentials** → encrypted Secrets, masked in logs.

> Edge case: if the Actions cache is ever evicted (rare for a job running every
> 5 min, since constant access keeps it warm), the next run re-seeds silently —
> you simply won't be alerted for anything posted during that gap.

## CLI reference

```
python -m watcher.main [options]
  --dry-run        fetch + print only; no notify, no state write
  --test-notify    send a hello to every configured channel, then exit
  --seed           re-baseline all companies silently (after editing keywords/list)
  --config PATH    path to companies.yaml
  --state PATH     path to state/seen.json
```

## Being a good citizen

- Only official public JSON endpoints are used, at a 5-minute cadence.
- Realistic User-Agent, request timeouts, bounded retry/backoff, and a short
  delay between companies.
- A single company's failure is logged and skipped — it never aborts the run.

"""Entry point: load config -> fetch -> filter -> diff -> notify -> save state.

Run modes (flags can be combined):
  --dry-run       fetch + filter + print, but never notify and never write state
  --test-notify   send a 'hello' through every configured channel, then exit
  --seed          treat every company as fresh: record all current matches as
                  'seen' without notifying (use after editing keywords/companies)
  --once          single pass (default; present for clarity / future loop mode)
  --config PATH   path to companies.yaml
  --state PATH    path to state/seen.json
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
import time
from pathlib import Path

from . import config as config_mod
from . import notify, state as state_mod
from .filters import filter_jobs, merge_keywords
from .models import Job
from .providers import get_fetcher

# Small polite delay between companies so we never burst many requests at once.
PER_COMPANY_DELAY = 1.0  # seconds


def _redact_enabled() -> bool:
    """Whether to keep sensitive detail (company names, job titles, URLs) OUT of
    stdout. On a PUBLIC repo, GitHub Actions run logs are world-readable, so we
    redact there by default; local runs stay fully verbose for debugging.

    Control explicitly with REDACT_LOGS=1 (force on) or REDACT_LOGS=0 (force off);
    otherwise it auto-enables whenever running inside GitHub Actions.
    """
    val = os.environ.get("REDACT_LOGS")
    if val is not None:
        return val.strip().lower() not in ("", "0", "false", "no", "off")
    return bool(os.environ.get("GITHUB_ACTIONS"))


def _pseudonym(name: str) -> str:
    """Stable, non-reversible label for a company name. Same company maps to the
    same token across runs (useful for correlating logs) without revealing who
    it is."""
    return "company:" + hashlib.sha256(name.encode("utf-8")).hexdigest()[:8]


def _co(name: str, redact: bool) -> str:
    return _pseudonym(name) if redact else name


def _collect_new_jobs(
    cfg: dict, state: dict, *, seed: bool, dry_run: bool
) -> list[Job]:
    """Fetch + filter every company, returning the matching jobs that are new
    (i.e. not already in state). Updates `state` in place for known companies
    unless dry_run. Companies seen for the first time (or under --seed) are
    seeded silently and contribute no 'new' jobs."""
    defaults_keywords = (cfg.get("defaults") or {}).get("keywords")
    companies = cfg["companies"]
    new_jobs: list[Job] = []
    redact = _redact_enabled()

    for i, company in enumerate(companies):
        name = company["name"]
        platform = company["platform"]
        keywords = merge_keywords(defaults_keywords, company.get("keywords"))

        try:
            fetcher = get_fetcher(platform)
            all_jobs = fetcher(company)
        except Exception as exc:  # noqa: BLE001 - isolate one company's failure
            # The raw exception can embed the company slug/URL, so only its type
            # is safe to log when redacting.
            detail = type(exc).__name__ if redact else exc
            print(f"[fetch] {_co(name, redact)} ({platform}) FAILED: {detail}")
            continue

        matches = filter_jobs(all_jobs, keywords)
        match_ids = [j.id for j in matches]
        print(
            f"[fetch] {_co(name, redact)}: {len(all_jobs)} postings, "
            f"{len(matches)} match (known={state_mod.is_known_company(state, name)})"
        )

        first_time = seed or not state_mod.is_known_company(state, name)
        if first_time:
            # Seed silently — establish the baseline without alerting.
            if not dry_run:
                state_mod.mark_seen(state, name, match_ids)
            if redact:
                if matches:
                    print(f"        seeded {len(matches)} match(es)")
            else:
                for j in matches:
                    print(f"        seeded: {j.title}")
        else:
            already = state_mod.seen_ids(state, name)
            fresh = [j for j in matches if j.id not in already]
            if redact:
                if fresh:
                    print(f"        {len(fresh)} NEW match(es) — details sent via notification")
            else:
                for j in fresh:
                    print(f"        NEW: {j.title} -> {j.url}")
            new_jobs.extend(fresh)
            if not dry_run:
                state_mod.mark_seen(state, name, match_ids)

        if i < len(companies) - 1:
            time.sleep(PER_COMPANY_DELAY)

    return new_jobs


def run(args: argparse.Namespace) -> int:
    if args.test_notify:
        notify.send_test()
        return 0

    cfg_path = Path(args.config) if args.config else config_mod.DEFAULT_CONFIG_PATH
    state_path = Path(args.state) if args.state else state_mod.DEFAULT_STATE_PATH

    try:
        cfg = config_mod.load(cfg_path)
    except config_mod.ConfigError as exc:
        print(f"[config] {exc}", file=sys.stderr)
        return 2

    state = state_mod.load(state_path)
    channels = notify.configured_channels()
    if not channels and not args.dry_run:
        print(
            "[warn] no notification channels configured (EMAIL_* / TELEGRAM_*); "
            "new jobs will be printed but not delivered."
        )
    else:
        print(f"[config] channels: {', '.join(channels) or 'none'}")

    new_jobs = _collect_new_jobs(
        cfg, state, seed=args.seed, dry_run=args.dry_run
    )

    if args.dry_run:
        print(f"[done] dry-run: {len(new_jobs)} new job(s); state NOT written")
        return 0

    if new_jobs:
        notify.notify_new_jobs(new_jobs)
    else:
        print("[done] no new postings")

    state_mod.save(state, state_path)
    print(f"[done] state written to {state_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="watcher", description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--test-notify", action="store_true")
    parser.add_argument("--seed", action="store_true")
    parser.add_argument("--once", action="store_true", help="single pass (default)")
    parser.add_argument("--config", help="path to companies.yaml")
    parser.add_argument("--state", help="path to state/seen.json")
    args = parser.parse_args(argv)
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())

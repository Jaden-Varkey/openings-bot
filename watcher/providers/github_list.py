"""Community-maintained internship lists hosted on GitHub.

Some community repos publish a structured `listings.json` that a bot keeps
updated — and they already aggregate large employers on bespoke career sites
that can't be polled directly. Reading a raw GitHub file is fully allowed and
effectively rate-limit-free, so this is a ban-proof way to cover those employers.

Required cfg key:
  url:  raw URL of the listings.json (see companies.yaml for the default).
Optional cfg keys:
  companies:    only keep these company names (case-insensitive). Omit for all.
  active_only:  drop closed listings (default True).
  visible_only: drop hidden listings (default True).
"""

from __future__ import annotations

from ..models import Job
from .http import get_json


def _wanted(name: str, allow: set[str] | None) -> bool:
    return allow is None or name.strip().lower() in allow


def fetch(cfg: dict) -> list[Job]:
    company_label = cfg["name"]
    url = cfg["url"]
    active_only = cfg.get("active_only", True)
    visible_only = cfg.get("visible_only", True)
    allow = cfg.get("companies")
    allow_set = {c.strip().lower() for c in allow} if allow else None

    data = get_json(url)
    jobs: list[Job] = []
    for item in data:
        if active_only and not item.get("active", True):
            continue
        if visible_only and not item.get("is_visible", True):
            continue
        name = item.get("company_name") or company_label
        if not _wanted(name, allow_set):
            continue
        jid = item.get("id")
        if not jid:
            continue
        locations = item.get("locations") or []
        jobs.append(
            Job(
                company=name,
                id=str(jid),
                title=(item.get("title") or "").strip(),
                url=item.get("url") or item.get("company_url") or "",
                location="; ".join(locations) if isinstance(locations, list) else str(locations),
            )
        )
    return jobs

"""Auto-detect a company's job board from just its name.

Company slugs on the big ATSs are almost always the normalized company name, so
we generate a few candidate slugs and probe each provider's public API. Whatever
returns a valid board wins — no API key, no LLM, fully deterministic.

Covers the slug-based boards (Greenhouse, Lever, Ashby, SmartRecruiters). Workday
can't be guessed from a name (it needs tenant/dc/site), so it's not probed here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import requests

TIMEOUT = 6

# name -> (url template, function extracting the job count from the JSON body)
PROBES = {
    "greenhouse": (
        "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
        lambda d: len(d.get("jobs", [])) if isinstance(d, dict) else None,
    ),
    "lever": (
        "https://api.lever.co/v0/postings/{slug}?mode=json",
        lambda d: len(d) if isinstance(d, list) else None,
    ),
    "ashby": (
        "https://api.ashbyhq.com/posting-api/job-board/{slug}",
        lambda d: len(d.get("jobs", [])) if isinstance(d, dict) else None,
    ),
    "smartrecruiters": (
        "https://api.smartrecruiters.com/v1/companies/{slug}/postings",
        lambda d: d.get("totalFound") if isinstance(d, dict) else None,
    ),
}


@dataclass
class Match:
    platform: str
    token: str
    job_count: int
    proper_name: str | None = None


def candidate_slugs(name: str) -> list[str]:
    """A few plausible slugs for a company name, most-likely first."""
    low = name.strip().lower()
    compact = re.sub(r"[^a-z0-9]", "", low)      # "Capital One" -> "capitalone"
    hyphen = re.sub(r"[^a-z0-9]+", "-", low).strip("-")   # -> "capital-one"
    underscore = re.sub(r"[^a-z0-9]+", "_", low).strip("_")
    # dict.fromkeys keeps order while dropping duplicates (e.g. single-word names)
    return list(dict.fromkeys(c for c in (compact, hyphen, underscore) if c))


def _probe(platform: str, slug: str) -> Match | None:
    url_tmpl, count_of = PROBES[platform]
    try:
        r = requests.get(url_tmpl.format(slug=slug), timeout=TIMEOUT)
    except requests.RequestException:
        return None
    if r.status_code != 200:
        return None
    try:
        data = r.json()
        count = count_of(data)
    except ValueError:
        return None
    if count is None:
        return None
        
    proper_name = None
    if platform == "greenhouse":
        try:
            res = requests.get(f"https://boards-api.greenhouse.io/v1/boards/{slug}", timeout=TIMEOUT)
            if res.status_code == 200:
                proper_name = res.json().get("name")
        except:
            pass
    elif platform == "smartrecruiters":
        try:
            proper_name = data.get("content", [{}])[0].get("company", {}).get("name")
        except:
            pass

    return Match(platform=platform, token=slug, job_count=count, proper_name=proper_name)


def resolve(name: str) -> list[Match]:
    """Return the job boards that match `name`, most openings first.

    Only boards with at least one live posting are returned: some APIs (notably
    SmartRecruiters) answer 200 with an empty list for *any* slug, so a zero
    count can't be trusted as a real board. Slugs are tried in order and the
    first one that yields any hit wins, so we don't report the same company
    under several near-identical slugs.
    """
    for slug in candidate_slugs(name):
        matches = [
            hit
            for platform in PROBES
            if (hit := _probe(platform, slug)) and hit.job_count > 0
        ]
        if matches:
            matches.sort(key=lambda m: m.job_count, reverse=True)
            return matches
    return []


if __name__ == "__main__":  # quick manual check: python -m watcher.resolve Cloudflare
    import sys

    for m in resolve(" ".join(sys.argv[1:]) or "Cloudflare"):
        print(f"{m.platform:16} token={m.token:20} jobs={m.job_count}")

"""SmartRecruiters public postings API.

Endpoint:  GET https://api.smartrecruiters.com/v1/companies/{token}/postings
The `token` is the company identifier from jobs.smartrecruiters.com/{token}.
"""

from __future__ import annotations

from ..models import Job
from .http import get_json

API = "https://api.smartrecruiters.com/v1/companies/{token}/postings"
PUBLIC_URL = "https://jobs.smartrecruiters.com/{token}/{id}"


def _location(j: dict) -> str:
    loc = j.get("location") or {}
    parts = [loc.get("city"), loc.get("region"), loc.get("country")]
    text = ", ".join(p for p in parts if p)
    if loc.get("remote"):
        text = f"{text} (remote)" if text else "Remote"
    return text


def fetch(cfg: dict) -> list[Job]:
    company = cfg["name"]
    token = cfg["token"]
    # The API paginates; 100 covers any realistic single-company posting count.
    data = get_json(API.format(token=token), params={"limit": 100})
    jobs: list[Job] = []
    for j in data.get("content", []):
        jid = j.get("id")
        if not jid:
            continue
        jobs.append(
            Job(
                company=company,
                id=str(jid),
                title=(j.get("name") or "").strip(),
                url=PUBLIC_URL.format(token=token, id=jid),
                location=_location(j),
            )
        )
    return jobs

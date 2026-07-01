"""Ashby public job board API.

Endpoint:  GET https://api.ashbyhq.com/posting-api/job-board/{token}
The `token` is the company slug from jobs.ashbyhq.com/{token}.
"""

from __future__ import annotations

from ..models import Job
from .http import get_json

API = "https://api.ashbyhq.com/posting-api/job-board/{token}"


def fetch(cfg: dict) -> list[Job]:
    company = cfg["name"]
    token = cfg["token"]
    data = get_json(API.format(token=token))
    jobs: list[Job] = []
    for j in data.get("jobs", []):
        jid = j.get("id")
        if not jid:
            continue
        jobs.append(
            Job(
                company=company,
                id=str(jid),
                title=(j.get("title") or "").strip(),
                url=j.get("jobUrl") or j.get("applyUrl") or "",
                location=j.get("location") or "",
            )
        )
    return jobs

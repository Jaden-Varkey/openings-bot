"""Greenhouse public job board API.

Endpoint:  GET https://boards-api.greenhouse.io/v1/boards/{token}/jobs
The `token` is the company slug from boards.greenhouse.io/{token}.
"""

from __future__ import annotations

from ..models import Job
from .http import get_json

API = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"


def fetch(cfg: dict) -> list[Job]:
    company = cfg["name"]
    token = cfg["token"]
    data = get_json(API.format(token=token))
    jobs: list[Job] = []
    for j in data.get("jobs", []):
        jid = j.get("id")
        if jid is None:
            continue
        location = (j.get("location") or {}).get("name", "") or ""
        jobs.append(
            Job(
                company=company,
                id=str(jid),
                title=j.get("title", "").strip(),
                url=j.get("absolute_url", ""),
                location=location,
            )
        )
    return jobs

"""Lever public postings API.

Endpoint:  GET https://api.lever.co/v0/postings/{token}?mode=json
The `token` is the company slug from jobs.lever.co/{token}.
"""

from __future__ import annotations

from ..models import Job
from .http import get_json

API = "https://api.lever.co/v0/postings/{token}"


def fetch(cfg: dict) -> list[Job]:
    company = cfg["name"]
    token = cfg["token"]
    data = get_json(API.format(token=token), params={"mode": "json"})
    jobs: list[Job] = []
    for j in data:
        jid = j.get("id")
        if not jid:
            continue
        categories = j.get("categories") or {}
        jobs.append(
            Job(
                company=company,
                id=str(jid),
                title=(j.get("text") or "").strip(),
                url=j.get("hostedUrl") or j.get("applyUrl") or "",
                location=categories.get("location", "") or "",
            )
        )
    return jobs

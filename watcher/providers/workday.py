"""Workday public careers (CXS) API.

Endpoint:  POST https://{tenant}.{dc}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs

Workday is per-company: you must supply `tenant`, `dc` (data center, e.g. wd1,
wd5), and `site` (the career site id). Grab these once from DevTools > Network:
open the company's Workday careers page, find the XHR ending in `/jobs`, and read
the four path segments. The README documents this step by step.

Optional cfg keys:
  searchText: server-side search string (default "intern" to narrow results).
  locale:     URL locale segment for the public link (default "en-US").
"""

from __future__ import annotations

from ..models import Job
from .http import post_json

API = "https://{tenant}.{dc}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs"
PUBLIC = "https://{tenant}.{dc}.myworkdayjobs.com/{locale}/{site}{path}"

PAGE_SIZE = 20
MAX_PAGES = 10  # safety cap: up to 200 postings per company


def fetch(cfg: dict) -> list[Job]:
    company = cfg["name"]
    tenant = cfg["tenant"]
    dc = cfg["dc"]
    site = cfg["site"]
    search_text = cfg.get("searchText", "intern")
    locale = cfg.get("locale", "en-US")
    url = API.format(tenant=tenant, dc=dc, site=site)

    jobs: list[Job] = []
    offset = 0
    for _ in range(MAX_PAGES):
        body = {
            "appliedFacets": {},
            "limit": PAGE_SIZE,
            "offset": offset,
            "searchText": search_text,
        }
        data = post_json(url, body)
        postings = data.get("jobPostings", [])
        for j in postings:
            path = j.get("externalPath", "")
            if not path:
                continue
            jobs.append(
                Job(
                    company=company,
                    id=path,  # externalPath is stable and unique per posting
                    title=(j.get("title") or "").strip(),
                    url=PUBLIC.format(
                        tenant=tenant, dc=dc, locale=locale, site=site, path=path
                    ),
                    location=j.get("locationsText", "") or "",
                )
            )
        total = data.get("total", 0)
        offset += PAGE_SIZE
        if offset >= total or not postings:
            break
    return jobs

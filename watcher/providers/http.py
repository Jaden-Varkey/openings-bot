"""Shared, polite HTTP helpers for all providers.

We hit official public JSON endpoints only, at low frequency, with a realistic
User-Agent and bounded retry/backoff. This keeps us well-behaved and avoids
tripping rate limits or bot defenses.
"""

from __future__ import annotations

import time
from typing import Any

import requests

# A plain, honest User-Agent. Identifies a normal browser-like client without
# pretending to be a specific person; these endpoints serve public job data.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36 openings-bot/0.1"
)

DEFAULT_TIMEOUT = 20  # seconds
MAX_RETRIES = 3
BACKOFF_BASE = 1.5  # seconds; grows as BACKOFF_BASE * (2 ** attempt)

_session: requests.Session | None = None


def session() -> requests.Session:
    global _session
    if _session is None:
        s = requests.Session()
        s.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
        _session = s
    return _session


def _request(method: str, url: str, **kwargs: Any) -> requests.Response:
    kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
    last_exc: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = session().request(method, url, **kwargs)
            # Retry on transient server / rate-limit responses.
            if resp.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(f"{resp.status_code} for {url}", response=resp)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < MAX_RETRIES - 1:
                time.sleep(BACKOFF_BASE * (2**attempt))
    assert last_exc is not None
    raise last_exc


def get_json(url: str, params: dict | None = None) -> Any:
    return _request("GET", url, params=params).json()


def post_json(url: str, json_body: dict) -> Any:
    return _request("POST", url, json=json_body).json()

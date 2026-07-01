"""Provider registry.

Maps a `platform` string (as used in companies.yaml) to a `fetch(cfg) -> list[Job]`
function. Add a new platform by writing a module with a `fetch` function and
registering it here.
"""

from __future__ import annotations

from typing import Callable

from ..models import Job
from . import ashby, github_list, greenhouse, lever, smartrecruiters, workday

REGISTRY: dict[str, Callable[[dict], list[Job]]] = {
    "greenhouse": greenhouse.fetch,
    "lever": lever.fetch,
    "ashby": ashby.fetch,
    "smartrecruiters": smartrecruiters.fetch,
    "workday": workday.fetch,
    "github_list": github_list.fetch,
}


def get_fetcher(platform: str) -> Callable[[dict], list[Job]]:
    try:
        return REGISTRY[platform]
    except KeyError:
        raise ValueError(
            f"Unknown platform '{platform}'. "
            f"Supported: {', '.join(sorted(REGISTRY))}"
        )

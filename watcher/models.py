"""Normalized data model shared across providers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Job:
    """A single job posting, normalized across all ATS platforms.

    `id` is the stable, provider-supplied identifier. Combined with `company`
    it forms the dedup key used by the state store, so two different companies
    can reuse the same underlying id without colliding.
    """

    company: str
    id: str
    title: str
    url: str
    location: str = ""

    @property
    def key(self) -> str:
        """Globally unique dedup key: '<company>:<id>'."""
        return f"{self.company}:{self.id}"

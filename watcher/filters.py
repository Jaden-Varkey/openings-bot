"""Keyword matching for job titles.

A job matches when its title (case-insensitive):
  - contains at least one `include` term, AND
  - contains every `require` term, AND
  - contains none of the `exclude` terms.

Matching is word-aware, not naive substring, to avoid false positives like
"intern" matching inside "Internal":

  * include  -> word-PREFIX match (`\\bsoftware engineer` also matches
                "Software Engineering Intern", `develop` -> developer/development).
  * require / exclude -> whole-WORD match allowing common inflections
                (`intern` matches intern/interns/internship/internships/interning
                but NOT "internal"/"internals").

Global defaults live under `defaults.keywords` in companies.yaml; any company
may override individual lists under its own `keywords:` key.
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Iterable

from .models import Job

DEFAULT_KEYWORDS: dict[str, list[str]] = {
    "include": [
        "software engineer",
        "software developer",
        "software development",
        "software dev engineer",  # some employers' "SDE" phrasing
        "swe",
        "sde",
    ],
    "require": ["intern"],
    "exclude": [
        # seniority
        "senior", "staff", "principal", "manager", "director",
        # Wrong-cycle postings: drop titles clearly labeled for other seasons or
        # years, but keep postings with no season/year in the title. Adjust these
        # to your own target cycle (add the years/seasons you want to exclude).
        "2023", "2024", "2025", "2026", "2028",
        "fall", "autumn", "winter", "spring",
    ],
}

# Inflections appended to require/exclude terms for whole-word matching.
# Crucially this lets "intern" match "internship" while still rejecting
# "internal" (whose trailing "al" is not in this set, so the word boundary
# after the optional suffix fails).
_SUFFIX = r"(?:s|es|ship|ships|ing)?"


@lru_cache(maxsize=512)
def _prefix_re(kw: str) -> re.Pattern[str]:
    return re.compile(r"\b" + re.escape(kw.lower()), re.IGNORECASE)


@lru_cache(maxsize=512)
def _word_re(kw: str) -> re.Pattern[str]:
    return re.compile(r"\b" + re.escape(kw.lower()) + _SUFFIX + r"\b", re.IGNORECASE)


def _include_matches(title: str, term: str) -> bool:
    """An include term matches when *every* word in it appears as a word-prefix
    somewhere in the title (order-independent). So "software engineer" also
    catches "Software Automation Engineer Intern" and "Software Quality Engineer
    Intern", while staying narrower than bare "software"."""
    return all(_prefix_re(word).search(title) for word in term.split())


def merge_keywords(
    defaults: dict | None, override: dict | None
) -> dict[str, list[str]]:
    """Return a complete keyword config, letting `override` replace any of the
    three lists individually while falling back to `defaults` (then the
    built-in DEFAULT_KEYWORDS) for the rest."""
    base = {**DEFAULT_KEYWORDS, **(defaults or {})}
    merged = {**base, **(override or {})}
    # Coerce to str so unquoted YAML numbers (e.g. a bare 2027) don't blow up
    # the regex helpers, which call .lower() / re.escape().
    return {
        "include": [str(x) for x in (merged.get("include") or [])],
        "require": [str(x) for x in (merged.get("require") or [])],
        "exclude": [str(x) for x in (merged.get("exclude") or [])],
    }


def title_matches(title: str, keywords: dict[str, Iterable[str]]) -> bool:
    include = list(keywords.get("include", []))
    require = list(keywords.get("require", []))
    exclude = list(keywords.get("exclude", []))

    if include and not any(_include_matches(title, k) for k in include):
        return False
    if any(not _word_re(k).search(title) for k in require):
        return False
    if any(_word_re(k).search(title) for k in exclude):
        return False
    return True


def filter_jobs(jobs: Iterable[Job], keywords: dict[str, Iterable[str]]) -> list[Job]:
    return [j for j in jobs if title_matches(j.title, keywords)]

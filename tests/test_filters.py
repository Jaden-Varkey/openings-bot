"""Offline regression tests for title matching — no network needed.

Run:  python -m pytest tests/ -q      (or)      python tests/test_filters.py

Cases are real titles pulled from live ATS/list APIs plus edge cases that the
word-aware matcher is specifically designed to get right (e.g. rejecting
"Internal"/"International", accepting "intern"/"internship").
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make `watcher` importable whether run via pytest or as a plain script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from watcher.filters import DEFAULT_KEYWORDS, title_matches

# (title, should_match_under_the_default_keywords)
CASES: list[tuple[str, bool]] = [
    # --- should ALERT ---
    ("Software Engineer, Intern", True),
    ("Software Engineer Internship", True),
    ("Software Developer Intern", True),
    ("Software Dev Engineer Intern", True),          # "SDE" phrasing
    ("SWE Intern", True),
    ("Software Engineering Intern, Summer 2027", True),
    ("Software Automation Engineer Intern", True),
    ("Full Stack Software Engineer Intern", True),
    # --- should be REJECTED ---
    ("Software Engineer, Internal Systems", False),  # 'Internal', not 'intern'
    ("Internal Audit Analyst", False),
    ("International Growth PM", False),
    ("Senior Software Engineer - Database Engine Internals", False),
    ("Staff Software Engineer Intern", False),       # seniority excluded
    ("Software Engineer Intern, Fall 2026", False),  # fall + 2026 excluded
    ("Software Engineer Intern - Summer 2025", False),
    ("Data Scientist Intern", False),                # no SWE include term
    ("Research Scientist Intern - AI/ML", False),    # not a SWE title
    ("Mechanical Engineer Intern", False),
]


def test_default_keyword_matching() -> None:
    failures = []
    for title, expected in CASES:
        got = title_matches(title, DEFAULT_KEYWORDS)
        if got != expected:
            failures.append(f"  {title!r}: got {got}, expected {expected}")
    assert not failures, "title_matches mismatches:\n" + "\n".join(failures)


if __name__ == "__main__":
    test_default_keyword_matching()
    print(f"OK — all {len(CASES)} cases passed")

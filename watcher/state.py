"""Persistence of already-seen job ids.

The state file maps a company to the list of job ids we've already observed. The
company is stored as a one-way hash, never in plaintext:
  { "<sha256(company)[:16]>": ["<id>", ...] }.
This keeps company names out of the persisted state (which on CI lives in the
GitHub Actions cache), so nothing that leaves this process reveals which
companies are watched. Dedup is unaffected — the hash is stable — and alert
emails still show the real name, which comes from the live fetch, not state.

On the very first run for a company (no entry yet) we seed every currently
matching job as 'seen' WITHOUT notifying, so the user isn't blasted with the
entire existing backlog. Only postings that appear afterwards trigger alerts.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

DEFAULT_STATE_PATH = Path(__file__).resolve().parent.parent / "state" / "seen.json"


def _key(company: str) -> str:
    """Stable, non-reversible state key for a company name."""
    return hashlib.sha256(company.encode("utf-8")).hexdigest()[:16]


def load(path: Path = DEFAULT_STATE_PATH) -> dict[str, list[str]]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    # Coerce to the expected shape defensively.
    return {str(k): [str(i) for i in (v or [])] for k, v in data.items()}


def save(state: dict[str, list[str]], path: Path = DEFAULT_STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Sorted ids keep the committed diff small and stable between runs.
    serializable = {k: sorted(set(v)) for k, v in sorted(state.items())}
    with path.open("w", encoding="utf-8") as f:
        json.dump(serializable, f, indent=2, ensure_ascii=False)
        f.write("\n")


def is_known_company(state: dict[str, list[str]], company: str) -> bool:
    """Whether we've recorded this company before (i.e. it has been seeded)."""
    return _key(company) in state


def seen_ids(state: dict[str, list[str]], company: str) -> set[str]:
    return set(state.get(_key(company), []))


def mark_seen(state: dict[str, list[str]], company: str, ids: list[str]) -> None:
    key = _key(company)
    existing = set(state.get(key, []))
    existing.update(ids)
    state[key] = sorted(existing)

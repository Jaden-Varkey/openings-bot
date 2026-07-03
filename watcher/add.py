"""Add a company to your local companies.yaml — no hand-editing YAML.

Run it with no arguments for friendly prompts:

    python -m watcher.add

...or pass everything on one line to skip the prompts:

    python -m watcher.add --name "ExampleCo" --platform greenhouse --token exampleco

The `token` is just the company's slug from its careers URL — e.g. for
`boards.greenhouse.io/stripe` the token is `stripe`. Workday needs `tenant`,
`dc`, and `site` instead (see the README); github_list needs a `url`.

It appends to companies.yaml (creating it if missing) and validates the entry
the same way the watcher does. Note: saving re-formats the file with standard
YAML style, so any hand-written comments in it are not preserved.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from .config import DEFAULT_CONFIG_PATH, REQUIRED_FIELDS

# Human-friendly hint shown when prompting for each platform-specific field.
FIELD_HELP = {
    "token": "company slug from the careers URL (e.g. boards.greenhouse.io/stripe -> stripe)",
    "tenant": "Workday subdomain before .wdN.myworkdayjobs.com",
    "dc": "Workday data-center segment (wd1, wd3, wd5, ...)",
    "site": "Workday career-site id from the URL path",
    "url": "raw URL of a community listings.json file",
}


def _prompt(label: str, hint: str = "") -> str:
    suffix = f" ({hint})" if hint else ""
    while True:
        value = input(f"{label}{suffix}: ").strip()
        if value:
            return value
        print("  ...required, please enter a value.")


def build_entry(args: argparse.Namespace) -> dict:
    """Assemble a company dict from flags, prompting for anything missing."""
    name = args.name or _prompt("Company name")

    platform = args.platform
    if not platform:
        print(f"Platforms: {', '.join(sorted(REQUIRED_FIELDS))}")
        platform = _prompt("Platform")
    if platform not in REQUIRED_FIELDS:
        raise SystemExit(
            f"Unknown platform {platform!r}; expected one of "
            f"{', '.join(sorted(REQUIRED_FIELDS))}"
        )

    entry: dict = {"name": name, "platform": platform}
    for field in REQUIRED_FIELDS[platform]:
        value = getattr(args, field, None) or _prompt(field, FIELD_HELP.get(field, ""))
        entry[field] = value
    return entry


def add_to_file(entry: dict, path: Path) -> None:
    """Append `entry` to the companies list in `path`, creating it if needed."""
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    else:
        data = {}
    if not isinstance(data, dict):
        raise SystemExit(f"{path}: expected a YAML mapping at the top level")

    companies = data.setdefault("companies", [])
    if any(c.get("name") == entry["name"] for c in companies):
        raise SystemExit(f"A company named {entry['name']!r} is already in {path.name}.")
    companies.append(entry)

    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="watcher.add", description=__doc__)
    parser.add_argument("--name")
    parser.add_argument("--platform", choices=sorted(REQUIRED_FIELDS))
    parser.add_argument("--token")
    parser.add_argument("--tenant")
    parser.add_argument("--dc")
    parser.add_argument("--site")
    parser.add_argument("--url")
    parser.add_argument("--config", help="path to companies.yaml")
    args = parser.parse_args(argv)

    path = Path(args.config) if args.config else DEFAULT_CONFIG_PATH
    entry = build_entry(args)
    add_to_file(entry, path)

    print(f"\nAdded {entry['name']!r} ({entry['platform']}) to {path}.")
    print("Next: run `python -m watcher.main --dry-run` to check it, then paste the")
    print("updated file into your COMPANIES_YAML secret (or re-run the workflow).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

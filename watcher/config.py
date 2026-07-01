"""Load and validate the company list.

Source precedence:
  1. The COMPANIES_YAML environment variable (the GitHub Secret) if set — this
     keeps the list out of the (public) repo entirely.
  2. Otherwise the local companies.yaml file, used for local testing.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "companies.yaml"
ENV_VAR = "COMPANIES_YAML"

REQUIRED_FIELDS = {
    "greenhouse": ["token"],
    "lever": ["token"],
    "ashby": ["token"],
    "smartrecruiters": ["token"],
    "workday": ["tenant", "dc", "site"],
    "github_list": ["url"],  # raw URL of a community listings.json
}


class ConfigError(Exception):
    pass


def load(path: Path = DEFAULT_CONFIG_PATH) -> dict:
    env_yaml = os.environ.get(ENV_VAR)
    if env_yaml and env_yaml.strip():
        source = f"${ENV_VAR}"
        data = yaml.safe_load(env_yaml) or {}
    else:
        if not path.exists():
            raise ConfigError(
                f"No company list: set the {ENV_VAR} env var or create {path}"
            )
        source = str(path)
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

    if not isinstance(data, dict):
        raise ConfigError(f"{source}: expected a YAML mapping at the top level")

    companies = data.get("companies")
    if not companies:
        raise ConfigError(f"{source}: no 'companies' list found")

    seen_names: set[str] = set()
    for i, c in enumerate(companies):
        name = c.get("name")
        platform = c.get("platform")
        if not name:
            raise ConfigError(f"companies[{i}] is missing 'name'")
        if name in seen_names:
            raise ConfigError(f"duplicate company name: {name!r}")
        seen_names.add(name)
        if platform not in REQUIRED_FIELDS:
            raise ConfigError(
                f"{name}: unknown platform {platform!r}; "
                f"expected one of {', '.join(sorted(REQUIRED_FIELDS))}"
            )
        for field in REQUIRED_FIELDS[platform]:
            if not c.get(field):
                raise ConfigError(f"{name}: platform '{platform}' requires '{field}'")

    return data

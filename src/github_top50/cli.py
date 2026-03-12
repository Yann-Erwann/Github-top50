"""CLI entrypoint for generating the GitHub Top 50 README section."""

from __future__ import annotations

import argparse
import time
from collections.abc import Sequence
from pathlib import Path

from github_top50.config import (
    CATEGORIES,
    CATEGORY_PER_PAGE,
    END,
    GLOBAL_QUERY,
    PER_PAGE,
    README_PATH,
    START,
)
from github_top50.services.github_client import search_repos
from github_top50.services.readme_builder import build_generated_content, update_readme


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser for the README generator."""
    parser = argparse.ArgumentParser(
        description="Generate the GitHub Top 50 section inside a README file."
    )
    parser.add_argument(
        "--readme-path",
        type=Path,
        default=README_PATH,
        help="Path to the README file to update.",
    )
    return parser


def _fetch_category_items() -> dict[str, list[dict[str, object]]]:
    category_items: dict[str, list[dict[str, object]]] = {}
    for index, category in enumerate(CATEGORIES):
        print(f"Fetching {category['title']}...")
        category_items[category["tag"]] = search_repos(
            category["query"], CATEGORY_PER_PAGE
        )
        if index < len(CATEGORIES) - 1:
            time.sleep(2)
    return category_items


def main(argv: Sequence[str] | None = None) -> None:
    """Generate the README Top 50 section in place."""
    args = build_parser().parse_args(list(argv) if argv is not None else [])
    print("Fetching global top 50...")
    global_items = search_repos(GLOBAL_QUERY, PER_PAGE)
    category_items = _fetch_category_items()
    generated = build_generated_content(global_items, CATEGORIES, category_items)
    update_readme(args.readme_path, START, END, generated)
    print("README.md mis à jour.")

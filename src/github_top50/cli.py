"""CLI entrypoint for generating the GitHub Top 50 README section."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from github_top50.application.generate_top50 import GenerateTop50ReadmeUseCase
from github_top50.config import (
    CATEGORIES,
    CATEGORY_PER_PAGE,
    END,
    GLOBAL_QUERY,
    HISTORY_DIR,
    LATEST_SNAPSHOT_PATH,
    PER_PAGE,
    README_PATH,
    START,
)
from github_top50.services.github_client import GitHubRepositoryGateway
from github_top50.services.history_store import SnapshotStore


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


def build_use_case() -> GenerateTop50ReadmeUseCase:
    """Build the application service that generates the README."""
    return GenerateTop50ReadmeUseCase(
        categories=CATEGORIES,
        repository_gateway=GitHubRepositoryGateway(),
        global_query=GLOBAL_QUERY,
        per_page=PER_PAGE,
        category_per_page=CATEGORY_PER_PAGE,
        snapshot_store=SnapshotStore(
            latest_snapshot_path=LATEST_SNAPSHOT_PATH,
            history_dir=HISTORY_DIR,
        ),
    )


def _fetch_category_items() -> dict[str, list[object]]:
    """Compatibility wrapper for tests around the use case fetch step."""
    return build_use_case().fetch_category_items()


def main(argv: Sequence[str] | None = None) -> None:
    """Generate the README Top 50 section in place."""
    args = build_parser().parse_args(list(argv) if argv is not None else [])
    build_use_case().run(
        readme_path=args.readme_path,
        start_marker=START,
        end_marker=END,
    )

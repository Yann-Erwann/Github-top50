"""Compatibility wrapper around the packaged GitHub Top 50 implementation."""

from __future__ import annotations

import sys
from pathlib import Path

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from github_top50 import (  # noqa: E402
    CATEGORIES,
    CATEGORY_PER_PAGE,
    END,
    GLOBAL_QUERY,
    PER_PAGE,
    README_PATH,
    START,
    build_table,
    build_toc,
    main,
    search_repos,
    slugify,
    update_readme,
)
from github_top50.services import github_client as _github_client  # noqa: E402

requests = _github_client.requests
time = _github_client.time

__all__ = [
    "CATEGORIES",
    "CATEGORY_PER_PAGE",
    "END",
    "GLOBAL_QUERY",
    "PER_PAGE",
    "README_PATH",
    "START",
    "build_table",
    "build_toc",
    "main",
    "requests",
    "search_repos",
    "slugify",
    "time",
    "update_readme",
]


if __name__ == "__main__":
    main(sys.argv[1:])

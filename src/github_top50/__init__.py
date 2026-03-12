"""Public API for the GitHub Top 50 generator."""

from github_top50.cli import main
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
from github_top50.services.readme_builder import (
    build_generated_content,
    build_table,
    build_toc,
    update_readme,
)
from github_top50.utils.slug import slugify

__all__ = [
    "CATEGORIES",
    "CATEGORY_PER_PAGE",
    "END",
    "GLOBAL_QUERY",
    "PER_PAGE",
    "README_PATH",
    "START",
    "build_generated_content",
    "build_table",
    "build_toc",
    "main",
    "search_repos",
    "slugify",
    "update_readme",
]

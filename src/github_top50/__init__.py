"""Public API for the GitHub Top 50 generator."""

from github_top50.application.generate_top50 import GenerateTop50ReadmeUseCase
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
from github_top50.domain.models import CategoryDefinition, ReadmeSection, Repository
from github_top50.services.github_client import GitHubRepositoryGateway, search_repos
from github_top50.services.readme_builder import (
    build_category_section,
    build_generated_content,
    build_table,
    build_toc,
    create_category_section,
    update_readme,
)
from github_top50.utils.slug import slugify

__all__ = [
    "CATEGORIES",
    "CATEGORY_PER_PAGE",
    "CategoryDefinition",
    "END",
    "GenerateTop50ReadmeUseCase",
    "GLOBAL_QUERY",
    "GitHubRepositoryGateway",
    "PER_PAGE",
    "README_PATH",
    "ReadmeSection",
    "Repository",
    "START",
    "build_category_section",
    "build_generated_content",
    "build_table",
    "build_toc",
    "create_category_section",
    "main",
    "search_repos",
    "slugify",
    "update_readme",
]

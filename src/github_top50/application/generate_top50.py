"""Use case for generating and updating the README Top 50 section."""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from github_top50.domain.models import (
    CategoryDefinition,
    CategoryLike,
    Repository,
    to_category_definition,
)
from github_top50.services.readme_builder import build_generated_content, update_readme

SleepFunc = Callable[[float], None]


class RepositoryGateway(Protocol):
    """Port implemented by adapters that can search repositories."""

    def search_repositories(self, query: str, per_page: int) -> list[Repository]:
        """Return repositories matching the query."""


@dataclass(slots=True)
class GenerateTop50ReadmeUseCase:
    """Orchestrate the full README generation flow."""

    categories: Sequence[CategoryLike]
    repository_gateway: RepositoryGateway
    global_query: str
    per_page: int
    category_per_page: int
    sleep_func: SleepFunc = time.sleep

    def _normalize_categories(self) -> tuple[CategoryDefinition, ...]:
        return tuple(to_category_definition(category) for category in self.categories)

    def fetch_category_items(
        self,
        categories: Sequence[CategoryDefinition] | None = None,
    ) -> dict[str, list[Repository]]:
        """Fetch repositories for each configured category."""
        resolved_categories = tuple(categories or self._normalize_categories())
        category_items: dict[str, list[Repository]] = {}

        for index, category in enumerate(resolved_categories):
            print(f"Fetching {category.title}...")
            category_items[category.tag] = self.repository_gateway.search_repositories(
                category.query, self.category_per_page
            )
            if index < len(resolved_categories) - 1:
                self.sleep_func(2)

        return category_items

    def run(
        self,
        *,
        readme_path: Path,
        start_marker: str,
        end_marker: str,
    ) -> str:
        """Generate README content and write it in place."""
        categories = self._normalize_categories()
        print("Fetching global top 50...")
        global_items = self.repository_gateway.search_repositories(
            self.global_query, self.per_page
        )
        category_items = self.fetch_category_items(categories)
        generated = build_generated_content(global_items, categories, category_items)
        update_readme(readme_path, start_marker, end_marker, generated)
        print("README.md mis à jour.")
        return generated

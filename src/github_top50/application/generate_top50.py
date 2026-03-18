"""Use case for generating and updating the README Top 50 section."""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from github_top50.domain.models import (
    CategoryDefinition,
    CategoryLike,
    Repository,
    to_category_definition,
)
from github_top50.services.history_store import SnapshotStore, apply_rank_changes
from github_top50.services.readme_builder import build_generated_content, update_readme

SleepFunc = Callable[[float], None]
NowFunc = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


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
    snapshot_store: SnapshotStore | None = None
    sleep_func: SleepFunc = time.sleep
    now_func: NowFunc = _utc_now

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
        previous_snapshot = (
            self.snapshot_store.load_latest()
            if self.snapshot_store is not None
            else None
        )

        print("Fetching global top 50...")
        global_items = self.repository_gateway.search_repositories(
            self.global_query, self.per_page
        )
        category_items = self.fetch_category_items(categories)

        global_items = apply_rank_changes(
            global_items,
            previous_snapshot.global_items
            if previous_snapshot is not None
            else global_items,
        )
        previous_category_items = (
            previous_snapshot.category_items if previous_snapshot is not None else {}
        )
        category_items = {
            tag: apply_rank_changes(
                items,
                previous_category_items.get(tag)
                if previous_snapshot is not None
                else items,
            )
            for tag, items in category_items.items()
        }

        generated = build_generated_content(global_items, categories, category_items)
        update_readme(readme_path, start_marker, end_marker, generated)
        if self.snapshot_store is not None:
            history_path = self.snapshot_store.save(
                captured_at=self.now_func(),
                global_items=global_items,
                categories=categories,
                category_items=category_items,
            )
            print(f"Snapshot enregistré dans {history_path}.")
        print("README.md mis à jour.")
        return generated

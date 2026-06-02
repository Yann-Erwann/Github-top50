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
    PeriodDefinition,
    Repository,
    to_category_definition,
)
from github_top50.services.history_store import SnapshotStore, apply_rank_changes
from github_top50.services.periods import build_created_period_query
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
    periods: Sequence[PeriodDefinition] = ()
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

    def fetch_period_items(
        self,
        captured_at: datetime,
    ) -> dict[str, list[Repository]]:
        """Fetch top repositories created during each bounded ranking period."""
        bounded_periods = tuple(
            period for period in self.periods if not period.all_time
        )
        period_items: dict[str, list[Repository]] = {}

        for index, period in enumerate(bounded_periods):
            query = build_created_period_query(captured_at, period)
            print(f"Fetching repositories created during {period.label}...")
            period_items[period.id] = self.repository_gateway.search_repositories(
                query,
                self.per_page,
            )
            if index < len(bounded_periods) - 1:
                self.sleep_func(2)

        return period_items

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
        captured_at = self.now_func()

        print("Fetching global top 50...")
        global_items = self.repository_gateway.search_repositories(
            self.global_query, self.per_page
        )
        if self.periods:
            self.sleep_func(2)
        period_items = self.fetch_period_items(captured_at)
        if period_items:
            self.sleep_func(2)
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
        previous_period_items = (
            previous_snapshot.period_items if previous_snapshot is not None else {}
        )
        period_items = {
            period_id: apply_rank_changes(
                items,
                previous_period_items.get(period_id, items),
            )
            for period_id, items in period_items.items()
        }

        generated = build_generated_content(global_items, categories, category_items)
        update_readme(readme_path, start_marker, end_marker, generated)
        if self.snapshot_store is not None:
            history_path = self.snapshot_store.save(
                captured_at=captured_at,
                global_items=global_items,
                categories=categories,
                category_items=category_items,
                periods=tuple(self.periods),
                period_items=period_items,
            )
            print(f"Snapshot enregistré dans {history_path}.")
        print("README.md mis à jour.")
        return generated

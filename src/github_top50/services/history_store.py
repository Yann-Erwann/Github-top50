"""Persistent snapshot storage and ranking delta helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from github_top50.domain.models import CategoryDefinition, Repository


@dataclass(frozen=True, slots=True)
class Top50Snapshot:
    """Stored snapshot of the global and per-category rankings."""

    captured_at: str
    global_items: tuple[Repository, ...]
    category_items: dict[str, tuple[Repository, ...]]


def _repository_key(repository: Repository) -> int | str:
    return repository.id if repository.id is not None else repository.full_name


def apply_rank_changes(
    items: list[Repository],
    previous_items: tuple[Repository, ...] | list[Repository] | None = None,
) -> list[Repository]:
    """Annotate repositories with their current and previous ranks."""
    previous_rank_by_key: dict[int | str, int] = {}
    for fallback_rank, previous in enumerate(previous_items or (), start=1):
        previous_rank = previous.rank or fallback_rank
        previous_rank_by_key[_repository_key(previous)] = previous_rank

    return [
        replace(
            repository,
            rank=current_rank,
            previous_rank=previous_rank_by_key.get(_repository_key(repository)),
        )
        for current_rank, repository in enumerate(items, start=1)
    ]


class SnapshotStore:
    """Store Top 50 snapshots on disk in JSON form."""

    def __init__(self, *, latest_snapshot_path: Path, history_dir: Path) -> None:
        self._latest_snapshot_path = latest_snapshot_path
        self._history_dir = history_dir

    def load_latest(self) -> Top50Snapshot | None:
        """Return the latest snapshot if one exists."""
        if not self._latest_snapshot_path.exists():
            return None

        payload = json.loads(self._latest_snapshot_path.read_text(encoding="utf-8"))
        return Top50Snapshot(
            captured_at=payload["captured_at"],
            global_items=tuple(self._deserialize_items(payload["global"]["items"])),
            category_items={
                tag: tuple(self._deserialize_items(section["items"]))
                for tag, section in payload["categories"].items()
            },
        )

    def save(
        self,
        *,
        captured_at: datetime,
        global_items: list[Repository],
        categories: tuple[CategoryDefinition, ...],
        category_items: dict[str, list[Repository]],
    ) -> Path:
        """Persist the latest snapshot and an immutable history entry."""
        timestamp = captured_at.astimezone(timezone.utc).replace(microsecond=0)
        serialized = self._serialize_snapshot(
            captured_at=timestamp,
            global_items=global_items,
            categories=categories,
            category_items=category_items,
        )

        self._latest_snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        self._history_dir.mkdir(parents=True, exist_ok=True)

        content = json.dumps(serialized, ensure_ascii=False, indent=2) + "\n"
        self._latest_snapshot_path.write_text(content, encoding="utf-8")

        history_name = timestamp.strftime("%Y-%m-%dT%H-%M-%SZ.json")
        history_path = self._history_dir / history_name
        history_path.write_text(content, encoding="utf-8")
        return history_path

    def _serialize_snapshot(
        self,
        *,
        captured_at: datetime,
        global_items: list[Repository],
        categories: tuple[CategoryDefinition, ...],
        category_items: dict[str, list[Repository]],
    ) -> dict[str, Any]:
        return {
            "captured_at": captured_at.isoformat().replace("+00:00", "Z"),
            "global": {"items": self._serialize_items(global_items)},
            "categories": {
                category.tag: {
                    "title": category.title,
                    "items": self._serialize_items(category_items[category.tag]),
                }
                for category in categories
            },
        }

    @staticmethod
    def _serialize_items(items: list[Repository]) -> list[dict[str, Any]]:
        return [
            {
                "id": repository.id,
                "full_name": repository.full_name,
                "html_url": repository.html_url,
                "stargazers_count": repository.stargazers_count,
                "language": repository.language,
                "description": repository.description,
                "rank": repository.rank,
                "previous_rank": repository.previous_rank,
            }
            for repository in items
        ]

    @staticmethod
    def _deserialize_items(items: list[dict[str, Any]]) -> list[Repository]:
        return [
            Repository(
                id=item.get("id"),
                full_name=item["full_name"],
                html_url=item["html_url"],
                stargazers_count=item["stargazers_count"],
                language=item.get("language"),
                description=item.get("description"),
                rank=item.get("rank"),
                previous_rank=item.get("previous_rank"),
            )
            for item in items
        ]

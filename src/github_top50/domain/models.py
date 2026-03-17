"""Typed domain objects for GitHub Top 50."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, TypeAlias, TypedDict


class Category(TypedDict):
    """A README category backed by a GitHub search query."""

    title: str
    tag: str
    query: str


class RepositoryItem(TypedDict, total=False):
    """Subset of GitHub repository fields rendered into the README."""

    full_name: str
    html_url: str
    stargazers_count: int
    language: str | None
    description: str | None


@dataclass(frozen=True, slots=True)
class CategoryDefinition:
    """Immutable category definition used by the application layer."""

    title: str
    tag: str
    query: str


@dataclass(frozen=True, slots=True)
class Repository:
    """Immutable repository data rendered into the README."""

    full_name: str
    html_url: str
    stargazers_count: int
    language: str | None
    description: str | None = None


@dataclass(frozen=True, slots=True)
class ReadmeSection:
    """Markdown section with optional stable markers."""

    title: str
    content: str
    heading_level: int = 3
    anchor: str | None = None
    start_marker: str | None = None
    end_marker: str | None = None

    def render(self) -> str:
        """Render the section into markdown."""
        lines: list[str] = []
        if self.anchor:
            lines.append(f'<a id="{self.anchor}"></a>')
        lines.extend([f"{'#' * self.heading_level} {self.title}", ""])
        if self.start_marker and self.end_marker:
            lines.extend([self.start_marker, self.content, self.end_marker])
        else:
            lines.append(self.content)
        return "\n".join(lines)


CategoryLike: TypeAlias = CategoryDefinition | Mapping[str, str]
RepositoryLike: TypeAlias = Repository | Mapping[str, Any]


def to_category_definition(category: CategoryLike) -> CategoryDefinition:
    """Normalize a category-like input into a dataclass."""
    if isinstance(category, CategoryDefinition):
        return category

    return CategoryDefinition(
        title=category["title"],
        tag=category["tag"],
        query=category["query"],
    )


def to_repository(item: RepositoryLike) -> Repository:
    """Normalize a repository-like input into a dataclass."""
    if isinstance(item, Repository):
        return item

    return Repository(
        full_name=item["full_name"],
        html_url=item["html_url"],
        stargazers_count=item["stargazers_count"],
        language=item.get("language"),
        description=item.get("description"),
    )

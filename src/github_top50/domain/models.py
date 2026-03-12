"""Typed domain objects for GitHub Top 50."""

from __future__ import annotations

from typing import TypedDict


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

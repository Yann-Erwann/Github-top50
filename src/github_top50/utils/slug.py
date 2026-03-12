"""Helpers for generating GitHub-compatible anchors."""

import re

_NON_ANCHOR_CHARS = re.compile(r"[^\w\s-]")
_WHITESPACE_RUNS = re.compile(r"[\s]+")


def slugify(title: str) -> str:
    """Convert a markdown heading to a GitHub-compatible anchor."""
    slug = _NON_ANCHOR_CHARS.sub("", title).strip().lower()
    return _WHITESPACE_RUNS.sub("-", slug)

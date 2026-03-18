"""Helpers for generating stable README anchor identifiers."""

from __future__ import annotations

import re
import unicodedata

_NON_ALNUM_RUNS = re.compile(r"[^a-z0-9]+")


def slugify(title: str) -> str:
    """Convert a heading title into a stable ASCII anchor identifier."""
    normalized = unicodedata.normalize("NFKD", title)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return _NON_ALNUM_RUNS.sub("-", ascii_text).strip("-")

"""GitHub API client helpers."""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from typing import Any

import requests

API_URL = "https://api.github.com/search/repositories"
RATE_LIMIT_WAIT_SECONDS = 60
RequestGet = Callable[..., requests.Response]
SleepFunc = Callable[[float], None]


def build_headers(token: str | None = None) -> dict[str, str]:
    """Build GitHub API headers from an optional token."""
    headers = {"Accept": "application/vnd.github+json"}
    resolved_token = token or os.getenv("GITHUB_TOKEN")
    if resolved_token:
        headers["Authorization"] = f"Bearer {resolved_token}"
    return headers


def search_repos(
    query: str,
    per_page: int,
    *,
    request_get: RequestGet | None = None,
    sleep_func: SleepFunc | None = None,
    token: str | None = None,
) -> list[dict[str, Any]]:
    """Search GitHub repositories and return the raw items list."""
    request_get = request_get or requests.get
    sleep_func = sleep_func or time.sleep
    params = {
        "q": query,
        "sort": "stars",
        "order": "desc",
        "per_page": per_page,
        "page": 1,
    }
    headers = build_headers(token)

    response = request_get(API_URL, headers=headers, params=params, timeout=30)
    if response.status_code == 403:
        print(f"Rate limited, waiting {RATE_LIMIT_WAIT_SECONDS}s...")
        sleep_func(RATE_LIMIT_WAIT_SECONDS)
        response = request_get(API_URL, headers=headers, params=params, timeout=30)

    response.raise_for_status()
    return response.json().get("items", [])

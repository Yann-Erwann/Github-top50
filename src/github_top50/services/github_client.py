"""GitHub API client helpers."""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from typing import Any

import requests

from github_top50.domain.models import Repository, to_repository

API_URL = "https://api.github.com/search/repositories"
RATE_LIMIT_WAIT_SECONDS = 60
RequestGet = Callable[..., requests.Response]
SleepFunc = Callable[[float], None]


def build_headers(token: str | None = None) -> dict[str, str]:
    """Build GitHub API headers from an optional token."""
    headers = {"Accept": "application/vnd.github+json"}
    resolved_token = token or os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if resolved_token:
        headers["Authorization"] = f"Bearer {resolved_token}"
    return headers


def get_rate_limit_wait_seconds(response: requests.Response) -> int | None:
    """Return the retry delay when GitHub explicitly signals rate limiting."""
    if response.status_code not in {403, 429}:
        return None

    retry_after = response.headers.get("Retry-After")
    if retry_after:
        try:
            return max(1, int(float(retry_after)))
        except ValueError:
            pass

    if response.headers.get("X-RateLimit-Remaining") != "0":
        return None

    reset_at = response.headers.get("X-RateLimit-Reset")
    if not reset_at:
        return RATE_LIMIT_WAIT_SECONDS

    try:
        return max(1, int(reset_at) - int(time.time()))
    except ValueError:
        return RATE_LIMIT_WAIT_SECONDS


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
    wait_seconds = get_rate_limit_wait_seconds(response)
    if wait_seconds is not None:
        print(f"Rate limited, waiting {wait_seconds}s...")
        sleep_func(wait_seconds)
        response = request_get(API_URL, headers=headers, params=params, timeout=30)

    response.raise_for_status()
    return response.json().get("items", [])


class GitHubRepositoryGateway:
    """Adapter that exposes typed repository search results."""

    def __init__(
        self,
        *,
        request_get: RequestGet | None = None,
        sleep_func: SleepFunc | None = None,
        token: str | None = None,
    ) -> None:
        self._request_get = request_get
        self._sleep_func = sleep_func
        self._token = token

    def search_repositories(self, query: str, per_page: int) -> list[Repository]:
        """Search GitHub and normalize results into domain objects."""
        raw_items = search_repos(
            query,
            per_page,
            request_get=self._request_get,
            sleep_func=self._sleep_func,
            token=self._token,
        )
        return [to_repository(item) for item in raw_items]

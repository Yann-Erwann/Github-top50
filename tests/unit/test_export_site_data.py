import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from scripts import export_site_data as exporter

from github_top50.domain.models import (
    CategoryDefinition,
    HostingRecommendationDefinition,
)


class FakeGitHubResponse:
    def __init__(
        self,
        payload,
        *,
        links=None,
        status_code=200,
        headers=None,
    ):
        self._payload = payload
        self.links = links or {}
        self.status_code = status_code
        self.headers = headers or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def _empty_movements() -> dict[str, None]:
    return {period.id: None for period in exporter.PERIODS}


def _starred_page(start_at: datetime, count: int) -> list[dict[str, str]]:
    return [
        {"starred_at": (start_at + timedelta(minutes=index)).isoformat()}
        for index in range(count)
    ]


def _global_period_rankings() -> dict[str, int | None]:
    rankings = _empty_movements()
    rankings["all"] = 1
    return rankings


def _global_period_stars(stars: int) -> dict[str, int | None]:
    totals = _empty_movements()
    totals["all"] = stars
    return totals


def _make_snapshot() -> dict[str, object]:
    return {
        "captured_at": "2026-04-04T07:36:12Z",
        "global": {
            "items": [
                {
                    "id": 1,
                    "full_name": "owner/global-one",
                    "html_url": "https://github.com/owner/global-one",
                    "stargazers_count": 100,
                    "language": "Python",
                    "description": "Global repository",
                    "rank": 1,
                }
            ]
        },
        "categories": {
            "PYTHON": {
                "title": "Legacy title that should be ignored",
                "items": [
                    {
                        "id": 2,
                        "full_name": "owner/python-lib",
                        "html_url": "https://github.com/owner/python-lib",
                        "stargazers_count": 42,
                        "language": "Python",
                        "description": "Python repository",
                        "rank": 1,
                    }
                ],
            },
            "REACT": {
                "title": "Another legacy title",
                "items": [
                    {
                        "id": 3,
                        "full_name": "owner/react-app",
                        "html_url": "https://github.com/owner/react-app",
                        "stargazers_count": 24,
                        "language": "TypeScript",
                        "description": "React repository",
                        "rank": 1,
                    }
                ],
            },
        },
    }


@pytest.fixture
def export_config(monkeypatch):
    monkeypatch.setattr(
        exporter,
        "CATEGORIES",
        (
            CategoryDefinition(
                title="Python picks",
                tag="PYTHON",
                query="language:python stars:>10",
            ),
            CategoryDefinition(
                title="React picks",
                tag="REACT",
                query="topic:react stars:>10",
            ),
        ),
    )
    monkeypatch.setattr(
        exporter,
        "HOSTING_RECOMMENDATIONS",
        (
            HostingRecommendationDefinition(
                stack="React / Next.js",
                hosting="Vercel",
                url="https://vercel.com/docs",
                notes="Preview and static hosting.",
            ),
        ),
    )
    monkeypatch.setattr(exporter, "GLOBAL_QUERY", "stars:>10")
    monkeypatch.setattr(exporter, "PER_PAGE", 50)
    monkeypatch.setattr(exporter, "CATEGORY_PER_PAGE", 10)


def test_build_site_payload_combines_snapshot_and_static_config(export_config):
    payload = exporter.build_site_payload(
        _make_snapshot(),
        input_path=Path("data/top50/latest.json"),
        generated_at="2026-04-05T10:00:00Z",
    )

    assert payload["snapshot"] == {
        "capturedAt": "2026-04-04T07:36:12Z",
        "label": "Snapshot du 2026-04-04",
        "source": "data/top50/latest.json",
    }
    assert payload["global"]["title"] == "Top 50 GitHub Stars"
    assert payload["global"]["highlights"][0]["fullName"] == "owner/global-one"
    assert payload["global"]["items"][0]["owner"] == "owner"
    assert payload["global"]["items"][0]["name"] == "global-one"
    assert payload["global"]["items"][0]["movements"] == _empty_movements()
    assert payload["global"]["items"][0]["periodRankings"] == _global_period_rankings()
    assert payload["global"]["items"][0]["periodStarsGained"] == _global_period_stars(
        100
    )
    assert payload["periods"][0]["id"] == "7d"
    assert payload["periods"][0]["available"] is False
    assert payload["periods"][-1]["id"] == "all"
    assert payload["categories"] == [
        {
            "tag": "PYTHON",
            "title": "Python picks",
            "query": "language:python stars:>10",
            "description": (
                "Repos les plus suivis pour Python picks, "
                "avec un focus sur les stacks et outils qui structurent l'écosystème."
            ),
            "accent": "aurora",
            "items": [
                {
                    "id": 2,
                    "rank": 1,
                    "previousRank": None,
                    "movements": _empty_movements(),
                    "periodRankings": _empty_movements(),
                    "periodStarsGained": _empty_movements(),
                    "fullName": "owner/python-lib",
                    "owner": "owner",
                    "name": "python-lib",
                    "htmlUrl": "https://github.com/owner/python-lib",
                    "stargazersCount": 42,
                    "language": "Python",
                    "description": "Python repository",
                }
            ],
        },
        {
            "tag": "REACT",
            "title": "React picks",
            "query": "topic:react stars:>10",
            "description": (
                "Repos les plus suivis pour React picks, "
                "avec un focus sur les stacks et outils qui structurent l'écosystème."
            ),
            "accent": "cobalt",
            "items": [
                {
                    "id": 3,
                    "rank": 1,
                    "previousRank": None,
                    "movements": _empty_movements(),
                    "periodRankings": _empty_movements(),
                    "periodStarsGained": _empty_movements(),
                    "fullName": "owner/react-app",
                    "owner": "owner",
                    "name": "react-app",
                    "htmlUrl": "https://github.com/owner/react-app",
                    "stargazersCount": 24,
                    "language": "TypeScript",
                    "description": "React repository",
                }
            ],
        },
    ]
    assert payload["hosting"] == [
        {
            "stack": "React / Next.js",
            "hosting": "Vercel",
            "url": "https://vercel.com/docs",
            "notes": "Preview and static hosting.",
            "fit": "Frontend statique et previews",
        }
    ]
    assert payload["stats"] == {
        "generatedAt": "2026-04-05T10:00:00Z",
        "totalStars": 100,
        "repositoryCount": 1,
        "categoryCount": 2,
        "hostingCount": 1,
        "topLanguage": {"name": "Python", "repositoryCount": 1},
        "languages": [{"name": "Python", "repositoryCount": 1}],
        "globalQuery": "stars:>10",
        "categoryLimit": 10,
        "globalLimit": 50,
    }


def test_github_star_history_client_counts_stargazers_at_timestamp():
    page_one = _starred_page(datetime(2026, 1, 1, tzinfo=UTC), 100)
    page_two = _starred_page(datetime(2026, 1, 1, 1, 40, tzinfo=UTC), 50)
    calls = []

    def fake_get(url, *, headers, params, timeout):
        calls.append((url, headers, params, timeout))
        page = params["page"]
        payload = page_one if page == 1 else page_two
        links = (
            {
                "last": {
                    "url": (
                        "https://api.github.com/repos/owner/repo/stargazers"
                        "?per_page=100&page=2"
                    )
                }
            }
            if page == 1
            else {}
        )
        return FakeGitHubResponse(payload, links=links)

    client = exporter.GitHubStarHistoryClient(
        token="token",
        request_get=fake_get,
    )

    count = client.count_stargazers_at(
        "owner/repo",
        datetime(2026, 1, 1, 2, 4, tzinfo=UTC),
    )
    cached_count = client.count_stargazers_at(
        "owner/repo",
        datetime(2026, 1, 1, 2, 4, tzinfo=UTC),
    )

    assert count == 125
    assert cached_count == 125
    assert len(calls) == 2
    assert calls[0][0] == "https://api.github.com/repos/owner/repo/stargazers"
    assert calls[0][1]["Accept"] == "application/vnd.github.star+json"
    assert calls[0][1]["Authorization"] == "Bearer token"
    assert calls[0][2] == {"per_page": 100, "page": 1}
    assert calls[0][3] == 30


def test_github_star_history_client_handles_empty_and_capped_pages():
    full_page = _starred_page(datetime(2026, 1, 1, tzinfo=UTC), 100)
    empty_calls = []

    empty_client = exporter.GitHubStarHistoryClient(
        request_get=lambda *args, **kwargs: (
            empty_calls.append((args, kwargs)) or FakeGitHubResponse([])
        ),
    )
    capped_client = exporter.GitHubStarHistoryClient(
        request_get=lambda *args, **kwargs: FakeGitHubResponse(full_page),
    )

    assert (
        empty_client.count_stargazers_at(
            "owner/empty",
            datetime(2026, 1, 1, tzinfo=UTC),
        )
        == 0
    )
    assert (
        capped_client.count_stargazers_at(
            "owner/capped",
            datetime(2026, 1, 2, tzinfo=UTC),
        )
        is None
    )
    assert empty_calls


def test_github_star_history_client_retries_rate_limit_and_rejects_bad_payload():
    responses = [
        FakeGitHubResponse(
            [],
            status_code=403,
            headers={
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": "1",
            },
        ),
        FakeGitHubResponse({"unexpected": "payload"}),
    ]
    sleep_calls = []

    def fake_get(*args, **kwargs):
        return responses.pop(0)

    client = exporter.GitHubStarHistoryClient(
        request_get=fake_get,
        sleep_func=sleep_calls.append,
    )

    with pytest.raises(ValueError, match="Unexpected GitHub stargazers payload"):
        client.count_stargazers_at(
            "owner/repo",
            datetime(2026, 1, 1, tzinfo=UTC),
        )

    assert sleep_calls == [1]


def test_build_site_payload_uses_previous_snapshot_for_rank_movements(export_config):
    previous_snapshot = _make_snapshot()
    previous_snapshot["captured_at"] = "2026-04-03T07:36:12Z"
    previous_snapshot["global"]["items"][0]["rank"] = 4
    previous_snapshot["categories"]["PYTHON"]["items"][0]["rank"] = 2
    previous_snapshot["categories"]["REACT"]["items"][0]["id"] = 99
    previous_snapshot["categories"]["REACT"]["items"][0]["full_name"] = (
        "owner/old-react"
    )

    payload = exporter.build_site_payload(
        _make_snapshot(),
        previous_snapshot=previous_snapshot,
    )

    assert payload["global"]["items"][0]["previousRank"] == 4
    assert payload["global"]["items"][0]["movements"]["7d"] == 4
    assert payload["global"]["items"][0]["periodRankings"]["7d"] == 1
    assert payload["global"]["items"][0]["periodStarsGained"]["7d"] == 0
    assert payload["categories"][0]["items"][0]["previousRank"] == 2
    assert payload["categories"][0]["items"][0]["movements"]["7d"] == 2
    assert payload["categories"][0]["items"][0]["periodRankings"]["7d"] == 1
    assert payload["categories"][0]["items"][0]["periodStarsGained"]["7d"] == 0
    assert payload["categories"][1]["items"][0]["previousRank"] is None
    assert payload["categories"][1]["items"][0]["movements"]["7d"] is None
    assert payload["categories"][1]["items"][0]["periodRankings"]["7d"] is None
    assert payload["categories"][1]["items"][0]["periodStarsGained"]["7d"] is None


def test_build_site_payload_uses_star_history_for_missing_category_baseline(
    export_config,
):
    previous_snapshot = _make_snapshot()
    previous_snapshot["captured_at"] = "2026-03-28T07:36:12Z"
    previous_snapshot["categories"]["PYTHON"]["items"][0]["id"] = 99
    previous_snapshot["categories"]["PYTHON"]["items"][0]["full_name"] = (
        "owner/old-python-lib"
    )

    payload = exporter.build_site_payload(
        _make_snapshot(),
        period_snapshots={"7d": previous_snapshot},
        star_history_baselines={"7d": {"owner/python-lib": 30}},
    )

    python_item = payload["categories"][0]["items"][0]
    assert python_item["periodRankings"]["7d"] == 1
    assert python_item["periodStarsGained"]["7d"] == 12


def test_build_site_payload_ranks_repositories_by_period_star_gains(export_config):
    snapshot = _make_snapshot()
    snapshot["global"]["items"].append(
        {
            "id": 4,
            "full_name": "owner/global-two",
            "html_url": "https://github.com/owner/global-two",
            "stargazers_count": 90,
            "language": "Python",
            "description": "Second global repository",
            "rank": 2,
        }
    )
    previous_snapshot = _make_snapshot()
    previous_snapshot["captured_at"] = "2026-04-03T07:36:12Z"
    previous_snapshot["global"]["items"][0]["stargazers_count"] = 99
    previous_snapshot["global"]["items"].append(
        {
            "id": 4,
            "full_name": "owner/global-two",
            "html_url": "https://github.com/owner/global-two",
            "stargazers_count": 70,
            "language": "Python",
            "description": "Second global repository",
            "rank": 2,
        }
    )

    payload = exporter.build_site_payload(
        snapshot,
        previous_snapshot=previous_snapshot,
    )
    repositories = {item["fullName"]: item for item in payload["global"]["items"]}

    assert repositories["owner/global-two"]["periodRankings"]["7d"] == 1
    assert repositories["owner/global-two"]["periodStarsGained"]["7d"] == 20
    assert repositories["owner/global-one"]["periodRankings"]["7d"] == 2
    assert repositories["owner/global-one"]["periodStarsGained"]["7d"] == 1


def test_build_site_payload_uses_api_period_repositories_outside_global_top(
    export_config,
):
    snapshot = _make_snapshot()
    snapshot["periods"] = {
        "7d": {
            "label": "7 jours",
            "query": "created:>=2026-03-28",
            "starts_at": "2026-03-28T07:36:12Z",
            "items": [
                {
                    "id": 99,
                    "full_name": "owner/recent-hit",
                    "html_url": "https://github.com/owner/recent-hit",
                    "stargazers_count": 1234,
                    "language": "TypeScript",
                    "description": "Recent repository",
                    "rank": 1,
                }
            ],
        }
    }

    payload = exporter.build_site_payload(snapshot)
    repositories = {item["fullName"]: item for item in payload["global"]["items"]}

    assert [item["fullName"] for item in payload["global"]["items"]] == [
        "owner/global-one",
        "owner/recent-hit",
    ]
    assert repositories["owner/recent-hit"]["periodRankings"]["7d"] == 1
    assert repositories["owner/recent-hit"]["periodStarsGained"]["7d"] == 1234
    assert repositories["owner/recent-hit"]["periodRankings"]["all"] is None
    assert payload["periods"][0]["available"] is True
    assert payload["periods"][0]["startsAt"] == "2026-03-28T07:36:12Z"
    assert payload["periods"][0]["rankingMode"] == "created"
    assert payload["periods"][-1]["rankingMode"] == "all"
    assert payload["stats"]["repositoryCount"] == 1
    assert payload["stats"]["totalStars"] == 100


def test_build_site_payload_raises_when_snapshot_tags_drift(export_config):
    snapshot = _make_snapshot()
    snapshot["categories"] = {"PYTHON": snapshot["categories"]["PYTHON"]}

    with pytest.raises(ValueError, match="missing tags: REACT"):
        exporter.build_site_payload(snapshot)


def test_build_site_payload_rejects_unsafe_repository_urls(export_config):
    snapshot = _make_snapshot()
    snapshot["global"]["items"][0]["html_url"] = "javascript:alert(1)"

    with pytest.raises(ValueError, match="Unsafe GitHub repository URL"):
        exporter.build_site_payload(snapshot)


def test_build_site_payload_rejects_unapproved_hosting_urls(export_config, monkeypatch):
    monkeypatch.setattr(
        exporter,
        "HOSTING_RECOMMENDATIONS",
        (
            HostingRecommendationDefinition(
                stack="React / Next.js",
                hosting="Unexpected host",
                url="https://example.com/docs",
                notes="Unexpected documentation host.",
            ),
        ),
    )

    with pytest.raises(ValueError, match="Unsafe hosting documentation URL"):
        exporter.build_site_payload(_make_snapshot())


def test_export_site_data_writes_json_and_creates_parent_directory(
    export_config, tmp_path
):
    input_path = tmp_path / "raw" / "latest.json"
    output_path = tmp_path / "public" / "site-data.json"
    input_path.parent.mkdir(parents=True)
    input_path.write_text(json.dumps(_make_snapshot()), encoding="utf-8")

    payload = exporter.export_site_data(
        input_path=input_path,
        output_path=output_path,
        generated_at="2026-04-05T10:00:00Z",
    )

    assert output_path.exists()
    assert json.loads(output_path.read_text(encoding="utf-8")) == payload


def test_export_site_data_uses_latest_history_before_current_snapshot(
    export_config, tmp_path
):
    input_path = tmp_path / "raw" / "latest.json"
    output_path = tmp_path / "public" / "site-data.json"
    history_dir = tmp_path / "raw" / "history"
    current_snapshot = _make_snapshot()
    all_time_snapshot = _make_snapshot()
    period_snapshot = _make_snapshot()
    older_snapshot = _make_snapshot()
    previous_snapshot = _make_snapshot()
    same_timestamp_snapshot = _make_snapshot()

    all_time_snapshot["captured_at"] = "2026-03-01T07:36:12Z"
    all_time_snapshot["global"]["items"][0]["rank"] = 20
    period_snapshot["captured_at"] = "2026-03-28T07:36:12Z"
    period_snapshot["global"]["items"][0]["rank"] = 11
    older_snapshot["captured_at"] = "2026-04-02T07:36:12Z"
    older_snapshot["global"]["items"][0]["rank"] = 9
    previous_snapshot["captured_at"] = "2026-04-03T07:36:12Z"
    previous_snapshot["global"]["items"][0]["rank"] = 3
    same_timestamp_snapshot["captured_at"] = current_snapshot["captured_at"]
    same_timestamp_snapshot["global"]["items"][0]["rank"] = 7

    input_path.parent.mkdir(parents=True)
    history_dir.mkdir(parents=True)
    input_path.write_text(json.dumps(current_snapshot), encoding="utf-8")
    (history_dir / "all-time.json").write_text(
        json.dumps(all_time_snapshot),
        encoding="utf-8",
    )
    (history_dir / "period.json").write_text(
        json.dumps(period_snapshot),
        encoding="utf-8",
    )
    (history_dir / "older.json").write_text(
        json.dumps(older_snapshot),
        encoding="utf-8",
    )
    (history_dir / "previous.json").write_text(
        json.dumps(previous_snapshot),
        encoding="utf-8",
    )
    (history_dir / "same.json").write_text(
        json.dumps(same_timestamp_snapshot),
        encoding="utf-8",
    )

    payload = exporter.export_site_data(
        input_path=input_path,
        output_path=output_path,
        history_dir=history_dir,
    )

    assert payload["global"]["items"][0]["previousRank"] == 3
    assert payload["global"]["items"][0]["movements"]["7d"] == 11
    assert payload["global"]["items"][0]["movements"]["all"] == 20
    assert payload["global"]["items"][0]["periodRankings"]["7d"] == 1
    assert payload["global"]["items"][0]["periodRankings"]["all"] == 1
    assert payload["global"]["items"][0]["periodStarsGained"]["7d"] == 0
    assert payload["global"]["items"][0]["periodStarsGained"]["all"] == 100
    assert payload["periods"][0]["baselineCapturedAt"] == "2026-03-28T07:36:12Z"
    assert payload["periods"][-1]["baselineCapturedAt"] == "2026-03-01T07:36:12Z"


def test_refresh_star_history_cache_fetches_missing_category_baselines(export_config):
    current_snapshot = _make_snapshot()
    previous_snapshot = _make_snapshot()
    previous_snapshot["captured_at"] = "2026-03-28T07:36:12Z"
    previous_snapshot["categories"]["PYTHON"]["items"][0]["id"] = 99
    previous_snapshot["categories"]["PYTHON"]["items"][0]["full_name"] = (
        "owner/old-python-lib"
    )
    cache = exporter.default_star_history_cache()

    class FakeStarHistoryClient:
        def __init__(self):
            self.calls = []

        def count_stargazers_at(self, full_name, timestamp):
            self.calls.append((full_name, exporter.timestamp_cache_key(timestamp)))
            return 30

    client = FakeStarHistoryClient()

    changed = exporter.refresh_star_history_cache(
        cache,
        current_snapshot,
        {"7d": previous_snapshot},
        repositories=["owner/python-lib"],
        client=client,
    )

    assert changed is True
    assert client.calls == [("owner/python-lib", "2026-03-28T07:36:12Z")]
    assert cache["repositories"]["owner/python-lib"] == {"2026-03-28T07:36:12Z": 30}


def test_main_passes_cli_paths_to_export(monkeypatch):
    captured = {}

    def fake_export_site_data(
        input_path: Path,
        output_path: Path,
        *,
        generated_at=None,
        history_dir=None,
        star_history_cache_path=None,
        refresh_github_star_history=False,
        star_history_repositories=(),
    ):
        captured["args"] = (
            input_path,
            output_path,
            generated_at,
            history_dir,
            star_history_cache_path,
            refresh_github_star_history,
            star_history_repositories,
        )
        return {}

    monkeypatch.setattr(exporter, "export_site_data", fake_export_site_data)

    exporter.main(
        [
            "--input-path",
            "custom/input.json",
            "--output-path",
            "custom/output.json",
        ]
    )

    assert captured["args"] == (
        Path("custom/input.json"),
        Path("custom/output.json"),
        None,
        exporter.HISTORY_DIR,
        exporter.DEFAULT_STAR_HISTORY_CACHE_PATH,
        False,
        [],
    )

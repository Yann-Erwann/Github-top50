import json
from pathlib import Path

import pytest
from scripts import export_site_data as exporter

from github_top50.domain.models import (
    CategoryDefinition,
    HostingRecommendationDefinition,
)


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


def test_build_site_payload_raises_when_snapshot_tags_drift(export_config):
    snapshot = _make_snapshot()
    snapshot["categories"] = {"PYTHON": snapshot["categories"]["PYTHON"]}

    with pytest.raises(ValueError, match="missing tags: REACT"):
        exporter.build_site_payload(snapshot)


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


def test_main_passes_cli_paths_to_export(monkeypatch):
    captured = {}

    def fake_export_site_data(
        input_path: Path, output_path: Path, *, generated_at=None
    ):
        captured["args"] = (input_path, output_path, generated_at)
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
    )

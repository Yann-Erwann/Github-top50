from unittest.mock import MagicMock, patch

import pytest
from requests.exceptions import HTTPError
from scripts.build_top50 import (
    build_table,
    build_toc,
    search_repos,
    slugify,
    update_readme,
)

from github_top50.domain.models import (
    HostingRecommendationDefinition,
    to_hosting_recommendation,
)
from github_top50.services.github_client import build_headers
from github_top50.services.readme_builder import (
    HOSTING_TITLE,
    build_hosting_section,
    build_hosting_table,
)

# ── slugify ──────────────────────────────────────────────────────────


class TestSlugify:
    def test_simple_text(self):
        assert slugify("Hello World") == "hello-world"

    def test_with_emoji(self):
        assert slugify("☕ Backend — Java & Spring Boot") == "backend-java-spring-boot"

    def test_already_lowercase(self):
        assert slugify("devops") == "devops"

    def test_special_characters(self):
        assert slugify("API & Contracts") == "api-contracts"

    def test_accents_are_normalized(self):
        assert slugify("📂 Top par catégorie") == "top-par-categorie"

    def test_separators_are_preserved_as_word_boundaries(self):
        assert (
            slugify("🏗️ Architecture-DDD/Event Storming")
            == "architecture-ddd-event-storming"
        )

    def test_multiple_spaces(self):
        assert slugify("a   b   c") == "a-b-c"

    def test_empty_string(self):
        assert slugify("") == ""


# ── build_table ──────────────────────────────────────────────────────


def _make_repo(name="owner/repo", stars=100, language="Python", description="A repo"):
    return {
        "id": 1,
        "full_name": name,
        "html_url": f"https://github.com/{name}",
        "stargazers_count": stars,
        "language": language,
        "description": description,
    }


def _make_hosting_recommendation(
    stack="Next.js",
    hosting="Vercel",
    url="https://vercel.com",
    notes="Déploiement statique simple",
):
    return {
        "stack": stack,
        "hosting": hosting,
        "url": url,
        "notes": notes,
    }


class TestBuildTable:
    def test_single_repo(self):
        items = [_make_repo()]
        table = build_table(items)
        lines = table.strip().split("\n")
        assert len(lines) == 3  # header + separator + 1 row
        assert "owner/repo" in lines[2]
        assert "NEW" in lines[2]
        assert "100" in lines[2]
        assert "Python" in lines[2]

    def test_numbering_starts_at_1(self):
        items = [
            _make_repo(),
            _make_repo(name="org/lib", stars=50, description="A repo"),
        ]
        table = build_table(items)
        lines = table.strip().split("\n")
        assert lines[2].startswith("| 1 |")
        assert lines[3].startswith("| 2 |")

    def test_custom_start_index(self):
        items = [_make_repo()]
        table = build_table(items, start=5)
        lines = table.strip().split("\n")
        assert lines[2].startswith("| 5 |")

    def test_none_language_shows_dash(self):
        items = [_make_repo(language=None)]
        table = build_table(items)
        assert "| - |" in table

    def test_none_description_shows_dash(self):
        items = [_make_repo(description=None)]
        table = build_table(items)
        assert "| - |" in table

    def test_pipe_in_description_escaped(self):
        items = [_make_repo(description="foo | bar")]
        table = build_table(items)
        assert "foo \\| bar" in table

    def test_long_description_truncated(self):
        long_desc = "a" * 150
        items = [_make_repo(description=long_desc)]
        table = build_table(items)
        # 97 chars + "..." = 100
        assert "..." in table
        # full 150-char string must NOT appear
        assert long_desc not in table

    def test_empty_items(self):
        table = build_table([])
        lines = table.strip().split("\n")
        assert len(lines) == 2  # header + separator only

    def test_rank_increase_renders_up_arrow(self):
        items = [
            _make_repo(
                stars=100,
                description="A repo",
                name="owner/repo",
                language="Python",
            )
        ]
        items[0]["rank"] = 1
        items[0]["previous_rank"] = 4

        table = build_table(items)

        assert "| 1 | ↑ 3 | [owner/repo]" in table

    def test_rank_drop_renders_down_arrow(self):
        items = [
            _make_repo(
                stars=100,
                description="A repo",
                name="owner/repo",
                language="Python",
            )
        ]
        items[0]["rank"] = 5
        items[0]["previous_rank"] = 2

        table = build_table(items)

        assert "| 5 | ↓ 3 | [owner/repo]" in table

    def test_rank_stability_renders_equal_marker(self):
        items = [
            _make_repo(
                stars=100,
                description="A repo",
                name="owner/repo",
                language="Python",
            )
        ]
        items[0]["rank"] = 3
        items[0]["previous_rank"] = 3

        table = build_table(items)

        assert "| 3 | = | [owner/repo]" in table


# ── build_toc ────────────────────────────────────────────────────────


class TestBuildToc:
    def test_contains_top50_link(self):
        toc = build_toc([])
        assert "Top 50 GitHub Stars" in toc

    def test_contains_hosting_link(self):
        toc = build_toc([])
        assert "Hébergement possible" in toc

    def test_contains_category_links(self):
        cats = [{"title": "🐍 Backend — Python", "tag": "PY", "query": "q"}]
        toc = build_toc(cats)
        assert "Backend — Python" in toc
        assert "(#" in toc

    def test_sommaire_header(self):
        toc = build_toc([])
        assert "Sommaire" in toc

    def test_places_hosting_link_last(self):
        toc = build_toc([])
        assert toc.index("Top 50 GitHub Stars") < toc.index("Hébergement possible")


# ── hosting recommendations ─────────────────────────────────────────


class TestBuildHostingTable:
    def test_contains_expected_columns_and_recommendation_link(self):
        items = [_make_hosting_recommendation()]

        table = build_hosting_table(items)
        lines = table.strip().split("\n")

        assert lines[0] == "| Stack | Hébergement recommandé | Pourquoi |"
        assert lines[1] == "|---|---|---|"
        assert lines[2] == (
            "| Next.js | [Vercel](https://vercel.com) | Déploiement statique simple |"
        )

    def test_escapes_pipe_characters_in_rendered_fields(self):
        items = [
            _make_hosting_recommendation(
                stack="Next.js | App Router",
                hosting="Render | Static",
                url="https://render.com",
                notes="Préprod | démo",
            )
        ]

        table = build_hosting_table(items)

        assert "Next.js \\| App Router" in table
        assert "[Render \\| Static](https://render.com)" in table
        assert "Préprod \\| démo" in table


class TestBuildHostingSection:
    def test_renders_anchor_and_section_title(self):
        section = build_hosting_section([_make_hosting_recommendation()])
        expected_anchor = slugify(HOSTING_TITLE)

        lines = section.split("\n")

        assert lines[0] == f'<a id="{expected_anchor}"></a>'
        assert lines[1] == f"## {HOSTING_TITLE}"
        assert "| Stack | Hébergement recommandé | Pourquoi |" in section


class TestHostingRecommendationNormalization:
    def test_mapping_is_normalized_to_definition(self):
        recommendation = to_hosting_recommendation(_make_hosting_recommendation())

        assert recommendation == HostingRecommendationDefinition(
            stack="Next.js",
            hosting="Vercel",
            url="https://vercel.com",
            notes="Déploiement statique simple",
        )

    def test_definition_instance_is_returned_as_is(self):
        recommendation = HostingRecommendationDefinition(
            stack="Astro",
            hosting="Cloudflare Pages",
            url="https://pages.cloudflare.com",
            notes="CDN global",
        )

        assert to_hosting_recommendation(recommendation) is recommendation


# ── search_repos ─────────────────────────────────────────────────────


class TestSearchRepos:
    def test_build_headers_uses_gh_token_fallback(self, monkeypatch):
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.setenv("GH_TOKEN", "test-token")

        assert build_headers() == {
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer test-token",
        }

    @patch("scripts.build_top50.requests.get")
    def test_returns_items(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"items": [_make_repo()]}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = search_repos("stars:>1", 10)
        assert len(result) == 1
        assert result[0]["full_name"] == "owner/repo"

    @patch("scripts.build_top50.requests.get")
    def test_empty_response(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"items": []}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = search_repos("stars:>1", 10)
        assert result == []

    @patch("scripts.build_top50.time.sleep")
    @patch("scripts.build_top50.requests.get")
    def test_rate_limit_retries(self, mock_get, mock_sleep):
        rate_resp = MagicMock()
        rate_resp.status_code = 403
        rate_resp.headers = {"Retry-After": "60"}

        ok_resp = MagicMock()
        ok_resp.status_code = 200
        ok_resp.headers = {}
        ok_resp.json.return_value = {"items": [_make_repo()]}
        ok_resp.raise_for_status = MagicMock()

        mock_get.side_effect = [rate_resp, ok_resp]

        result = search_repos("stars:>1", 10)
        mock_sleep.assert_called_once_with(60)
        assert len(result) == 1

    @patch("scripts.build_top50.time.sleep")
    @patch("scripts.build_top50.requests.get")
    def test_non_rate_limit_403_raises_without_sleeping(self, mock_get, mock_sleep):
        forbidden_resp = MagicMock()
        forbidden_resp.status_code = 403
        forbidden_resp.headers = {}
        forbidden_resp.raise_for_status.side_effect = HTTPError("403 Forbidden")
        mock_get.return_value = forbidden_resp

        with pytest.raises(HTTPError, match="403 Forbidden"):
            search_repos("stars:>1", 10)

        mock_sleep.assert_not_called()


# ── update_readme ────────────────────────────────────────────────────


class TestUpdateReadme:
    def test_replaces_content_between_markers(self, tmp_path):
        readme = tmp_path / "README.md"
        readme.write_text(
            "Header\n<!-- TOP50:START -->\nold content\n<!-- TOP50:END -->\nFooter",
            encoding="utf-8",
        )

        update_readme(
            readme,
            "<!-- TOP50:START -->",
            "<!-- TOP50:END -->",
            "new content",
        )

        result = readme.read_text(encoding="utf-8")
        assert "new content" in result
        assert "old content" not in result
        assert "Header" in result
        assert "Footer" in result

    def test_raises_when_markers_missing(self, tmp_path):
        readme = tmp_path / "README.md"
        readme.write_text("No markers here", encoding="utf-8")

        with pytest.raises(RuntimeError, match="Balises TOP50 introuvables"):
            update_readme(readme, "<!-- TOP50:START -->", "<!-- TOP50:END -->", "x")

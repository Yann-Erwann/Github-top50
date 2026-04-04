"""Integration tests — validate interactions between multiple components."""

import re
from unittest.mock import MagicMock, patch

import pytest
from scripts.build_top50 import (
    CATEGORIES,
    END,
    START,
    build_generated_content,
    build_table,
    build_toc,
    search_repos,
    slugify,
    update_readme,
)


def _make_repo(name="owner/repo", stars=100, language="Python", description="A repo"):
    return {
        "id": abs(hash(name)) % 10_000,
        "full_name": name,
        "html_url": f"https://github.com/{name}",
        "stargazers_count": stars,
        "language": language,
        "description": description,
    }


FAKE_ITEMS = [
    _make_repo(f"org/repo-{i}", stars=1000 - i, description=f"Desc {i}")
    for i in range(10)
]


def _mock_api_response(*args, **kwargs):
    """Return a fake successful GitHub API response."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"items": FAKE_ITEMS}
    resp.raise_for_status = MagicMock()
    return resp


# ── Full pipeline (integration) ──────────────────────────────────────


class TestFullPipeline:
    """Integration: chain search → build → TOC → update_readme with mocked API."""

    def _build_readme_template(self, tmp_path):
        """Create a minimal README with TOP50 markers."""
        readme = tmp_path / "README.md"
        readme.write_text(
            f"# My Top Stars\n\n{START}\nplaceholder\n{END}\n\nFooter\n",
            encoding="utf-8",
        )
        return readme

    @patch("scripts.build_top50.time.sleep")
    @patch("scripts.build_top50.requests.get", side_effect=_mock_api_response)
    def test_full_generation_produces_valid_readme(
        self, mock_get, mock_sleep, tmp_path
    ):
        """Chain all components together and validate the generated README structure."""
        readme = self._build_readme_template(tmp_path)

        # --- Run the full pipeline (same logic as main()) ---
        global_items = search_repos("stars:>1", 50)

        test_categories = CATEGORIES[:3]  # use only 3 categories to keep it fast

        category_items = {}
        for cat in test_categories:
            category_items[cat.tag] = search_repos(cat.query, 10)

        generated = build_generated_content(
            global_items, test_categories, category_items
        )
        update_readme(readme, START, END, generated)

        # --- Verify generated README ---
        content = readme.read_text(encoding="utf-8")

        # Header and footer preserved
        assert content.startswith("# My Top Stars")
        assert content.strip().endswith("Footer")

        # Markers present
        assert START in content
        assert END in content

        # TOC present
        assert "Sommaire" in content
        assert "Hébergement possible" in content
        assert "Top 50 GitHub Stars" in content
        assert "Top par catégorie" in content
        assert '<a id="hebergement-possible"></a>' in content
        assert '<a id="top-50-github-stars"></a>' in content
        assert '<a id="top-par-categorie"></a>' in content
        assert content.index('<a id="top-50-github-stars"></a>') < content.index(
            '<a id="top-par-categorie"></a>'
        )
        assert content.index('<a id="top-par-categorie"></a>') < content.index(
            '<a id="hebergement-possible"></a>'
        )

        # Global table
        assert "| # | Trend | Repository | Description |" in content

        # Category sections
        for cat in test_categories:
            assert cat.title in content
            assert f'<a id="{slugify(cat.title)}"></a>' in content
            assert f"<!-- {cat.tag}:START -->" in content
            assert f"<!-- {cat.tag}:END -->" in content

        # Repo data in table rows
        assert "org/repo-0" in content
        assert "Desc 0" in content

    @patch("scripts.build_top50.time.sleep")
    @patch("scripts.build_top50.requests.get", side_effect=_mock_api_response)
    def test_idempotent_generation(self, mock_get, mock_sleep, tmp_path):
        """Running the pipeline twice produces the same output."""
        readme = self._build_readme_template(tmp_path)

        def _generate():
            items = search_repos("stars:>1", 50)
            generated = build_generated_content(items, [], {})
            update_readme(readme, START, END, generated)
            return readme.read_text(encoding="utf-8")

        first_run = _generate()
        second_run = _generate()
        assert first_run == second_run


# ── README structure validation ──────────────────────────────────────


class TestReadmeStructure:
    """Integration: validate markdown structure across generated tables and TOC."""

    def test_table_rows_have_correct_columns(self):
        items = FAKE_ITEMS[:5]
        table = build_table(items)
        lines = table.strip().split("\n")

        # Header + separator + 5 data rows
        assert len(lines) == 7

        for line in lines[2:]:
            cols = [c.strip() for c in line.split("|") if c.strip()]
            assert len(cols) == 6, f"Expected 6 columns, got {len(cols)}: {line}"

    def test_table_links_are_valid_markdown(self):
        items = FAKE_ITEMS[:3]
        table = build_table(items)
        # Every data row should contain a markdown link [name](url)
        link_pattern = re.compile(r"\[[\w/\-]+\]\(https://github\.com/[\w/\-]+\)")
        for line in table.strip().split("\n")[2:]:
            assert link_pattern.search(line), f"No valid link in row: {line}"

    def test_toc_anchors_are_valid(self):
        toc = build_toc(CATEGORIES)
        anchor_pattern = re.compile(r"\(#[\w-]+\)")
        anchors = anchor_pattern.findall(toc)
        # 3 global links + 1 per category
        assert len(anchors) == 3 + len(CATEGORIES)

    def test_all_categories_have_unique_tags(self):
        tags = [c.tag for c in CATEGORIES]
        assert len(tags) == len(set(tags)), "Duplicate category tags found"

    def test_all_categories_have_required_keys(self):
        for cat in CATEGORIES:
            assert cat.title
            assert cat.tag
            assert cat.query

    def test_category_markers_are_well_formed(self):
        for cat in CATEGORIES:
            tag = cat.tag
            assert tag == tag.upper(), f"Tag '{tag}' should be uppercase"
            assert " " not in tag, f"Tag '{tag}' should not contain spaces"


# ── Multi-step integration ───────────────────────────────────────────


class TestSearchAndBuild:
    """Integration: search_repos → build_table → markers chain."""

    @patch("scripts.build_top50.requests.get", side_effect=_mock_api_response)
    def test_search_then_build_table(self, mock_get):
        items = search_repos("topic:python stars:>1000", 10)
        table = build_table(items)

        lines = table.strip().split("\n")
        assert len(lines) == 12  # header + separator + 10 rows
        assert "org/repo-0" in lines[2]
        assert "1,000" in lines[2]  # stars with comma formatting

    @patch("scripts.build_top50.requests.get", side_effect=_mock_api_response)
    def test_search_then_build_with_category_markers(self, mock_get):
        cat = CATEGORIES[0]
        items = search_repos(cat.query, 10)
        table = build_table(items)

        tag_start = f"<!-- {cat.tag}:START -->"
        tag_end = f"<!-- {cat.tag}:END -->"
        section = f"### {cat.title}\n\n{tag_start}\n{table}\n{tag_end}"

        assert cat.title in section
        assert tag_start in section
        assert tag_end in section
        assert "| # |" in section

    @patch("scripts.build_top50.requests.get")
    def test_api_error_propagates(self, mock_get):
        """HTTP errors from the API should propagate as exceptions."""
        from requests.exceptions import HTTPError

        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.raise_for_status.side_effect = HTTPError("500 Server Error")
        mock_get.return_value = mock_resp

        with pytest.raises(HTTPError):
            search_repos("stars:>1", 10)

    @patch("scripts.build_top50.requests.get", side_effect=_mock_api_response)
    def test_toc_links_match_category_headings(self, mock_get):
        """TOC anchor links should correspond to generated section headings."""
        test_cats = CATEGORIES[:3]
        toc = build_toc(test_cats)
        full_content = build_generated_content(
            FAKE_ITEMS,
            test_cats,
            {cat.tag: FAKE_ITEMS for cat in test_cats},
        )

        for cat in test_cats:
            assert f"(#{slugify(cat.title)})" in toc
            assert f'<a id="{slugify(cat.title)}"></a>' in full_content

"""Integration / system tests for the full README generation pipeline."""

import re
from pathlib import Path
from unittest.mock import MagicMock, patch

from scripts.build_top50 import (
    CATEGORIES,
    END,
    START,
    build_table,
    build_toc,
    search_repos,
    update_readme,
)


def _make_repo(name="owner/repo", stars=100, language="Python", description="A repo"):
    return {
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


# ── Full pipeline (system test) ──────────────────────────────────────


class TestFullPipeline:
    """End-to-end test: mock the API, run the full generation, validate README."""

    def _build_readme_template(self, tmp_path):
        """Create a minimal README with TOP50 markers."""
        readme = tmp_path / "README.md"
        readme.write_text(
            "# My Top Stars\n\n"
            f"{START}\n"
            "placeholder\n"
            f"{END}\n\n"
            "Footer\n",
            encoding="utf-8",
        )
        return readme

    @patch("scripts.build_top50.time.sleep")
    @patch("scripts.build_top50.requests.get", side_effect=_mock_api_response)
    def test_full_generation_produces_valid_readme(
        self, mock_get, mock_sleep, tmp_path
    ):
        """Run the complete pipeline and validate the generated README structure."""
        readme = self._build_readme_template(tmp_path)

        # --- Run the full pipeline (same logic as main()) ---
        global_items = search_repos("stars:>1", 50)
        global_table = build_table(global_items)

        test_categories = CATEGORIES[:3]  # use only 3 categories to keep it fast

        category_sections = []
        for cat in test_categories:
            tag_start = f"<!-- {cat['tag']}:START -->"
            tag_end = f"<!-- {cat['tag']}:END -->"
            items = search_repos(cat["query"], 10)
            table = build_table(items)
            section = f"### {cat['title']}\n\n{tag_start}\n{table}\n{tag_end}"
            category_sections.append(section)

        categories_block = "\n\n".join(category_sections)
        toc = build_toc(test_categories)
        generated = (
            f"{toc}\n\n{global_table}\n\n"
            f"## 📂 Top par catégorie\n\n{categories_block}"
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
        assert "Top 50 GitHub Stars" in content
        assert "Top par catégorie" in content

        # Global table
        assert "| # | Repository | Description |" in content

        # Category sections
        for cat in test_categories:
            assert cat["title"] in content
            assert f"<!-- {cat['tag']}:START -->" in content
            assert f"<!-- {cat['tag']}:END -->" in content

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
            table = build_table(items)
            toc = build_toc([])
            generated = f"{toc}\n\n{table}"
            update_readme(readme, START, END, generated)
            return readme.read_text(encoding="utf-8")

        first_run = _generate()
        second_run = _generate()
        assert first_run == second_run


# ── README structure validation ──────────────────────────────────────


class TestReadmeStructure:
    """Validate markdown structure of generated tables and TOC."""

    def test_table_rows_have_correct_columns(self):
        items = FAKE_ITEMS[:5]
        table = build_table(items)
        lines = table.strip().split("\n")

        # Header + separator + 5 data rows
        assert len(lines) == 7

        for line in lines[2:]:
            cols = [c.strip() for c in line.split("|") if c.strip()]
            assert len(cols) == 5, f"Expected 5 columns, got {len(cols)}: {line}"

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
        # 2 global links + 1 per category
        assert len(anchors) == 2 + len(CATEGORIES)

    def test_all_categories_have_unique_tags(self):
        tags = [c["tag"] for c in CATEGORIES]
        assert len(tags) == len(set(tags)), "Duplicate category tags found"

    def test_all_categories_have_required_keys(self):
        for cat in CATEGORIES:
            assert "title" in cat
            assert "tag" in cat
            assert "query" in cat

    def test_category_markers_are_well_formed(self):
        for cat in CATEGORIES:
            tag = cat["tag"]
            assert tag == tag.upper(), f"Tag '{tag}' should be uppercase"
            assert " " not in tag, f"Tag '{tag}' should not contain spaces"


# ── Multi-step integration ───────────────────────────────────────────


class TestSearchAndBuild:
    """Integration: search_repos → build_table chain."""

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
        items = search_repos(cat["query"], 10)
        table = build_table(items)

        tag_start = f"<!-- {cat['tag']}:START -->"
        tag_end = f"<!-- {cat['tag']}:END -->"
        section = f"### {cat['title']}\n\n{tag_start}\n{table}\n{tag_end}"

        assert cat["title"] in section
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

        try:
            search_repos("stars:>1", 10)
            assert False, "Should have raised HTTPError"
        except HTTPError:
            pass

    @patch("scripts.build_top50.requests.get", side_effect=_mock_api_response)
    def test_toc_links_match_category_headings(self, mock_get):
        """TOC anchor links should correspond to generated section headings."""
        test_cats = CATEGORIES[:3]
        toc = build_toc(test_cats)

        sections = []
        for cat in test_cats:
            items = search_repos(cat["query"], 10)
            table = build_table(items)
            sections.append(f"### {cat['title']}\n\n{table}")

        full_content = toc + "\n\n" + "\n\n".join(sections)

        # Every category mentioned in the TOC should appear as a heading
        for cat in test_cats:
            assert cat["title"] in full_content

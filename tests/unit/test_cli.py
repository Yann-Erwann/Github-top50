import runpy
import sys
from pathlib import Path

import pytest

SRC_PATH = Path(__file__).resolve().parents[2] / "src"

from github_top50 import cli  # noqa: E402
from github_top50.services import readme_builder as rb  # noqa: E402


def _make_repo(name="owner/repo", stars=100, language="Python", description="A repo"):
    return {
        "full_name": name,
        "html_url": f"https://github.com/{name}",
        "stargazers_count": stars,
        "language": language,
        "description": description,
    }


def test_build_category_section_wraps_table_with_markers():
    category = {"title": "🐍 Backend — Python", "tag": "PY", "query": "q"}

    section = rb.build_category_section(category, [_make_repo()])

    assert section.startswith("### 🐍 Backend — Python")
    assert "<!-- PY:START -->" in section
    assert "<!-- PY:END -->" in section
    assert "| 1 | [owner/repo]" in section


def test_build_generated_content_assembles_global_and_category_sections():
    categories = (
        {"title": "🐍 Backend — Python", "tag": "PY", "query": "q1"},
        {"title": "🔒 Security & DevSecOps", "tag": "SEC", "query": "q2"},
    )
    global_items = [_make_repo()]
    category_items = {
        "PY": [_make_repo(name="org/python-lib")],
        "SEC": [_make_repo(name="org/security-lib")],
    }

    content = rb.build_generated_content(global_items, categories, category_items)

    assert "## 📂 Top par catégorie" in content
    assert "org/python-lib" in content
    assert "org/security-lib" in content
    assert "(#backend-python)" in content
    assert "(#security-devsecops)" in content


def test_fetch_category_items_queries_each_category_and_sleeps(monkeypatch):
    test_categories = (
        {"title": "Cat A", "tag": "A", "query": "q-a"},
        {"title": "Cat B", "tag": "B", "query": "q-b"},
    )
    calls = []
    sleeps = []

    def fake_search(query, per_page):
        calls.append((query, per_page))
        return [_make_repo(name=f"org/{query}")]

    monkeypatch.setattr(cli, "CATEGORIES", test_categories)
    monkeypatch.setattr(cli, "CATEGORY_PER_PAGE", 7)
    monkeypatch.setattr(cli, "search_repos", fake_search)
    monkeypatch.setattr(cli.time, "sleep", sleeps.append)

    result = cli._fetch_category_items()

    assert calls == [("q-a", 7), ("q-b", 7)]
    assert sleeps == [2]
    assert result["A"][0]["full_name"] == "org/q-a"
    assert result["B"][0]["full_name"] == "org/q-b"


def test_main_wires_search_generation_and_readme_update(monkeypatch, tmp_path, capsys):
    global_items = [_make_repo(name="org/global")]
    category_items = {"PY": [_make_repo(name="org/category")]}
    expected_content = "generated readme block"
    captured = {}

    monkeypatch.setattr(cli, "GLOBAL_QUERY", "stars:>42")
    monkeypatch.setattr(cli, "PER_PAGE", 42)
    monkeypatch.setattr(
        cli,
        "CATEGORIES",
        ({"title": "Cat", "tag": "PY", "query": "q"},),
    )
    monkeypatch.setattr(cli, "README_PATH", tmp_path / "README.md")
    monkeypatch.setattr(cli, "START", "<!-- START -->")
    monkeypatch.setattr(cli, "END", "<!-- END -->")

    def fake_search(query, per_page):
        captured["search"] = (query, per_page)
        return global_items

    def fake_fetch_category_items():
        captured["fetched"] = True
        return category_items

    def fake_build_generated_content(
        passed_global_items, categories, passed_category_items
    ):
        captured["build"] = (passed_global_items, categories, passed_category_items)
        return expected_content

    def fake_update_readme(path, start, end, generated):
        captured["update"] = (path, start, end, generated)

    monkeypatch.setattr(cli, "search_repos", fake_search)
    monkeypatch.setattr(cli, "_fetch_category_items", fake_fetch_category_items)
    monkeypatch.setattr(cli, "build_generated_content", fake_build_generated_content)
    monkeypatch.setattr(cli, "update_readme", fake_update_readme)

    cli.main()

    assert captured["search"] == ("stars:>42", 42)
    assert captured["fetched"] is True
    assert captured["build"] == (
        global_items,
        ({"title": "Cat", "tag": "PY", "query": "q"},),
        category_items,
    )
    assert captured["update"] == (
        tmp_path / "README.md",
        "<!-- START -->",
        "<!-- END -->",
        expected_content,
    )
    output = capsys.readouterr().out
    assert "Fetching global top 50..." in output
    assert "README.md mis à jour." in output


def test_main_help_exits_without_running_generation(monkeypatch, capsys):
    monkeypatch.setattr(
        cli,
        "search_repos",
        lambda *args, **kwargs: pytest.fail("search_repos should not run for --help"),
    )

    with pytest.raises(SystemExit, match="0"):
        cli.main(["--help"])

    output = capsys.readouterr().out
    assert "Generate the GitHub Top 50 section" in output
    assert "--readme-path" in output


def test_package_main_module_invokes_cli_main(monkeypatch):
    called = {"value": False}

    def fake_main(argv=None):
        called["value"] = True
        assert argv == []

    monkeypatch.setattr("github_top50.cli.main", fake_main)
    monkeypatch.setattr(sys, "argv", ["github_top50"])

    runpy.run_module("github_top50.__main__", run_name="__main__")

    assert called["value"] is True


def test_script_entrypoint_invokes_main_and_restores_src_path(monkeypatch):
    script_path = Path("scripts/build_top50.py")
    src_path = str(Path("src").resolve())
    called = {"value": False}

    def fake_main(argv=None):
        called["value"] = True
        assert argv == []

    monkeypatch.setattr("github_top50.main", fake_main)
    monkeypatch.setattr(sys, "argv", [str(script_path)])

    removed = False
    if src_path in sys.path:
        sys.path.remove(src_path)
        removed = True

    try:
        runpy.run_path(str(script_path), run_name="__main__")
    finally:
        if removed and src_path not in sys.path:
            sys.path.insert(0, src_path)

    assert called["value"] is True
    assert src_path in sys.path

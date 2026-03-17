import runpy
import sys
from pathlib import Path

import pytest

SRC_PATH = Path(__file__).resolve().parents[2] / "src"

from github_top50 import cli  # noqa: E402
from github_top50.domain.models import ReadmeSection  # noqa: E402
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

    assert section.startswith('<a id="backend-python"></a>\n### 🐍 Backend — Python')
    assert "<!-- PY:START -->" in section
    assert "<!-- PY:END -->" in section
    assert "| 1 | [owner/repo]" in section


def test_create_category_section_returns_typed_section():
    category = {"title": "🐍 Backend — Python", "tag": "PY", "query": "q"}

    section = rb.create_category_section(category, [_make_repo()])

    assert isinstance(section, ReadmeSection)
    assert section.title == "🐍 Backend — Python"
    assert section.anchor == "backend-python"
    assert section.start_marker == "<!-- PY:START -->"
    assert section.end_marker == "<!-- PY:END -->"
    assert "| 1 | [owner/repo]" in section.render()


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

    assert '<a id="top-50-github-stars"></a>' in content
    assert "## 🏆 Top 50 GitHub Stars" in content
    assert "## 📂 Top par catégorie" in content
    assert "org/python-lib" in content
    assert "org/security-lib" in content
    assert "(#backend-python)" in content
    assert "(#security-devsecops)" in content
    assert "(#top-par-categorie)" in content
    assert content.index("#### 📑 Sommaire") < content.index(
        '<a id="top-50-github-stars"></a>'
    )


def test_fetch_category_items_queries_each_category_and_sleeps(monkeypatch):
    expected = {"A": [_make_repo(name="org/q-a")]}

    class FakeUseCase:
        def fetch_category_items(self):
            return expected

    monkeypatch.setattr(cli, "build_use_case", lambda: FakeUseCase())

    assert cli._fetch_category_items() == expected


def test_main_wires_search_generation_and_readme_update(monkeypatch, tmp_path, capsys):
    captured = {}

    monkeypatch.setattr(cli, "README_PATH", tmp_path / "README.md")
    monkeypatch.setattr(cli, "START", "<!-- START -->")
    monkeypatch.setattr(cli, "END", "<!-- END -->")

    class FakeUseCase:
        def run(self, *, readme_path, start_marker, end_marker):
            captured["run"] = (readme_path, start_marker, end_marker)

    monkeypatch.setattr(cli, "build_use_case", lambda: FakeUseCase())

    cli.main()

    assert captured["run"] == (
        tmp_path / "README.md",
        "<!-- START -->",
        "<!-- END -->",
    )
    assert capsys.readouterr().out == ""


def test_main_help_exits_without_running_generation(monkeypatch, capsys):
    monkeypatch.setattr(
        cli,
        "build_use_case",
        lambda: pytest.fail("build_use_case should not run for --help"),
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

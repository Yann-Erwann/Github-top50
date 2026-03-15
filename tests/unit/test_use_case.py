from github_top50.application.generate_top50 import GenerateTop50ReadmeUseCase
from github_top50.domain.models import CategoryDefinition, Repository


class FakeGateway:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def search_repositories(self, query, per_page):
        self.calls.append((query, per_page))
        return self.responses[query]


def _make_repo(name="owner/repo", stars=100, language="Python", description="A repo"):
    return Repository(
        full_name=name,
        html_url=f"https://github.com/{name}",
        stargazers_count=stars,
        language=language,
        description=description,
    )


def test_fetch_category_items_queries_each_category_and_sleeps(capsys):
    categories = (
        CategoryDefinition(title="Cat A", tag="A", query="q-a"),
        CategoryDefinition(title="Cat B", tag="B", query="q-b"),
    )
    sleeps = []
    gateway = FakeGateway(
        {
            "q-a": [_make_repo(name="org/q-a")],
            "q-b": [_make_repo(name="org/q-b")],
        }
    )
    use_case = GenerateTop50ReadmeUseCase(
        categories=categories,
        repository_gateway=gateway,
        global_query="stars:>1",
        per_page=50,
        category_per_page=7,
        sleep_func=sleeps.append,
    )

    result = use_case.fetch_category_items()

    assert gateway.calls == [("q-a", 7), ("q-b", 7)]
    assert sleeps == [2]
    assert result["A"][0].full_name == "org/q-a"
    assert result["B"][0].full_name == "org/q-b"
    output = capsys.readouterr().out
    assert "Fetching Cat A..." in output
    assert "Fetching Cat B..." in output


def test_run_builds_content_and_updates_readme(monkeypatch, tmp_path, capsys):
    categories = (CategoryDefinition(title="Cat", tag="PY", query="q-cat"),)
    gateway = FakeGateway(
        {
            "stars:>42": [_make_repo(name="org/global")],
            "q-cat": [_make_repo(name="org/category")],
        }
    )
    captured = {}
    use_case = GenerateTop50ReadmeUseCase(
        categories=categories,
        repository_gateway=gateway,
        global_query="stars:>42",
        per_page=42,
        category_per_page=10,
    )

    def fake_build_generated_content(global_items, passed_categories, category_items):
        captured["build"] = (global_items, passed_categories, category_items)
        return "generated readme block"

    def fake_update_readme(path, start, end, generated):
        captured["update"] = (path, start, end, generated)

    monkeypatch.setattr(
        "github_top50.application.generate_top50.build_generated_content",
        fake_build_generated_content,
    )
    monkeypatch.setattr(
        "github_top50.application.generate_top50.update_readme",
        fake_update_readme,
    )

    generated = use_case.run(
        readme_path=tmp_path / "README.md",
        start_marker="<!-- START -->",
        end_marker="<!-- END -->",
    )

    assert gateway.calls == [("stars:>42", 42), ("q-cat", 10)]
    assert captured["build"][0][0].full_name == "org/global"
    assert captured["build"][1] == categories
    assert captured["build"][2]["PY"][0].full_name == "org/category"
    assert captured["update"] == (
        tmp_path / "README.md",
        "<!-- START -->",
        "<!-- END -->",
        "generated readme block",
    )
    assert generated == "generated readme block"
    output = capsys.readouterr().out
    assert "Fetching global top 50..." in output
    assert "Fetching Cat..." in output
    assert "README.md mis à jour." in output

"""README link integrity checks."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from github_top50.config import CATEGORIES, END, README_PATH, START
from github_top50.services.readme_builder import build_generated_content

MARKDOWN_LINK_RE = re.compile(r"(?<!\!)\[(?P<label>[^\]]+)\]\((?P<target>[^)]+)\)")
HEADING_RE = re.compile(r"^#{2,3}\s+(?P<title>.+)$", re.MULTILINE)


def _make_repo(
    name: str = "owner/repo",
    stars: int = 100,
    language: str | None = "Python",
    description: str | None = "A repo",
) -> dict[str, object]:
    return {
        "full_name": name,
        "html_url": f"https://github.com/{name}",
        "stargazers_count": stars,
        "language": language,
        "description": description,
    }


def _extract_top50_block(readme_content: str) -> str:
    start_index = readme_content.index(START) + len(START)
    end_index = readme_content.index(END)
    return readme_content[start_index:end_index].strip()


def _extract_markdown_links(content: str) -> list[tuple[str, str]]:
    return [
        (match.group("label"), match.group("target"))
        for match in MARKDOWN_LINK_RE.finditer(content)
    ]


def _extract_repo_links(content: str) -> list[tuple[str, str]]:
    return [
        (label, target)
        for label, target in _extract_markdown_links(content)
        if target.startswith("https://github.com/")
    ]


def _extract_internal_links(content: str) -> list[tuple[str, str]]:
    return [
        (label, target)
        for label, target in _extract_markdown_links(content)
        if target.startswith("#")
    ]


def _assert_is_github_repository_link(label: str, target: str) -> None:
    parsed = urlparse(target)
    path_parts = [part for part in parsed.path.split("/") if part]

    assert parsed.scheme == "https"
    assert parsed.netloc == "github.com"
    assert len(path_parts) == 2, f"Expected owner/repo URL, got {target}"
    assert not parsed.params
    assert not parsed.query
    assert not parsed.fragment
    assert label == "/".join(path_parts)


def test_generated_content_uses_only_internal_anchors_and_github_repo_links():
    categories = CATEGORIES[:2]
    global_items = [_make_repo(name="org/global-repo")]
    category_items = {
        categories[0]["tag"]: [_make_repo(name="org/java-repo")],
        categories[1]["tag"]: [_make_repo(name="org/node-repo")],
    }

    content = build_generated_content(global_items, categories, category_items)
    links = _extract_markdown_links(content)

    assert links
    for _, target in links:
        assert target.startswith("#") or target.startswith("https://github.com/")


def test_generated_content_repository_links_match_owner_repo_paths():
    categories = CATEGORIES[:2]
    global_items = [_make_repo(name="org/global-repo")]
    category_items = {
        categories[0]["tag"]: [_make_repo(name="org/java-repo")],
        categories[1]["tag"]: [_make_repo(name="org/node-repo")],
    }

    content = build_generated_content(global_items, categories, category_items)

    for label, target in _extract_repo_links(content):
        _assert_is_github_repository_link(label, target)


def test_committed_readme_top50_repository_links_target_github_repositories():
    readme_content = README_PATH.read_text(encoding="utf-8")
    top50_block = _extract_top50_block(readme_content)
    repo_links = _extract_repo_links(top50_block)

    assert len(repo_links) >= 50
    for label, target in repo_links:
        _assert_is_github_repository_link(label, target)


def test_committed_readme_top50_internal_links_reference_existing_headings():
    readme_content = README_PATH.read_text(encoding="utf-8")
    top50_block = _extract_top50_block(readme_content)
    headings = {match.group("title") for match in HEADING_RE.finditer(readme_content)}

    internal_links = _extract_internal_links(top50_block)

    assert internal_links
    for label, _ in internal_links:
        assert label in headings

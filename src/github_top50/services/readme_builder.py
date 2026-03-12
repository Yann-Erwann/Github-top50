"""README rendering helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from github_top50.domain.models import Category
from github_top50.utils.slug import slugify


def build_table(items: Sequence[Mapping[str, Any]], start: int = 1) -> str:
    """Build a markdown table from repository items."""
    lines = [
        "| # | Repository | Description | ⭐ Stars | Langage |",
        "|---:|---|---|---:|---|",
    ]
    for idx, repo in enumerate(items, start=start):
        name = repo["full_name"]
        html_url = repo["html_url"]
        stars = repo["stargazers_count"]
        language = repo["language"] or "-"
        desc = (repo.get("description") or "-").replace("|", "\\|")
        if len(desc) > 100:
            desc = desc[:97] + "..."
        lines.append(
            f"| {idx} | [{name}]({html_url}) | {desc} | {stars:,} | {language} |"
        )
    return "\n".join(lines)


def build_toc(categories: Sequence[Category]) -> str:
    """Build the README table of contents."""
    toc_lines = ["#### 📑 Sommaire\n"]
    toc_lines.append("- [🏆 Top 50 GitHub Stars](#-top-50-github-stars)")
    toc_lines.append("- [📂 Top par catégorie](#-top-par-catégorie)")
    for category in categories:
        toc_lines.append(f"  - [{category['title']}](#{slugify(category['title'])})")
    return "\n".join(toc_lines)


def build_category_section(
    category: Category, items: Sequence[Mapping[str, Any]]
) -> str:
    """Render a single category section with stable markers."""
    tag_start = f"<!-- {category['tag']}:START -->"
    tag_end = f"<!-- {category['tag']}:END -->"
    table = build_table(items)
    return f"### {category['title']}\n\n{tag_start}\n{table}\n{tag_end}"


def build_generated_content(
    global_items: Sequence[Mapping[str, Any]],
    categories: Sequence[Category],
    category_items: Mapping[str, Sequence[Mapping[str, Any]]],
) -> str:
    """Assemble the full generated README block."""
    global_table = build_table(global_items)
    category_sections = [
        build_category_section(category, category_items[category["tag"]])
        for category in categories
    ]
    categories_block = "\n\n".join(category_sections)
    toc = build_toc(categories)
    return f"{toc}\n\n{global_table}\n\n## 📂 Top par catégorie\n\n{categories_block}"


def update_readme(
    readme_path: Path,
    start_marker: str,
    end_marker: str,
    generated_content: str,
) -> None:
    """Replace content between markers in the README."""
    content = readme_path.read_text(encoding="utf-8")

    if start_marker not in content or end_marker not in content:
        raise RuntimeError("Balises TOP50 introuvables dans README.md")

    before = content.split(start_marker)[0]
    after = content.split(end_marker)[1]
    new_content = f"{before}{start_marker}\n{generated_content}\n{end_marker}{after}"
    readme_path.write_text(new_content, encoding="utf-8")

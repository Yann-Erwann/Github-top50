"""README rendering helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from github_top50.domain.models import (
    CategoryLike,
    ReadmeSection,
    RepositoryLike,
    to_category_definition,
    to_repository,
)
from github_top50.utils.slug import slugify

TOP_50_TITLE = "🏆 Top 50 GitHub Stars"
TOP_50_DESCRIPTION = (
    "Les 50 dépôts les plus populaires sur GitHub, mis à jour quotidiennement."
)
TOP_BY_CATEGORY_TITLE = "📂 Top par catégorie"


def build_table(items: Sequence[RepositoryLike], start: int = 1) -> str:
    """Build a markdown table from repository items."""
    lines = [
        "| # | Repository | Description | ⭐ Stars | Langage |",
        "|---:|---|---|---:|---|",
    ]
    for idx, repo in enumerate(items, start=start):
        repository = to_repository(repo)
        name = repository.full_name
        html_url = repository.html_url
        stars = repository.stargazers_count
        language = repository.language or "-"
        desc = (repository.description or "-").replace("|", "\\|")
        if len(desc) > 100:
            desc = desc[:97] + "..."
        lines.append(
            f"| {idx} | [{name}]({html_url}) | {desc} | {stars:,} | {language} |"
        )
    return "\n".join(lines)


def build_toc(categories: Sequence[CategoryLike]) -> str:
    """Build the README table of contents."""
    toc_lines = ["#### 📑 Sommaire\n"]
    toc_lines.append(f"- [{TOP_50_TITLE}](#{slugify(TOP_50_TITLE)})")
    toc_lines.append(f"- [{TOP_BY_CATEGORY_TITLE}](#{slugify(TOP_BY_CATEGORY_TITLE)})")
    for category in categories:
        category_definition = to_category_definition(category)
        toc_lines.append(
            f"  - [{category_definition.title}](#{slugify(category_definition.title)})"
        )
    return "\n".join(toc_lines)


def build_category_section(
    category: CategoryLike, items: Sequence[RepositoryLike]
) -> str:
    """Render a single category section with stable markers."""
    return create_category_section(category, items).render()


def create_category_section(
    category: CategoryLike, items: Sequence[RepositoryLike]
) -> ReadmeSection:
    """Build a typed README section for a category."""
    category_definition = to_category_definition(category)
    return ReadmeSection(
        title=category_definition.title,
        content=build_table(items),
        anchor=slugify(category_definition.title),
        start_marker=f"<!-- {category_definition.tag}:START -->",
        end_marker=f"<!-- {category_definition.tag}:END -->",
    )


def build_generated_content(
    global_items: Sequence[RepositoryLike],
    categories: Sequence[CategoryLike],
    category_items: Mapping[str, Sequence[RepositoryLike]],
) -> str:
    """Assemble the full generated README block."""
    normalized_categories = tuple(
        to_category_definition(category) for category in categories
    )
    global_table = build_table(global_items)
    category_sections = [
        create_category_section(category, category_items[category.tag]).render()
        for category in normalized_categories
    ]
    categories_block = "\n\n".join(category_sections)
    toc = build_toc(normalized_categories)
    global_section = ReadmeSection(
        title=TOP_50_TITLE,
        content=f"{TOP_50_DESCRIPTION}\n\n{global_table}",
        heading_level=2,
        anchor=slugify(TOP_50_TITLE),
    )
    categories_section = ReadmeSection(
        title=TOP_BY_CATEGORY_TITLE,
        content=categories_block,
        heading_level=2,
        anchor=slugify(TOP_BY_CATEGORY_TITLE),
    )
    return f"{toc}\n\n{global_section.render()}\n\n{categories_section.render()}"


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

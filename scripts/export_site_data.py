"""Export a consolidated JSON payload for the GitHub Pages site."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from github_top50.config import (  # noqa: E402
    CATEGORIES,
    CATEGORY_PER_PAGE,
    GLOBAL_QUERY,
    HISTORY_DIR,
    HOSTING_RECOMMENDATIONS,
    LATEST_SNAPSHOT_PATH,
    PER_PAGE,
)

DEFAULT_OUTPUT_PATH = Path("site/public/data/site-data.json")
ALLOWED_REPOSITORY_HOSTS = frozenset({"github.com"})
ALLOWED_HOSTING_HOSTS = frozenset({"render.com", "vercel.com"})

CATEGORY_ACCENTS = (
    "aurora",
    "cobalt",
    "sun",
    "mint",
    "ember",
    "signal",
)

RepositoryKey = int | str


def is_allowed_host(host: str, allowed_hosts: frozenset[str]) -> bool:
    """Return whether a host matches the configured allowlist."""
    return any(
        host == allowed or host.endswith(f".{allowed}") for allowed in allowed_hosts
    )


def require_https_url(
    value: object,
    *,
    allowed_hosts: frozenset[str],
    label: str,
) -> str:
    """Validate external URLs before they are written into the static site data."""
    url = str(value)
    parsed = urlparse(url)

    if parsed.scheme != "https" or not is_allowed_host(parsed.netloc, allowed_hosts):
        raise ValueError(f"Unsafe {label} URL: {url}")

    return url


def build_category_description(title: str) -> str:
    """Return a short editorial summary for a category card."""
    sanitized_title = " ".join(title.split())
    return (
        f"Repos les plus suivis pour {sanitized_title}, "
        "avec un focus sur les stacks et outils qui structurent l'écosystème."
    )


def build_hosting_fit(stack: str) -> str:
    """Classify the hosting recommendation for the frontend site."""
    lowered_stack = stack.lower()

    if "docker" in lowered_stack and any(
        keyword in lowered_stack for keyword in ("react", "next", "angular")
    ):
        return "Frontend containerisé"
    if "docker" in lowered_stack:
        return "Services conteneurisés"
    if any(keyword in lowered_stack for keyword in ("react", "next", "angular")):
        return "Frontend statique et previews"
    return "Validation rapide"


def repository_key(item: Mapping[str, Any]) -> RepositoryKey:
    """Return the stable key used to match repositories across snapshots."""
    repo_id = item.get("id")

    if isinstance(repo_id, int) and not isinstance(repo_id, bool):
        return repo_id

    return str(item["full_name"])


def to_int_or_none(value: object) -> int | None:
    """Normalize JSON integer values while rejecting booleans."""
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def rank_from_item(item: Mapping[str, Any], fallback_rank: int) -> int:
    """Return an item's rank, falling back to its position in the list."""
    rank = to_int_or_none(item.get("rank"))

    return fallback_rank if rank is None else rank


def build_rank_index(items: Sequence[Mapping[str, Any]]) -> dict[RepositoryKey, int]:
    """Build a repository-to-rank index from a historical item list."""
    return {
        repository_key(item): rank_from_item(item, fallback_rank)
        for fallback_rank, item in enumerate(items, start=1)
    }


def previous_rank_for(
    item: Mapping[str, Any],
    previous_ranks: Mapping[RepositoryKey, int] | None,
) -> int | None:
    """Return the previous rank from explicit data or from historical snapshots."""
    explicit_previous_rank = to_int_or_none(item.get("previous_rank"))
    if explicit_previous_rank is not None:
        return explicit_previous_rank

    explicit_previous_rank = to_int_or_none(item.get("previousRank"))
    if explicit_previous_rank is not None:
        return explicit_previous_rank

    return None if previous_ranks is None else previous_ranks.get(repository_key(item))


def to_camel_repository(
    item: Mapping[str, Any],
    fallback_rank: int,
    previous_ranks: Mapping[RepositoryKey, int] | None = None,
) -> dict[str, Any]:
    """Normalize repository records for the TypeScript frontend contract."""
    full_name = str(item["full_name"])
    owner, _, name = full_name.partition("/")

    return {
        "id": item.get("id"),
        "rank": item.get("rank", fallback_rank),
        "previousRank": previous_rank_for(item, previous_ranks),
        "fullName": full_name,
        "owner": owner,
        "name": name or full_name,
        "htmlUrl": require_https_url(
            item["html_url"],
            allowed_hosts=ALLOWED_REPOSITORY_HOSTS,
            label="GitHub repository",
        ),
        "stargazersCount": item["stargazers_count"],
        "language": item.get("language"),
        "description": item.get("description"),
    }


def build_language_stats(items: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate repository counts by language for the summary ribbon."""
    counts: dict[str, int] = {}

    for item in items:
        language = str(item.get("language") or "Mixte")
        counts[language] = counts.get(language, 0) + 1

    return [
        {"name": name, "repositoryCount": repository_count}
        for name, repository_count in sorted(
            counts.items(),
            key=lambda entry: (-entry[1], entry[0]),
        )[:6]
    ]


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser for the site export."""
    parser = argparse.ArgumentParser(
        description="Export consolidated JSON data for the GitHub Pages frontend."
    )
    parser.add_argument(
        "--input-path",
        type=Path,
        default=LATEST_SNAPSHOT_PATH,
        help="Path to the source snapshot JSON file.",
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to the consolidated site JSON file.",
    )
    parser.add_argument(
        "--history-dir",
        type=Path,
        default=HISTORY_DIR,
        help="Directory containing historical snapshot JSON files.",
    )
    return parser


def utc_now() -> str:
    """Return an ISO 8601 UTC timestamp without microseconds."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_snapshot_timestamp(value: object) -> datetime | None:
    """Parse a snapshot timestamp into a UTC datetime."""
    if not isinstance(value, str):
        return None

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)

    return parsed.astimezone(UTC)


def load_snapshot(input_path: Path) -> dict[str, Any]:
    """Load the raw Top 50 snapshot from disk."""
    with input_path.open(encoding="utf-8") as input_file:
        return json.load(input_file)


def load_previous_snapshot(
    current_snapshot: Mapping[str, Any],
    *,
    history_dir: Path = HISTORY_DIR,
) -> dict[str, Any] | None:
    """Load the latest historical snapshot captured before the current snapshot."""
    current_timestamp = parse_snapshot_timestamp(current_snapshot.get("captured_at"))
    if current_timestamp is None or not history_dir.exists():
        return None

    previous_snapshot: dict[str, Any] | None = None
    previous_timestamp: datetime | None = None

    for history_path in history_dir.glob("*.json"):
        candidate = load_snapshot(history_path)
        candidate_timestamp = parse_snapshot_timestamp(candidate.get("captured_at"))

        if candidate_timestamp is None or candidate_timestamp >= current_timestamp:
            continue

        if previous_timestamp is None or candidate_timestamp > previous_timestamp:
            previous_snapshot = candidate
            previous_timestamp = candidate_timestamp

    return previous_snapshot


def validate_category_tags(snapshot_categories: Mapping[str, Any]) -> None:
    """Fail fast if snapshot category tags drift from the static configuration."""
    configured_tags = [category.tag for category in CATEGORIES]
    configured_tag_set = set(configured_tags)
    snapshot_tag_set = set(snapshot_categories)

    missing_tags = [tag for tag in configured_tags if tag not in snapshot_tag_set]
    extra_tags = sorted(snapshot_tag_set - configured_tag_set)

    if missing_tags or extra_tags:
        issues: list[str] = []
        if missing_tags:
            issues.append(f"missing tags: {', '.join(missing_tags)}")
        if extra_tags:
            issues.append(f"unexpected tags: {', '.join(extra_tags)}")
        raise ValueError(
            "Snapshot categories do not match static configuration: "
            + "; ".join(issues)
        )


def category_rank_index(
    previous_categories: Mapping[str, Any],
    tag: str,
) -> dict[RepositoryKey, int] | None:
    """Build the historical rank index for a category, if it exists."""
    previous_category = previous_categories.get(tag)

    if not isinstance(previous_category, Mapping):
        return None

    previous_items = previous_category.get("items")

    if not isinstance(previous_items, list):
        return None

    return build_rank_index(previous_items)


def build_site_payload(
    snapshot: Mapping[str, Any],
    *,
    input_path: Path = LATEST_SNAPSHOT_PATH,
    generated_at: str | None = None,
    previous_snapshot: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the site payload by combining raw snapshot data and static metadata."""
    snapshot_categories = snapshot["categories"]
    validate_category_tags(snapshot_categories)
    previous_categories = (
        previous_snapshot.get("categories", {}) if previous_snapshot is not None else {}
    )
    global_previous_ranks = (
        build_rank_index(previous_snapshot["global"]["items"])
        if previous_snapshot is not None
        else None
    )

    global_items = [
        to_camel_repository(item, index, global_previous_ranks)
        for index, item in enumerate(snapshot["global"]["items"], start=1)
    ]
    categories = []

    for index, category in enumerate(CATEGORIES):
        previous_ranks = category_rank_index(previous_categories, category.tag)
        categories.append(
            {
                "tag": category.tag,
                "title": category.title,
                "query": category.query,
                "description": build_category_description(category.title),
                "accent": CATEGORY_ACCENTS[index % len(CATEGORY_ACCENTS)],
                "items": [
                    to_camel_repository(item, item_index, previous_ranks)
                    for item_index, item in enumerate(
                        snapshot_categories[category.tag]["items"],
                        start=1,
                    )
                ],
            }
        )
    hosting = [
        {
            "stack": recommendation.stack,
            "hosting": recommendation.hosting,
            "url": require_https_url(
                recommendation.url,
                allowed_hosts=ALLOWED_HOSTING_HOSTS,
                label="hosting documentation",
            ),
            "notes": recommendation.notes,
            "fit": build_hosting_fit(recommendation.stack),
        }
        for recommendation in HOSTING_RECOMMENDATIONS
    ]
    languages = build_language_stats(global_items)
    total_stars = sum(int(item["stargazersCount"]) for item in global_items)
    captured_at = str(snapshot["captured_at"])

    return {
        "snapshot": {
            "capturedAt": captured_at,
            "label": f"Snapshot du {captured_at[:10]}",
            "source": input_path.as_posix(),
        },
        "global": {
            "title": "Top 50 GitHub Stars",
            "subtitle": (
                "Lecture éditoriale des dépôts les plus suivis sur GitHub, "
                "mise à jour à partir du snapshot versionné du repository."
            ),
            "items": global_items,
            "highlights": global_items[:3],
        },
        "categories": categories,
        "hosting": hosting,
        "stats": {
            "generatedAt": generated_at or utc_now(),
            "totalStars": total_stars,
            "repositoryCount": len(global_items),
            "categoryCount": len(categories),
            "hostingCount": len(hosting),
            "topLanguage": (
                languages[0] if languages else {"name": "Mixte", "repositoryCount": 0}
            ),
            "languages": languages,
            "globalQuery": GLOBAL_QUERY,
            "categoryLimit": CATEGORY_PER_PAGE,
            "globalLimit": PER_PAGE,
        },
    }


def export_site_data(
    input_path: Path = LATEST_SNAPSHOT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    *,
    generated_at: str | None = None,
    history_dir: Path = HISTORY_DIR,
) -> dict[str, Any]:
    """Read the snapshot, build the consolidated payload, and write it to disk."""
    snapshot = load_snapshot(input_path)
    previous_snapshot = load_previous_snapshot(snapshot, history_dir=history_dir)
    payload = build_site_payload(
        snapshot,
        input_path=input_path,
        generated_at=generated_at,
        previous_snapshot=previous_snapshot,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return payload


def main(argv: Sequence[str] | None = None) -> None:
    """Export consolidated JSON data for the future site."""
    args = build_parser().parse_args(list(argv) if argv is not None else [])
    export_site_data(
        input_path=args.input_path,
        output_path=args.output_path,
        history_dir=args.history_dir,
    )


if __name__ == "__main__":
    main(sys.argv[1:])

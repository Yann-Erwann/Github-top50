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
    PERIODS,
)
from github_top50.domain.models import PeriodDefinition  # noqa: E402
from github_top50.services.periods import period_start_timestamp  # noqa: E402

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


def build_period_performance(
    items: Sequence[Mapping[str, Any]],
    baseline_items: Sequence[Mapping[str, Any]] | None,
) -> dict[RepositoryKey, dict[str, int | None]]:
    """Rank tracked repositories by stars gained since a historical snapshot."""
    if baseline_items is None:
        return {
            repository_key(item): {"rank": None, "starsGained": None} for item in items
        }

    baseline_by_key = {repository_key(item): item for item in baseline_items}
    performance: dict[RepositoryKey, dict[str, int | None]] = {}
    ranked_items: list[tuple[RepositoryKey, int, int, int]] = []

    for fallback_rank, item in enumerate(items, start=1):
        key = repository_key(item)
        baseline_item = baseline_by_key.get(key)
        baseline_stars = (
            to_int_or_none(baseline_item.get("stargazers_count"))
            if baseline_item is not None
            else None
        )
        current_stars = to_int_or_none(item.get("stargazers_count"))
        stars_gained = (
            current_stars - baseline_stars
            if current_stars is not None and baseline_stars is not None
            else None
        )
        performance[key] = {"rank": None, "starsGained": stars_gained}

        if stars_gained is not None:
            ranked_items.append(
                (
                    key,
                    stars_gained,
                    current_stars or 0,
                    rank_from_item(item, fallback_rank),
                )
            )

    ranked_items.sort(key=lambda entry: (-entry[1], -entry[2], entry[3]))

    for period_rank, (key, _, _, _) in enumerate(ranked_items, start=1):
        performance[key]["rank"] = period_rank

    return performance


def explicit_previous_rank_for(item: Mapping[str, Any]) -> int | None:
    """Return an item's explicit previous rank, if the source snapshot provides one."""
    explicit_previous_rank = to_int_or_none(item.get("previous_rank"))
    if explicit_previous_rank is not None:
        return explicit_previous_rank

    return to_int_or_none(item.get("previousRank"))


def previous_rank_for(
    item: Mapping[str, Any],
    previous_ranks: Mapping[RepositoryKey, int] | None,
) -> int | None:
    """Return the previous rank from explicit data or from historical snapshots."""
    explicit_previous_rank = explicit_previous_rank_for(item)
    if explicit_previous_rank is not None:
        return explicit_previous_rank

    return None if previous_ranks is None else previous_ranks.get(repository_key(item))


def movement_rank_for(
    item: Mapping[str, Any],
    previous_ranks: Mapping[RepositoryKey, int] | None,
) -> int | None:
    """Return a historical rank for a comparison period."""
    return None if previous_ranks is None else previous_ranks.get(repository_key(item))


def period_value_for(
    item: Mapping[str, Any],
    period_performance: Mapping[str, Mapping[RepositoryKey, Mapping[str, int | None]]]
    | None,
    field: str,
) -> dict[str, int | None]:
    """Return one period performance field for a repository."""
    key = repository_key(item)

    return {
        period_id: performance.get(key, {}).get(field)
        for period_id, performance in (period_performance or {}).items()
    }


def merge_repository_items(
    *item_lists: Sequence[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    """Merge repository lists while preserving the first occurrence of each item."""
    merged_items: list[Mapping[str, Any]] = []
    seen_keys: set[RepositoryKey] = set()

    for items in item_lists:
        for item in items:
            key = repository_key(item)
            if key in seen_keys:
                continue

            seen_keys.add(key)
            merged_items.append(item)

    return merged_items


def snapshot_period_items(
    snapshot: Mapping[str, Any],
    period_id: str,
) -> list[Mapping[str, Any]] | None:
    """Return an API-backed period repository list from an enriched snapshot."""
    periods = snapshot.get("periods")
    if not isinstance(periods, Mapping):
        return None

    section = periods.get(period_id)
    if not isinstance(section, Mapping):
        return None

    items = section.get("items")
    return items if isinstance(items, list) else None


def build_api_period_performance(
    items: Sequence[Mapping[str, Any]],
) -> dict[RepositoryKey, dict[str, int | None]]:
    """Build rankings from API results for repositories created during a period."""
    return {
        repository_key(item): {
            "rank": rank_from_item(item, fallback_rank),
            "starsGained": to_int_or_none(item.get("stargazers_count")),
        }
        for fallback_rank, item in enumerate(items, start=1)
    }


def build_global_catalog(snapshot: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return every repository needed to render global period rankings."""
    item_lists: list[Sequence[Mapping[str, Any]]] = [snapshot["global"]["items"]]

    for period in PERIODS:
        if period.all_time:
            continue

        items = snapshot_period_items(snapshot, period.id)
        if items is not None:
            item_lists.append(items)

    return merge_repository_items(*item_lists)


def to_camel_repository(
    item: Mapping[str, Any],
    fallback_rank: int,
    previous_ranks: Mapping[RepositoryKey, int] | None = None,
    period_rank_indexes: Mapping[str, Mapping[RepositoryKey, int] | None] | None = None,
    period_performance: Mapping[str, Mapping[RepositoryKey, Mapping[str, int | None]]]
    | None = None,
) -> dict[str, Any]:
    """Normalize repository records for the TypeScript frontend contract."""
    full_name = str(item["full_name"])
    owner, _, name = full_name.partition("/")
    rank = rank_from_item(item, fallback_rank)

    return {
        "id": item.get("id"),
        "rank": rank,
        "previousRank": previous_rank_for(item, previous_ranks),
        "movements": {
            period_id: movement_rank_for(item, rank_index)
            for period_id, rank_index in (period_rank_indexes or {}).items()
        },
        "periodRankings": period_value_for(item, period_performance, "rank"),
        "periodStarsGained": period_value_for(item, period_performance, "starsGained"),
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


def period_target_timestamp(
    current_timestamp: datetime,
    period: PeriodDefinition,
) -> datetime | None:
    """Return the desired historical timestamp for a comparison period."""
    return period_start_timestamp(current_timestamp, period)


def load_history_snapshots(
    current_snapshot: Mapping[str, Any],
    *,
    history_dir: Path = HISTORY_DIR,
) -> list[tuple[datetime, dict[str, Any]]]:
    """Load historical snapshots captured before the current snapshot."""
    current_timestamp = parse_snapshot_timestamp(current_snapshot.get("captured_at"))
    if current_timestamp is None or not history_dir.exists():
        return []

    history_snapshots: list[tuple[datetime, dict[str, Any]]] = []

    for history_path in history_dir.glob("*.json"):
        candidate = load_snapshot(history_path)
        candidate_timestamp = parse_snapshot_timestamp(candidate.get("captured_at"))

        if candidate_timestamp is None or candidate_timestamp >= current_timestamp:
            continue

        history_snapshots.append((candidate_timestamp, candidate))

    return sorted(history_snapshots, key=lambda entry: entry[0])


def load_previous_snapshot(
    current_snapshot: Mapping[str, Any],
    *,
    history_dir: Path = HISTORY_DIR,
) -> dict[str, Any] | None:
    """Load the latest historical snapshot captured before the current snapshot."""
    history_snapshots = load_history_snapshots(
        current_snapshot, history_dir=history_dir
    )

    return history_snapshots[-1][1] if history_snapshots else None


def select_period_snapshot(
    history_snapshots: Sequence[tuple[datetime, Mapping[str, Any]]],
    current_timestamp: datetime,
    period: PeriodDefinition,
) -> Mapping[str, Any] | None:
    """Select the best historical snapshot for a comparison period."""
    if not history_snapshots:
        return None

    if period.all_time:
        return history_snapshots[0][1]

    target_timestamp = period_target_timestamp(current_timestamp, period)
    if target_timestamp is None:
        return history_snapshots[-1][1]

    selected_snapshot: Mapping[str, Any] | None = None

    for snapshot_timestamp, snapshot in history_snapshots:
        if snapshot_timestamp <= target_timestamp:
            selected_snapshot = snapshot
            continue

        break

    return selected_snapshot or history_snapshots[0][1]


def build_period_snapshots(
    current_snapshot: Mapping[str, Any],
    history_snapshots: Sequence[tuple[datetime, Mapping[str, Any]]],
) -> dict[str, Mapping[str, Any] | None]:
    """Map each configured period to its selected historical snapshot."""
    current_timestamp = parse_snapshot_timestamp(current_snapshot.get("captured_at"))
    if current_timestamp is None:
        return {period.id: None for period in PERIODS}

    return {
        period.id: select_period_snapshot(history_snapshots, current_timestamp, period)
        for period in PERIODS
    }


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


def category_period_rank_indexes(
    period_snapshots: Mapping[str, Mapping[str, Any] | None],
    tag: str,
) -> dict[str, dict[RepositoryKey, int] | None]:
    """Build category rank indexes for every comparison period."""
    period_ranks: dict[str, dict[RepositoryKey, int] | None] = {}

    for period_id, snapshot in period_snapshots.items():
        previous_categories = snapshot.get("categories", {}) if snapshot else {}
        period_ranks[period_id] = category_rank_index(previous_categories, tag)

    return period_ranks


def category_period_performance(
    items: Sequence[Mapping[str, Any]],
    period_snapshots: Mapping[str, Mapping[str, Any] | None],
    tag: str,
) -> dict[str, dict[RepositoryKey, dict[str, int | None]]]:
    """Rank tracked category repositories by stars gained for every period."""
    performance: dict[str, dict[RepositoryKey, dict[str, int | None]]] = {}

    for period_id, snapshot in period_snapshots.items():
        previous_categories = snapshot.get("categories", {}) if snapshot else {}
        previous_category = previous_categories.get(tag)
        previous_items = (
            previous_category.get("items")
            if isinstance(previous_category, Mapping)
            else None
        )
        performance[period_id] = build_period_performance(
            items,
            previous_items if isinstance(previous_items, list) else None,
        )

    return performance


def global_period_rank_indexes(
    period_snapshots: Mapping[str, Mapping[str, Any] | None],
) -> dict[str, dict[RepositoryKey, int] | None]:
    """Build global rank indexes for every comparison period."""
    period_ranks: dict[str, dict[RepositoryKey, int] | None] = {}

    for period_id, snapshot in period_snapshots.items():
        if snapshot is None:
            period_ranks[period_id] = None
            continue

        period_ranks[period_id] = build_rank_index(snapshot["global"]["items"])

    return period_ranks


def global_period_performance(
    items: Sequence[Mapping[str, Any]],
    current_snapshot: Mapping[str, Any],
    period_snapshots: Mapping[str, Mapping[str, Any] | None],
) -> dict[str, dict[RepositoryKey, dict[str, int | None]]]:
    """Rank tracked global repositories by stars gained for every period."""
    performance = {
        period_id: build_period_performance(
            items,
            snapshot["global"]["items"] if snapshot is not None else None,
        )
        for period_id, snapshot in period_snapshots.items()
    }

    for period in PERIODS:
        explicit_items = (
            current_snapshot["global"]["items"]
            if period.all_time
            else snapshot_period_items(current_snapshot, period.id)
        )
        if explicit_items is not None:
            performance[period.id] = build_api_period_performance(explicit_items)

    return performance


def build_period_metadata(
    period_snapshots: Mapping[str, Mapping[str, Any] | None],
    current_snapshot: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Build the frontend metadata for the period selector."""
    metadata: list[dict[str, Any]] = []

    for period in PERIODS:
        snapshot = period_snapshots.get(period.id)
        explicit_section = (
            None
            if period.all_time
            else current_snapshot.get("periods", {}).get(period.id)
        )
        starts_at = (
            str(explicit_section.get("starts_at"))
            if isinstance(explicit_section, Mapping)
            and explicit_section.get("starts_at") is not None
            else None
        )
        baseline_captured_at = (
            str(snapshot["captured_at"]) if snapshot is not None else None
        )
        metadata.append(
            {
                "id": period.id,
                "label": period.label,
                "days": period.days,
                "months": period.months,
                "available": period.all_time
                or starts_at is not None
                or snapshot is not None,
                "baselineCapturedAt": baseline_captured_at,
                "startsAt": starts_at,
                "rankingMode": (
                    "all"
                    if period.all_time
                    else "created"
                    if starts_at is not None
                    else "tracked-delta"
                ),
            }
        )

    return metadata


def build_site_payload(
    snapshot: Mapping[str, Any],
    *,
    input_path: Path = LATEST_SNAPSHOT_PATH,
    generated_at: str | None = None,
    previous_snapshot: Mapping[str, Any] | None = None,
    period_snapshots: Mapping[str, Mapping[str, Any] | None] | None = None,
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
    selected_period_snapshots = (
        {period.id: period_snapshots.get(period.id) for period in PERIODS}
        if period_snapshots is not None
        else {period.id: previous_snapshot for period in PERIODS}
    )
    global_period_ranks = global_period_rank_indexes(selected_period_snapshots)
    global_catalog = build_global_catalog(snapshot)
    global_performance = global_period_performance(
        global_catalog,
        snapshot,
        selected_period_snapshots,
    )

    global_items = [
        to_camel_repository(
            item,
            index,
            global_previous_ranks,
            global_period_ranks,
            global_performance,
        )
        for index, item in enumerate(global_catalog, start=1)
    ]
    categories = []

    for index, category in enumerate(CATEGORIES):
        previous_ranks = category_rank_index(previous_categories, category.tag)
        period_ranks = category_period_rank_indexes(
            selected_period_snapshots,
            category.tag,
        )
        category_items = snapshot_categories[category.tag]["items"]
        period_performance = category_period_performance(
            category_items,
            selected_period_snapshots,
            category.tag,
        )
        categories.append(
            {
                "tag": category.tag,
                "title": category.title,
                "query": category.query,
                "description": build_category_description(category.title),
                "accent": CATEGORY_ACCENTS[index % len(CATEGORY_ACCENTS)],
                "items": [
                    to_camel_repository(
                        item,
                        item_index,
                        previous_ranks,
                        period_ranks,
                        period_performance,
                    )
                    for item_index, item in enumerate(
                        category_items,
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
    current_global_items = global_items[: len(snapshot["global"]["items"])]
    languages = build_language_stats(current_global_items)
    total_stars = sum(int(item["stargazersCount"]) for item in current_global_items)
    captured_at = str(snapshot["captured_at"])

    return {
        "snapshot": {
            "capturedAt": captured_at,
            "label": f"Snapshot du {captured_at[:10]}",
            "source": input_path.as_posix(),
        },
        "periods": build_period_metadata(selected_period_snapshots, snapshot),
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
            "repositoryCount": len(current_global_items),
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
    history_snapshots = load_history_snapshots(snapshot, history_dir=history_dir)
    previous_snapshot = history_snapshots[-1][1] if history_snapshots else None
    period_snapshots = build_period_snapshots(snapshot, history_snapshots)
    payload = build_site_payload(
        snapshot,
        input_path=input_path,
        generated_at=generated_at,
        previous_snapshot=previous_snapshot,
        period_snapshots=period_snapshots,
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

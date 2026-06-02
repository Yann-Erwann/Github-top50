from datetime import datetime, timezone

from github_top50.config import HISTORY_DIR, LATEST_SNAPSHOT_PATH
from github_top50.domain.models import CategoryDefinition, PeriodDefinition, Repository
from github_top50.services.history_store import SnapshotStore, apply_rank_changes


def _make_repo(
    *,
    repo_id: int,
    name: str,
    stars: int = 100,
    rank: int | None = None,
) -> Repository:
    return Repository(
        full_name=name,
        html_url=f"https://github.com/{name}",
        stargazers_count=stars,
        language="Python",
        description="A repo",
        id=repo_id,
        rank=rank,
    )


def test_apply_rank_changes_marks_new_and_previous_positions():
    previous_items = [
        _make_repo(repo_id=1, name="org/one", rank=1),
        _make_repo(repo_id=2, name="org/two", rank=2),
        _make_repo(repo_id=3, name="org/three", rank=3),
    ]
    current_items = [
        _make_repo(repo_id=2, name="org/two"),
        _make_repo(repo_id=1, name="org/one"),
        _make_repo(repo_id=4, name="org/four"),
    ]

    ranked = apply_rank_changes(current_items, previous_items)

    assert ranked[0].rank == 1
    assert ranked[0].previous_rank == 2
    assert ranked[1].rank == 2
    assert ranked[1].previous_rank == 1
    assert ranked[2].rank == 3
    assert ranked[2].previous_rank is None


def test_snapshot_store_round_trips_latest_snapshot(tmp_path):
    store = SnapshotStore(
        latest_snapshot_path=tmp_path / LATEST_SNAPSHOT_PATH,
        history_dir=tmp_path / HISTORY_DIR,
    )
    categories = (CategoryDefinition(title="Cat A", tag="A", query="q-a"),)
    previous_global_items = [
        _make_repo(repo_id=99, name="org/old", rank=1),
        _make_repo(repo_id=1, name="org/one", rank=2),
    ]
    previous_category_items = [
        _make_repo(repo_id=99, name="org/old-cat", rank=1),
        _make_repo(repo_id=10, name="org/cat-a", rank=2),
    ]
    global_items = apply_rank_changes(
        [_make_repo(repo_id=1, name="org/one")],
        previous_global_items,
    )
    category_items = {
        "A": apply_rank_changes(
            [_make_repo(repo_id=10, name="org/cat-a")],
            previous_category_items,
        )
    }
    periods = (
        PeriodDefinition(id="7d", label="7 jours", days=7),
        PeriodDefinition(id="all", label="Toute la période", all_time=True),
    )
    period_items = {"7d": [_make_repo(repo_id=20, name="org/recent", rank=1)]}

    history_path = store.save(
        captured_at=datetime(2026, 3, 18, 6, 0, 0, tzinfo=timezone.utc),
        global_items=global_items,
        categories=categories,
        category_items=category_items,
        periods=periods,
        period_items=period_items,
    )

    latest = store.load_latest()

    assert history_path.name == "2026-03-18T06-00-00Z.json"
    assert latest is not None
    assert latest.captured_at == "2026-03-18T06:00:00Z"
    assert latest.global_items[0].full_name == "org/one"
    assert latest.global_items[0].rank == 1
    assert latest.global_items[0].previous_rank == 2
    assert latest.category_items["A"][0].full_name == "org/cat-a"
    assert latest.category_items["A"][0].rank == 1
    assert latest.category_items["A"][0].previous_rank == 2
    assert latest.period_items["7d"][0].full_name == "org/recent"
    payload = history_path.read_text(encoding="utf-8")
    assert '"query": "created:>=2026-03-11"' in payload
    assert '"starts_at": "2026-03-11T06:00:00Z"' in payload

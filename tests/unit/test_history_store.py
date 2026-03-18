from datetime import datetime, timezone

from github_top50.config import HISTORY_DIR, LATEST_SNAPSHOT_PATH
from github_top50.domain.models import CategoryDefinition, Repository
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
    global_items = apply_rank_changes([_make_repo(repo_id=1, name="org/one")])
    category_items = {
        "A": apply_rank_changes([_make_repo(repo_id=10, name="org/cat-a")])
    }

    history_path = store.save(
        captured_at=datetime(2026, 3, 18, 6, 0, 0, tzinfo=timezone.utc),
        global_items=global_items,
        categories=categories,
        category_items=category_items,
    )

    latest = store.load_latest()

    assert history_path.name == "2026-03-18T06-00-00Z.json"
    assert latest is not None
    assert latest.captured_at == "2026-03-18T06:00:00Z"
    assert latest.global_items[0].full_name == "org/one"
    assert latest.global_items[0].rank == 1
    assert latest.category_items["A"][0].full_name == "org/cat-a"
    assert latest.category_items["A"][0].rank == 1

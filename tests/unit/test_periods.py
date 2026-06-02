from datetime import datetime, timezone

import pytest

from github_top50.domain.models import PeriodDefinition
from github_top50.services.periods import (
    build_created_period_query,
    period_start_timestamp,
    subtract_months,
)


def test_subtract_months_clamps_day_to_target_month():
    timestamp = datetime(2026, 3, 31, 12, 0, tzinfo=timezone.utc)

    assert subtract_months(timestamp, 1) == datetime(
        2026,
        2,
        28,
        12,
        0,
        tzinfo=timezone.utc,
    )


def test_period_start_timestamp_supports_days_and_calendar_months():
    timestamp = datetime(2026, 4, 4, 7, 36, tzinfo=timezone.utc)

    assert period_start_timestamp(
        timestamp,
        PeriodDefinition(id="7d", label="7 jours", days=7),
    ) == datetime(2026, 3, 28, 7, 36, tzinfo=timezone.utc)
    assert period_start_timestamp(
        timestamp,
        PeriodDefinition(id="2m", label="2 mois", months=2),
    ) == datetime(2026, 2, 4, 7, 36, tzinfo=timezone.utc)
    assert (
        period_start_timestamp(
            timestamp,
            PeriodDefinition(id="all", label="Toute la période", all_time=True),
        )
        is None
    )


def test_build_created_period_query_uses_inclusive_start_date():
    timestamp = datetime(2026, 4, 4, 7, 36, tzinfo=timezone.utc)

    assert (
        build_created_period_query(
            timestamp,
            PeriodDefinition(id="7d", label="7 jours", days=7),
        )
        == "created:>=2026-03-28"
    )


def test_build_created_period_query_rejects_unbounded_period():
    with pytest.raises(ValueError, match="does not have a bounded start date"):
        build_created_period_query(
            datetime(2026, 4, 4, tzinfo=timezone.utc),
            PeriodDefinition(id="all", label="Toute la période", all_time=True),
        )

"""Shared helpers for repository ranking periods."""

from __future__ import annotations

from calendar import monthrange
from datetime import datetime, timedelta

from github_top50.domain.models import PeriodDefinition


def subtract_months(value: datetime, months: int) -> datetime:
    """Return a timestamp shifted back by a whole number of calendar months."""
    month_index = value.month - months - 1
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, monthrange(year, month)[1])

    return value.replace(year=year, month=month, day=day)


def period_start_timestamp(
    current_timestamp: datetime,
    period: PeriodDefinition,
) -> datetime | None:
    """Return the inclusive start timestamp for a bounded ranking period."""
    if period.all_time:
        return None

    if period.days is not None:
        return current_timestamp - timedelta(days=period.days)

    if period.months is not None:
        return subtract_months(current_timestamp, period.months)

    return None


def build_created_period_query(
    current_timestamp: datetime,
    period: PeriodDefinition,
) -> str:
    """Build a GitHub Search query for repositories created during a period."""
    start_timestamp = period_start_timestamp(current_timestamp, period)
    if start_timestamp is None:
        raise ValueError(f"Period {period.id!r} does not have a bounded start date")

    return f"created:>={start_timestamp.date().isoformat()}"

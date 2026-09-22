"""Pure metrics shared by InsightAgent's deterministic business tools."""

from __future__ import annotations

import re
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

_QUARTER_PATTERN = re.compile(r"^(20\d{2})Q([1-4])$")


def parse_quarter(value: str) -> tuple[date, date, date, date, date, date]:
    """Return current, prior-quarter and prior-year half-open date windows."""

    if not isinstance(value, str):
        raise ValueError("季度必须是 YYYYQn 格式，例如 2026Q2")
    match = _QUARTER_PATTERN.fullmatch(value.strip())
    if not match:
        raise ValueError("季度必须是 YYYYQn 格式，例如 2026Q2")
    year, quarter = int(match.group(1)), int(match.group(2))
    month = (quarter - 1) * 3 + 1
    current_start = date(year, month, 1)
    current_end = date(year + 1, 1, 1) if quarter == 4 else date(year, month + 3, 1)
    if quarter == 1:
        previous_start, previous_end = date(year - 1, 10, 1), date(year, 1, 1)
    else:
        previous_start, previous_end = date(year, month - 3, 1), current_start
    prior_year_start = date(year - 1, month, 1)
    prior_year_end = date(year, 1, 1) if quarter == 4 else date(year - 1, month + 3, 1)
    return (
        current_start,
        current_end,
        previous_start,
        previous_end,
        prior_year_start,
        prior_year_end,
    )


def safe_rate(
    numerator: Decimal | float | int, denominator: Decimal | float | int
) -> float | None:
    """Return a decimal rate, or ``None`` where a baseline is zero."""

    denominator_value = Decimal(str(denominator or 0))
    if denominator_value == 0:
        return None
    return float(Decimal(str(numerator or 0)) / denominator_value)


def money(value: Any) -> float:
    """Serialize monetary values as rounded RMB amounts."""

    return float(Decimal(str(value or 0)).quantize(Decimal("0.01"), ROUND_HALF_UP))


def rate(value: float | Decimal | None) -> float | None:
    """Serialize a rate in decimal form to four decimal places."""

    if value is None:
        return None
    return float(Decimal(str(value)).quantize(Decimal("0.0001"), ROUND_HALF_UP))


def change_rate(current: Any, baseline: Any) -> float | None:
    """Return ``(current - baseline) / baseline`` with a safe zero baseline."""

    return safe_rate(Decimal(str(current or 0)) - Decimal(str(baseline or 0)), baseline)


def percentage_point_change(
    current: float | Decimal | None, baseline: float | Decimal | None
) -> float | None:
    """Return the change between two decimal rates in percentage points."""

    if current is None or baseline is None:
        return None
    return float((Decimal(str(current)) - Decimal(str(baseline))) * 100)


def sales_change_score(current: Any, baseline: Any) -> int:
    """Score quarter-on-quarter sales on the Day 4 0-40 demo scale."""

    current_value = Decimal(str(current or 0))
    baseline_value = Decimal(str(baseline or 0))
    if baseline_value <= 0:
        return 40 if current_value > 0 else 0
    change = (current_value - baseline_value) / baseline_value
    if change >= 0:
        return 40
    if change >= Decimal("-0.10"):
        return 32
    if change >= Decimal("-0.20"):
        return 24
    if change >= Decimal("-0.30"):
        return 12
    return 0


def activity_score(current_days: Any, baseline_days: Any) -> int:
    """Score active purchasing days on the Day 4 0-20 demo scale."""

    current_value = Decimal(str(current_days or 0))
    baseline_value = Decimal(str(baseline_days or 0))
    if baseline_value <= 0:
        return 20 if current_value > 0 else 0
    ratio_value = current_value / baseline_value
    if ratio_value >= 1:
        return 20
    if ratio_value >= Decimal("0.8"):
        return 16
    if ratio_value >= Decimal("0.5"):
        return 10
    if ratio_value > 0:
        return 5
    return 0


def discount_score(average_discount_rate: float | Decimal | None) -> int:
    """Score the policy's line-average discount bands on a 0-20 scale."""

    if average_discount_rate is None:
        return 0
    value = Decimal(str(average_discount_rate))
    if value <= Decimal("0.08"):
        return 20
    if value <= Decimal("0.12"):
        return 14
    if value <= Decimal("0.15"):
        return 8
    return 0


def gross_margin_score(
    current_margin: float | Decimal | None,
    baseline_margin: float | Decimal | None,
) -> int:
    """Score gross-margin movement on the Day 4 0-20 demo scale."""

    if current_margin is None:
        return 0
    if baseline_margin is None:
        return 20
    decline_pp = (Decimal(str(baseline_margin)) - Decimal(str(current_margin))) * 100
    if decline_pp <= 0:
        return 20
    if decline_pp <= 1:
        return 16
    if decline_pp <= 2:
        return 12
    if decline_pp <= 5:
        return 6
    return 0


def health_risk_level(score: int) -> str:
    """Map a validated 0-100 score to the Day 4 risk band."""

    if isinstance(score, bool) or not isinstance(score, int) or not 0 <= score <= 100:
        raise ValueError("健康度分数必须是 0 到 100 的整数")
    if score >= 80:
        return "low"
    if score >= 60:
        return "medium"
    return "high"

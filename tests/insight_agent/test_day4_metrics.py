from __future__ import annotations

import pytest

from insight_agent.tools.metrics import (
    activity_score,
    change_rate,
    discount_score,
    gross_margin_score,
    health_risk_level,
    percentage_point_change,
    sales_change_score,
)


def test_change_helpers_handle_normal_and_zero_baselines() -> None:
    assert change_rate(80, 100) == -0.2
    assert change_rate(10, 0) is None
    assert percentage_point_change(0.25, 0.28) == pytest.approx(-3.0)
    assert percentage_point_change(None, 0.28) is None


@pytest.mark.parametrize(
    ("current", "baseline", "expected"),
    [
        (100, 100, 40),
        (95, 100, 32),
        (85, 100, 24),
        (75, 100, 12),
        (60, 100, 0),
        (1, 0, 40),
        (0, 0, 0),
    ],
)
def test_sales_change_score_bands(current: int, baseline: int, expected: int) -> None:
    assert sales_change_score(current, baseline) == expected


@pytest.mark.parametrize(
    ("current", "baseline", "expected"),
    [
        (10, 10, 20),
        (9, 10, 16),
        (6, 10, 10),
        (2, 10, 5),
        (0, 10, 0),
        (1, 0, 20),
        (0, 0, 0),
    ],
)
def test_activity_score_bands(current: int, baseline: int, expected: int) -> None:
    assert activity_score(current, baseline) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [(0.08, 20), (0.0801, 14), (0.12, 14), (0.13, 8), (0.15, 8), (0.16, 0), (None, 0)],
)
def test_discount_score_uses_policy_bands(value: float | None, expected: int) -> None:
    assert discount_score(value) == expected


@pytest.mark.parametrize(
    ("current", "baseline", "expected"),
    [
        (0.28, 0.27, 20),
        (0.27, 0.28, 16),
        (0.26, 0.28, 12),
        (0.24, 0.28, 6),
        (0.20, 0.28, 0),
        (None, 0.28, 0),
    ],
)
def test_gross_margin_score_bands(
    current: float | None, baseline: float, expected: int
) -> None:
    assert gross_margin_score(current, baseline) == expected


def test_health_risk_level_validates_and_maps_score() -> None:
    assert health_risk_level(80) == "low"
    assert health_risk_level(60) == "medium"
    assert health_risk_level(59) == "high"
    with pytest.raises(ValueError):
        health_risk_level(101)

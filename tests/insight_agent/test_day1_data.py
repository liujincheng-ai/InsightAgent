"""Fast deterministic checks for the Day 1 synthetic dataset generator."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from insight_agent.database.generate_data import (
    END_DATE,
    FACT_ROW_COUNT,
    RANDOM_SEED,
    START_DATE,
    build_dimensions,
    generate_sales,
)


@pytest.fixture(scope="module")
def dataset():
    regions, products, customers = build_dimensions()
    sales = generate_sales(products, customers)
    return regions, products, customers, sales


def test_dimension_and_fact_counts(dataset):
    regions, products, customers, sales = dataset
    assert len(regions) == 5
    assert len(products) == 36
    assert len(customers) == 150
    assert len(sales) == FACT_ROW_COUNT


def test_date_range_and_foreign_keys(dataset):
    regions, products, customers, sales = dataset
    region_ids = {row["region_id"] for row in regions}
    product_ids = {row["product_id"] for row in products}
    customer_ids = {row["customer_id"] for row in customers}
    dates = [row["sale_date"] for row in sales]
    assert min(dates) == START_DATE
    assert max(dates) == END_DATE
    assert all(isinstance(value, date) for value in dates)
    assert {row["region_id"] for row in sales} <= region_ids
    assert {row["product_id"] for row in sales} <= product_ids
    assert {row["customer_id"] for row in sales} <= customer_ids


def test_amount_formulas(dataset):
    _, _, _, sales = dataset
    for row in sales:
        expected_sales = (
            Decimal(row["quantity"])
            * row["unit_price"]
            * (Decimal("1") - row["discount_rate"])
        ).quantize(Decimal("0.01"))
        assert abs(row["sales_amount"] - expected_sales) <= Decimal("0.01")
        assert row["gross_profit"] == row["sales_amount"] - row["cost_amount"]


def test_fixed_seed_is_reproducible(dataset):
    _, products, customers, sales = dataset
    regenerated = generate_sales(products, customers, seed=RANDOM_SEED)
    assert regenerated == sales

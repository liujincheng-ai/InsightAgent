"""Generate the deterministic synthetic automotive-parts sales dataset."""

from __future__ import annotations

import argparse
import calendar
import csv
import hashlib
import json
import random
from collections import Counter, defaultdict
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

RANDOM_SEED = 20260904
FACT_ROW_COUNT = 60_000
START_DATE = date(2025, 1, 1)
END_DATE = date(2026, 6, 30)

REGION_NAMES = ["华东", "华南", "华北", "华中", "西南"]
REGION_MANAGERS = ["陈晓东", "林悦南", "赵明北", "周文中", "杨川西"]
CATEGORY_PRODUCTS = {
    "刹车系统": ["制动盘", "制动片", "制动钳", "制动鼓", "制动软管", "制动液"],
    "滤清系统": [
        "机油滤清器",
        "空气滤清器",
        "燃油滤清器",
        "空调滤清器",
        "液压滤芯",
        "变速箱滤芯",
    ],
    "点火系统": ["火花塞", "点火线圈", "高压线", "点火模块", "分电器", "预热塞"],
    "悬挂系统": ["减震器", "控制臂", "球头", "稳定杆", "悬挂弹簧", "顶胶"],
    "照明系统": ["前照灯", "尾灯", "雾灯", "转向灯", "日间行车灯", "牌照灯"],
    "雨刮及易损件": ["雨刮片", "雨刮电机", "玻璃水泵", "皮带", "张紧轮", "保险丝盒"],
}
BRANDS = ["启航", "恒驰", "锐联", "德远", "新程", "安途"]
CHANNEL_COUNTS = {
    "经销商": 10,
    "汽修连锁": 5,
    "直营网点": 5,
    "电商": 5,
    "大客户直供": 5,
}
CHANNEL_WEIGHTS = {
    "经销商": 0.45,
    "汽修连锁": 0.18,
    "直营网点": 0.13,
    "电商": 0.12,
    "大客户直供": 0.12,
}
BASE_DISCOUNT = {
    "经销商": 0.080,
    "汽修连锁": 0.065,
    "直营网点": 0.035,
    "电商": 0.055,
    "大客户直供": 0.075,
}
BASE_QUANTITY = {
    "刹车系统": 42,
    "滤清系统": 58,
    "点火系统": 45,
    "悬挂系统": 30,
    "照明系统": 36,
    "雨刮及易损件": 52,
}
SPECIAL_EAST_DEALERS = [
    "华东核心经销商一号",
    "华东核心经销商二号",
    "华东核心经销商三号",
]

MONEY_QUANT = Decimal("0.01")
RATE_QUANT = Decimal("0.0001")


def money(value: Decimal | float | int | str) -> Decimal:
    """Round a value to currency precision deterministically."""
    return Decimal(str(value)).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def rate(value: Decimal | float | int | str) -> Decimal:
    """Round a value to rate precision deterministically."""
    return Decimal(str(value)).quantize(RATE_QUANT, rounding=ROUND_HALF_UP)


def iter_months(start: date, end: date) -> list[tuple[int, int]]:
    months: list[tuple[int, int]] = []
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        months.append((year, month))
        month += 1
        if month == 13:
            year += 1
            month = 1
    return months


def build_dimensions() -> tuple[list[dict[str, Any]], ...]:
    """Build stable region, product, and customer dimensions."""
    regions = [
        {
            "region_id": index,
            "region_name": name,
            "manager_name": REGION_MANAGERS[index - 1],
        }
        for index, name in enumerate(REGION_NAMES, start=1)
    ]

    products: list[dict[str, Any]] = []
    product_id = 1
    for category_index, (category, product_names) in enumerate(
        CATEGORY_PRODUCTS.items(), start=1
    ):
        for item_index, product_name in enumerate(product_names, start=1):
            unit_cost = money(35 + category_index * 18 + item_index * 7.5)
            list_price = money(unit_cost * Decimal("1.48"))
            products.append(
                {
                    "product_id": product_id,
                    "product_name": f"{BRANDS[item_index - 1]}{product_name}",
                    "category": category,
                    "brand": BRANDS[item_index - 1],
                    "unit_cost": unit_cost,
                    "list_price": list_price,
                }
            )
            product_id += 1

    customer_type_by_channel = {
        "经销商": "区域经销",
        "汽修连锁": "连锁维修",
        "直营网点": "直营网点",
        "电商": "线上零售",
        "大客户直供": "企业直供",
    }
    customers: list[dict[str, Any]] = []
    customer_id = 1
    join_base = date(2021, 1, 1)
    for region_id, region_name in enumerate(REGION_NAMES, start=1):
        local_index = 0
        for channel, count in CHANNEL_COUNTS.items():
            for channel_index in range(1, count + 1):
                local_index += 1
                if region_name == "华东" and channel == "经销商" and channel_index <= 3:
                    customer_name = SPECIAL_EAST_DEALERS[channel_index - 1]
                    customer_level = "A"
                else:
                    customer_name = f"{region_name}{channel}客户{channel_index:02d}"
                    customer_level = (
                        "A"
                        if channel_index <= max(1, count // 5)
                        else "B"
                        if channel_index <= max(3, count * 3 // 5)
                        else "C"
                    )
                customers.append(
                    {
                        "customer_id": customer_id,
                        "customer_name": customer_name,
                        "region_id": region_id,
                        "customer_type": customer_type_by_channel[channel],
                        "customer_level": customer_level,
                        "channel": channel,
                        "join_date": join_base
                        + timedelta(days=region_id * 31 + local_index * 17),
                    }
                )
                customer_id += 1
    return regions, products, customers


def _random_date_in_month(rng: random.Random, year: int, month: int) -> date:
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, rng.randint(1, last_day))


def _customer_choice(
    rng: random.Random,
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    channel_counts = Counter(customer["channel"] for customer in candidates)
    weights = []
    for customer in candidates:
        channel = customer["channel"]
        if channel == "经销商" and customer["region_id"] == 1:
            if customer["customer_name"] in SPECIAL_EAST_DEALERS:
                # The three named A-level dealers hold 60% of East-China dealer
                # volume, making their planted decline visible and reproducible.
                customer_weight = CHANNEL_WEIGHTS[channel] * 0.60 / 3
            else:
                customer_weight = CHANNEL_WEIGHTS[channel] * 0.40 / 7
            weights.append(customer_weight)
        else:
            weights.append(CHANNEL_WEIGHTS[channel] / channel_counts[channel])
    return rng.choices(candidates, weights=weights, k=1)[0]


def generate_sales(
    products: list[dict[str, Any]],
    customers: list[dict[str, Any]],
    seed: int = RANDOM_SEED,
    row_count: int = FACT_ROW_COUNT,
) -> list[dict[str, Any]]:
    """Generate balanced sales cells and a controlled 2026 Q2 anomaly."""
    rng = random.Random(seed)
    products_by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    customers_by_region: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for product in products:
        products_by_category[product["category"]].append(product)
    for customer in customers:
        customers_by_region[customer["region_id"]].append(customer)

    cells = [
        (year, month, region_id, category)
        for year, month in iter_months(START_DATE, END_DATE)
        for region_id in range(1, len(REGION_NAMES) + 1)
        for category in CATEGORY_PRODUCTS
    ]
    base_rows, remainder = divmod(row_count, len(cells))
    sales: list[dict[str, Any]] = []
    sale_id = 1

    for cell_index, (year, month, region_id, category) in enumerate(cells):
        rows_in_cell = base_rows + (1 if cell_index < remainder else 0)
        for _ in range(rows_in_cell):
            product = rng.choice(products_by_category[category])
            customer = _customer_choice(rng, customers_by_region[region_id])
            sale_date = _random_date_in_month(rng, year, month)
            base_quantity = BASE_QUANTITY[category]
            quantity = max(1, round(rng.gauss(base_quantity, base_quantity * 0.24)))

            # A modest 2026 growth trend applies everywhere except the planted anomaly.
            demand_factor = Decimal("1.04") if year == 2026 else Decimal("1.00")
            is_current_east_brake = (
                year == 2026
                and month in (4, 5, 6)
                and region_id == 1
                and category == "刹车系统"
            )
            if is_current_east_brake:
                if customer["customer_name"] in SPECIAL_EAST_DEALERS:
                    demand_factor *= Decimal("0.15")
                elif customer["channel"] == "经销商":
                    demand_factor *= Decimal("0.85")
                else:
                    demand_factor *= Decimal("0.93")
            elif (
                year == 2026
                and month in (4, 5, 6)
                and region_id == 2
                and category == "刹车系统"
            ):
                demand_factor *= Decimal("1.10")

            quantity = max(1, round(quantity * float(demand_factor)))
            price_trend = Decimal("1.02") if year == 2026 else Decimal("1.00")
            price_noise = Decimal(str(rng.uniform(0.97, 1.03)))
            unit_price = money(product["list_price"] * price_trend * price_noise)

            discount_value = BASE_DISCOUNT[customer["channel"]] + rng.uniform(
                -0.008, 0.008
            )
            if is_current_east_brake:
                discount_value += 0.04
            discount_rate = rate(max(0.0, discount_value))

            sales_amount = money(
                Decimal(quantity) * unit_price * (Decimal("1") - discount_rate)
            )
            cost_noise = Decimal(str(rng.uniform(0.98, 1.02)))
            cost_amount = money(Decimal(quantity) * product["unit_cost"] * cost_noise)
            gross_profit = money(sales_amount - cost_amount)

            sales.append(
                {
                    "sale_id": sale_id,
                    "sale_date": sale_date,
                    "region_id": region_id,
                    "product_id": product["product_id"],
                    "customer_id": customer["customer_id"],
                    "channel": customer["channel"],
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "discount_rate": discount_rate,
                    "sales_amount": sales_amount,
                    "cost_amount": cost_amount,
                    "gross_profit": gross_profit,
                }
            )
            sale_id += 1

    if sales:
        sales[0]["sale_date"] = START_DATE
        sales[-1]["sale_date"] = END_DATE
    return sales


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest


def write_dataset(output_dir: Path, seed: int, row_count: int) -> dict[str, Any]:
    regions, products, customers = build_dimensions()
    sales = generate_sales(products, customers, seed=seed, row_count=row_count)
    files = {
        "dim_region.csv": (
            ["region_id", "region_name", "manager_name"],
            regions,
        ),
        "dim_product.csv": (
            [
                "product_id",
                "product_name",
                "category",
                "brand",
                "unit_cost",
                "list_price",
            ],
            products,
        ),
        "dim_customer.csv": (
            [
                "customer_id",
                "customer_name",
                "region_id",
                "customer_type",
                "customer_level",
                "channel",
                "join_date",
            ],
            customers,
        ),
        "fact_sales.csv": (
            [
                "sale_id",
                "sale_date",
                "region_id",
                "product_id",
                "customer_id",
                "channel",
                "quantity",
                "unit_price",
                "discount_rate",
                "sales_amount",
                "cost_amount",
                "gross_profit",
            ],
            sales,
        ),
    }
    hashes = {
        file_name: _write_csv(output_dir / file_name, columns, rows)
        for file_name, (columns, rows) in files.items()
    }
    fingerprint_source = "\n".join(
        f"{name}:{hashes[name]}" for name in sorted(hashes)
    ).encode("utf-8")
    return {
        "random_seed": seed,
        "fact_row_count": len(sales),
        "dimension_counts": {
            "regions": len(regions),
            "products": len(products),
            "customers": len(customers),
        },
        "csv_sha256": hashes,
        "dataset_fingerprint": hashlib.sha256(fingerprint_source).hexdigest(),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "raw",
    )
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    parser.add_argument("--rows", type=int, default=FACT_ROW_COUNT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = write_dataset(args.output_dir, args.seed, args.rows)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

# ruff: noqa: E501
"""Build the frozen Week 1 Text-to-SQL semantic dataset from deterministic CSVs.

The generated cases contain business definitions and verified result sets, never
model output.  Re-running this builder is allowed only while authoring the dataset;
the committed SHA-256 fingerprints are the evaluation source of truth afterwards.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import duckdb

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "insight_agent" / "data" / "raw"
OUT = Path(__file__).resolve().parent / "dataset"


def _sql(body: str) -> str:
    return " ".join(line.strip() for line in body.strip().splitlines())


CASE_SPECS: list[dict[str, Any]] = [
    {
        "id": "w1-dev-01",
        "split": "dev",
        "question": "2026 年第二季度哪个区域销售额环比下降最多？",
        "tags": ["time", "aggregation"],
        "sql": """SELECT r.region_name, ROUND(SUM(CASE WHEN f.sale_date >= DATE '2026-01-01' AND f.sale_date < DATE '2026-04-01' THEN f.sales_amount ELSE 0 END),2) q1_sales, ROUND(SUM(CASE WHEN f.sale_date >= DATE '2026-04-01' AND f.sale_date < DATE '2026-07-01' THEN f.sales_amount ELSE 0 END),2) q2_sales FROM fact_sales f JOIN dim_region r ON r.region_id=f.region_id GROUP BY r.region_name ORDER BY (q2_sales-q1_sales) ASC LIMIT 1""",
    },
    {
        "id": "w1-dev-02",
        "split": "dev",
        "question": "华东 2026 Q2 销售额的环比和同比分别是多少？",
        "tags": ["time", "fact_completeness"],
        "sql": """SELECT ROUND(SUM(CASE WHEN f.sale_date>=DATE '2026-04-01' AND f.sale_date<DATE '2026-07-01' THEN f.sales_amount ELSE 0 END),2) q2_2026_sales, ROUND(SUM(CASE WHEN f.sale_date>=DATE '2026-01-01' AND f.sale_date<DATE '2026-04-01' THEN f.sales_amount ELSE 0 END),2) q1_2026_sales, ROUND(SUM(CASE WHEN f.sale_date>=DATE '2025-04-01' AND f.sale_date<DATE '2025-07-01' THEN f.sales_amount ELSE 0 END),2) q2_2025_sales FROM fact_sales f JOIN dim_region r ON r.region_id=f.region_id WHERE r.region_name='华东'""",
    },
    {
        "id": "w1-dev-03",
        "split": "dev",
        "question": "华东 2026 Q2 哪个汽车配件品类销售额环比下降最多？",
        "tags": ["join", "time", "top_n"],
        "sql": """SELECT p.category, ROUND(SUM(CASE WHEN f.sale_date>=DATE '2026-01-01' AND f.sale_date<DATE '2026-04-01' THEN f.sales_amount ELSE 0 END),2) q1_sales, ROUND(SUM(CASE WHEN f.sale_date>=DATE '2026-04-01' AND f.sale_date<DATE '2026-07-01' THEN f.sales_amount ELSE 0 END),2) q2_sales FROM fact_sales f JOIN dim_region r ON r.region_id=f.region_id JOIN dim_product p ON p.product_id=f.product_id WHERE r.region_name='华东' GROUP BY p.category ORDER BY (q2_sales-q1_sales) ASC LIMIT 1""",
    },
    {
        "id": "w1-dev-04",
        "split": "dev",
        "question": "华东刹车系统 2026 Q2 各渠道销售额相比 Q1 如何变化？",
        "tags": ["join", "time", "grouping"],
        "sql": """SELECT f.channel, ROUND(SUM(CASE WHEN f.sale_date>=DATE '2026-01-01' AND f.sale_date<DATE '2026-04-01' THEN f.sales_amount ELSE 0 END),2) q1_sales, ROUND(SUM(CASE WHEN f.sale_date>=DATE '2026-04-01' AND f.sale_date<DATE '2026-07-01' THEN f.sales_amount ELSE 0 END),2) q2_sales FROM fact_sales f JOIN dim_region r ON r.region_id=f.region_id JOIN dim_product p ON p.product_id=f.product_id WHERE r.region_name='华东' AND p.category='刹车系统' GROUP BY f.channel ORDER BY (q2_sales-q1_sales)""",
    },
    {
        "id": "w1-dev-05",
        "split": "dev",
        "question": "哪三个客户对华东刹车系统 2026 Q2 相比 Q1 的销售额下降贡献最大？",
        "tags": ["join", "contribution", "top_n"],
        "sql": """SELECT c.customer_name, c.customer_level, f.channel, ROUND(SUM(CASE WHEN f.sale_date>=DATE '2026-01-01' AND f.sale_date<DATE '2026-04-01' THEN f.sales_amount ELSE 0 END)-SUM(CASE WHEN f.sale_date>=DATE '2026-04-01' AND f.sale_date<DATE '2026-07-01' THEN f.sales_amount ELSE 0 END),2) decline_amount FROM fact_sales f JOIN dim_region r ON r.region_id=f.region_id JOIN dim_product p ON p.product_id=f.product_id JOIN dim_customer c ON c.customer_id=f.customer_id WHERE r.region_name='华东' AND p.category='刹车系统' GROUP BY c.customer_name,c.customer_level,f.channel HAVING SUM(CASE WHEN f.sale_date>=DATE '2026-01-01' AND f.sale_date<DATE '2026-04-01' THEN f.sales_amount ELSE 0 END)>SUM(CASE WHEN f.sale_date>=DATE '2026-04-01' AND f.sale_date<DATE '2026-07-01' THEN f.sales_amount ELSE 0 END) ORDER BY decline_amount DESC LIMIT 3""",
    },
    {
        "id": "w1-dev-06",
        "split": "dev",
        "question": "华东和华南刹车系统 2026 Q2 的销售额环比表现有何不同？",
        "tags": ["join", "time", "multi_dimension"],
        "sql": """SELECT r.region_name, ROUND(SUM(CASE WHEN f.sale_date>=DATE '2026-01-01' AND f.sale_date<DATE '2026-04-01' THEN f.sales_amount ELSE 0 END),2) q1_sales, ROUND(SUM(CASE WHEN f.sale_date>=DATE '2026-04-01' AND f.sale_date<DATE '2026-07-01' THEN f.sales_amount ELSE 0 END),2) q2_sales FROM fact_sales f JOIN dim_region r ON r.region_id=f.region_id JOIN dim_product p ON p.product_id=f.product_id WHERE r.region_name IN ('华东','华南') AND p.category='刹车系统' GROUP BY r.region_name ORDER BY r.region_name""",
    },
    {
        "id": "w1-dev-07",
        "split": "dev",
        "question": "华东刹车系统 2026 Q1 和 Q2 的加权毛利率分别是多少，变化多少个百分点？",
        "tags": ["weighted_margin", "fact_completeness"],
        "sql": """SELECT ROUND(100*SUM(CASE WHEN f.sale_date>=DATE '2026-01-01' AND f.sale_date<DATE '2026-04-01' THEN f.gross_profit ELSE 0 END)/NULLIF(SUM(CASE WHEN f.sale_date>=DATE '2026-01-01' AND f.sale_date<DATE '2026-04-01' THEN f.sales_amount ELSE 0 END),0),4) q1_margin_pct, ROUND(100*SUM(CASE WHEN f.sale_date>=DATE '2026-04-01' AND f.sale_date<DATE '2026-07-01' THEN f.gross_profit ELSE 0 END)/NULLIF(SUM(CASE WHEN f.sale_date>=DATE '2026-04-01' AND f.sale_date<DATE '2026-07-01' THEN f.sales_amount ELSE 0 END),0),4) q2_margin_pct FROM fact_sales f JOIN dim_region r ON r.region_id=f.region_id JOIN dim_product p ON p.product_id=f.product_id WHERE r.region_name='华东' AND p.category='刹车系统'""",
    },
    {
        "id": "w1-dev-08",
        "split": "dev",
        "question": "列出华东 2026 Q2 相比 Q1 销售额逆势增长最多的 5 个产品。",
        "tags": ["join", "top_n", "time"],
        "sql": """SELECT p.product_name, ROUND(SUM(CASE WHEN f.sale_date>=DATE '2026-04-01' AND f.sale_date<DATE '2026-07-01' THEN f.sales_amount ELSE 0 END)-SUM(CASE WHEN f.sale_date>=DATE '2026-01-01' AND f.sale_date<DATE '2026-04-01' THEN f.sales_amount ELSE 0 END),2) growth_amount FROM fact_sales f JOIN dim_region r ON r.region_id=f.region_id JOIN dim_product p ON p.product_id=f.product_id WHERE r.region_name='华东' GROUP BY p.product_name HAVING SUM(CASE WHEN f.sale_date>=DATE '2026-04-01' AND f.sale_date<DATE '2026-07-01' THEN f.sales_amount ELSE 0 END)>SUM(CASE WHEN f.sale_date>=DATE '2026-01-01' AND f.sale_date<DATE '2026-04-01' THEN f.sales_amount ELSE 0 END) ORDER BY growth_amount DESC,p.product_name LIMIT 5""",
    },
    {
        "id": "w1-dev-09",
        "split": "dev",
        "question": "2026 年 1 月到 6 月全公司每月销售额是多少？",
        "tags": ["time", "aggregation"],
        "sql": """SELECT TO_CHAR(DATE_TRUNC('month',f.sale_date),'YYYY-MM') sales_month, ROUND(SUM(f.sales_amount),2) sales_amount FROM fact_sales f WHERE f.sale_date>=DATE '2026-01-01' AND f.sale_date<DATE '2026-07-01' GROUP BY 1 ORDER BY 1""",
    },
    {
        "id": "w1-dev-10",
        "split": "dev",
        "question": "华东刹车系统经销商渠道 2026 年 1 月到 6 月每月销售额是多少？",
        "tags": ["scope_retention", "time", "join"],
        "sql": """SELECT TO_CHAR(DATE_TRUNC('month',f.sale_date),'YYYY-MM') sales_month, ROUND(SUM(f.sales_amount),2) sales_amount FROM fact_sales f JOIN dim_region r ON r.region_id=f.region_id JOIN dim_product p ON p.product_id=f.product_id WHERE r.region_name='华东' AND p.category='刹车系统' AND f.channel='经销商' AND f.sale_date>=DATE '2026-01-01' AND f.sale_date<DATE '2026-07-01' GROUP BY 1 ORDER BY 1""",
    },
    {
        "id": "w1-dev-11",
        "split": "dev",
        "question": "华东 2026 Q2 销量最高的品类是哪一个？注意查询销量而不是销售额。",
        "tags": ["sales_vs_quantity", "join"],
        "sql": """SELECT p.category, SUM(f.quantity) sales_quantity FROM fact_sales f JOIN dim_region r ON r.region_id=f.region_id JOIN dim_product p ON p.product_id=f.product_id WHERE r.region_name='华东' AND f.sale_date>=DATE '2026-04-01' AND f.sale_date<DATE '2026-07-01' GROUP BY p.category ORDER BY sales_quantity DESC,p.category LIMIT 1""",
    },
    {
        "id": "w1-dev-12",
        "split": "dev",
        "question": "华东 2026 Q2 哪个品类的销售明细加权平均折扣率最高？",
        "tags": ["weighted_average", "join"],
        "sql": """SELECT p.category, ROUND(100*SUM(f.sales_amount*f.discount_rate)/NULLIF(SUM(f.sales_amount),0),4) weighted_discount_pct FROM fact_sales f JOIN dim_region r ON r.region_id=f.region_id JOIN dim_product p ON p.product_id=f.product_id WHERE r.region_name='华东' AND f.sale_date>=DATE '2026-04-01' AND f.sale_date<DATE '2026-07-01' GROUP BY p.category ORDER BY weighted_discount_pct DESC,p.category LIMIT 1""",
    },
    {
        "id": "w1-dev-13",
        "split": "dev",
        "question": "2026 Q2 各交易区域有多少家活跃经销商？",
        "tags": ["distinct", "transaction_region"],
        "sql": """SELECT r.region_name, COUNT(DISTINCT f.customer_id) active_dealers FROM fact_sales f JOIN dim_region r ON r.region_id=f.region_id WHERE f.channel='经销商' AND f.sale_date>=DATE '2026-04-01' AND f.sale_date<DATE '2026-07-01' GROUP BY r.region_name ORDER BY r.region_name""",
    },
    {
        "id": "w1-dev-14",
        "split": "dev",
        "question": "华东 2026 Q2 刹车系统的销售额和销量分别是多少？",
        "tags": ["sales_vs_quantity", "fact_completeness"],
        "sql": """SELECT ROUND(SUM(f.sales_amount),2) sales_amount, SUM(f.quantity) sales_quantity FROM fact_sales f JOIN dim_region r ON r.region_id=f.region_id JOIN dim_product p ON p.product_id=f.product_id WHERE r.region_name='华东' AND p.category='刹车系统' AND f.sale_date>=DATE '2026-04-01' AND f.sale_date<DATE '2026-07-01'""",
    },
    {
        "id": "w1-dev-15",
        "split": "dev",
        "question": "华东 2026 Q2 销售额最高的 3 个产品是什么？",
        "tags": ["top_n", "join"],
        "sql": """SELECT p.product_name, ROUND(SUM(f.sales_amount),2) sales_amount FROM fact_sales f JOIN dim_region r ON r.region_id=f.region_id JOIN dim_product p ON p.product_id=f.product_id WHERE r.region_name='华东' AND f.sale_date>=DATE '2026-04-01' AND f.sale_date<DATE '2026-07-01' GROUP BY p.product_name ORDER BY sales_amount DESC,p.product_name LIMIT 3""",
    },
    {
        "id": "w1-dev-16",
        "split": "dev",
        "question": "按交易发生区域统计 2026 Q2 销售额，列出前 3 名。",
        "tags": ["transaction_region", "top_n"],
        "sql": """SELECT r.region_name, ROUND(SUM(f.sales_amount),2) sales_amount FROM fact_sales f JOIN dim_region r ON r.region_id=f.region_id WHERE f.sale_date>=DATE '2026-04-01' AND f.sale_date<DATE '2026-07-01' GROUP BY r.region_name ORDER BY sales_amount DESC,r.region_name LIMIT 3""",
    },
    {
        "id": "w1-dev-17",
        "split": "dev",
        "question": "2027 Q1 华东销售额是多少？",
        "tags": ["no_data", "time"],
        "sql": """SELECT ROUND(SUM(f.sales_amount),2) sales_amount FROM fact_sales f JOIN dim_region r ON r.region_id=f.region_id WHERE r.region_name='华东' AND f.sale_date>=DATE '2027-01-01' AND f.sale_date<DATE '2027-04-01'""",
    },
    {
        "id": "w1-dev-18",
        "split": "dev",
        "question": "2026 Q2 全国各渠道销售额是多少？",
        "tags": ["grouping", "aggregation"],
        "sql": """SELECT f.channel, ROUND(SUM(f.sales_amount),2) sales_amount FROM fact_sales f WHERE f.sale_date>=DATE '2026-04-01' AND f.sale_date<DATE '2026-07-01' GROUP BY f.channel ORDER BY sales_amount DESC,f.channel""",
    },
    {
        "id": "w1-test-01",
        "split": "test",
        "question": "华东刹车系统 2026 Q2 相比 Q1，哪个渠道销售额下降最多？该渠道占区域品类整体净下降的比例是多少？",
        "tags": ["contribution", "denominator", "day7_regression"],
        "sql": """WITH channel_sales AS (SELECT f.channel, SUM(CASE WHEN f.sale_date>=DATE '2026-01-01' AND f.sale_date<DATE '2026-04-01' THEN f.sales_amount ELSE 0 END) q1_sales, SUM(CASE WHEN f.sale_date>=DATE '2026-04-01' AND f.sale_date<DATE '2026-07-01' THEN f.sales_amount ELSE 0 END) q2_sales FROM fact_sales f JOIN dim_region r ON r.region_id=f.region_id JOIN dim_product p ON p.product_id=f.product_id WHERE r.region_name='华东' AND p.category='刹车系统' GROUP BY f.channel) SELECT channel, ROUND(q1_sales-q2_sales,2) decline_amount, ROUND(100*(q1_sales-q2_sales)/NULLIF(SUM(q1_sales-q2_sales) OVER (),0),4) contribution_pct FROM channel_sales ORDER BY decline_amount DESC LIMIT 1""",
    },
    {
        "id": "w1-test-02",
        "split": "test",
        "question": "给出华东刹车系统 2026 Q1、Q2 的加权毛利率以及 Q2 环比变化百分点，三个值都要列出。",
        "tags": ["weighted_margin", "fact_completeness", "day7_regression"],
        "sql": """WITH m AS (SELECT 100*SUM(CASE WHEN f.sale_date>=DATE '2026-01-01' AND f.sale_date<DATE '2026-04-01' THEN f.gross_profit ELSE 0 END)/NULLIF(SUM(CASE WHEN f.sale_date>=DATE '2026-01-01' AND f.sale_date<DATE '2026-04-01' THEN f.sales_amount ELSE 0 END),0) q1_margin_pct, 100*SUM(CASE WHEN f.sale_date>=DATE '2026-04-01' AND f.sale_date<DATE '2026-07-01' THEN f.gross_profit ELSE 0 END)/NULLIF(SUM(CASE WHEN f.sale_date>=DATE '2026-04-01' AND f.sale_date<DATE '2026-07-01' THEN f.sales_amount ELSE 0 END),0) q2_margin_pct FROM fact_sales f JOIN dim_region r ON r.region_id=f.region_id JOIN dim_product p ON p.product_id=f.product_id WHERE r.region_name='华东' AND p.category='刹车系统') SELECT ROUND(q1_margin_pct,4) q1_margin_pct,ROUND(q2_margin_pct,4) q2_margin_pct,ROUND(q2_margin_pct-q1_margin_pct,4) change_pp FROM m""",
    },
    {
        "id": "w1-test-03",
        "split": "test",
        "question": "2026 Q2 每个区域购买过刹车系统的不同客户数是多少？",
        "tags": ["join_duplicate", "distinct"],
        "sql": """SELECT r.region_name,COUNT(DISTINCT f.customer_id) customer_count FROM fact_sales f JOIN dim_region r ON r.region_id=f.region_id JOIN dim_product p ON p.product_id=f.product_id WHERE p.category='刹车系统' AND f.sale_date>=DATE '2026-04-01' AND f.sale_date<DATE '2026-07-01' GROUP BY r.region_name ORDER BY r.region_name""",
    },
    {
        "id": "w1-test-04",
        "split": "test",
        "question": "全公司 2026 上半年销售额比 2025 上半年增长了多少？",
        "tags": ["time", "aggregation"],
        "sql": """SELECT ROUND(SUM(CASE WHEN f.sale_date>=DATE '2025-01-01' AND f.sale_date<DATE '2025-07-01' THEN f.sales_amount ELSE 0 END),2) h1_2025_sales,ROUND(SUM(CASE WHEN f.sale_date>=DATE '2026-01-01' AND f.sale_date<DATE '2026-07-01' THEN f.sales_amount ELSE 0 END),2) h1_2026_sales FROM fact_sales f""",
    },
    {
        "id": "w1-test-05",
        "split": "test",
        "question": "2026 Q2 华东不存在品类的销售额是多少？如果没有记录请明确说明无数据。",
        "tags": ["no_data", "null"],
        "sql": """SELECT ROUND(SUM(f.sales_amount),2) sales_amount FROM fact_sales f JOIN dim_region r ON r.region_id=f.region_id JOIN dim_product p ON p.product_id=f.product_id WHERE r.region_name='华东' AND p.category='不存在品类' AND f.sale_date>=DATE '2026-04-01' AND f.sale_date<DATE '2026-07-01'""",
    },
    {
        "id": "w1-test-06",
        "split": "test",
        "question": "华南经销商渠道 2026 Q2 与 Q1 的销售额分别是多少？",
        "tags": ["channel", "time"],
        "sql": """SELECT ROUND(SUM(CASE WHEN f.sale_date>=DATE '2026-01-01' AND f.sale_date<DATE '2026-04-01' THEN f.sales_amount ELSE 0 END),2) q1_sales,ROUND(SUM(CASE WHEN f.sale_date>=DATE '2026-04-01' AND f.sale_date<DATE '2026-07-01' THEN f.sales_amount ELSE 0 END),2) q2_sales FROM fact_sales f JOIN dim_region r ON r.region_id=f.region_id WHERE r.region_name='华南' AND f.channel='经销商'""",
    },
    {
        "id": "w1-test-07",
        "split": "test",
        "question": "西南 2026 年 1 月到 6 月每月销售额是多少？",
        "tags": ["time", "region"],
        "sql": """SELECT TO_CHAR(DATE_TRUNC('month',f.sale_date),'YYYY-MM') sales_month,ROUND(SUM(f.sales_amount),2) sales_amount FROM fact_sales f JOIN dim_region r ON r.region_id=f.region_id WHERE r.region_name='西南' AND f.sale_date>=DATE '2026-01-01' AND f.sale_date<DATE '2026-07-01' GROUP BY 1 ORDER BY 1""",
    },
    {
        "id": "w1-test-08",
        "split": "test",
        "question": "2026 Q2 同比 2025 Q2，哪个品类全国销售额增长率最高？",
        "tags": ["yoy", "top_n"],
        "sql": """SELECT p.category,ROUND(SUM(CASE WHEN f.sale_date>=DATE '2025-04-01' AND f.sale_date<DATE '2025-07-01' THEN f.sales_amount ELSE 0 END),2) q2_2025_sales,ROUND(SUM(CASE WHEN f.sale_date>=DATE '2026-04-01' AND f.sale_date<DATE '2026-07-01' THEN f.sales_amount ELSE 0 END),2) q2_2026_sales FROM fact_sales f JOIN dim_product p ON p.product_id=f.product_id GROUP BY p.category ORDER BY (q2_2026_sales-q2_2025_sales)/NULLIF(q2_2025_sales,0) DESC,p.category LIMIT 1""",
    },
    {
        "id": "w1-challenge-01",
        "split": "challenge",
        "question": "华东最近表现怎么样？",
        "tags": ["ambiguity", "metric", "time"],
        "clarify": ["指标", "时间范围"],
    },
    {
        "id": "w1-challenge-02",
        "split": "challenge",
        "question": "哪个区域最好？",
        "tags": ["ambiguity", "metric", "time"],
        "clarify": ["指标", "时间范围"],
    },
    {
        "id": "w1-challenge-03",
        "split": "challenge",
        "question": "按客户区域比较 2026 Q2 销售额。",
        "tags": ["ambiguity", "region_dimension"],
        "clarify": ["交易发生区域", "客户所属区域"],
    },
    {
        "id": "w1-challenge-04",
        "split": "challenge",
        "question": "近期销售下降最多的品类是什么？",
        "tags": ["ambiguity", "time", "comparison"],
        "clarify": ["时间范围", "比较基准"],
    },
]


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _connect() -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect(":memory:")
    for table in ("dim_region", "dim_product", "dim_customer", "fact_sales"):
        path = (RAW / f"{table}.csv").as_posix().replace("'", "''")
        conn.execute(f"CREATE TABLE {table} AS SELECT * FROM read_csv_auto('{path}')")
    return conn


def build() -> None:
    conn = _connect()
    grouped: dict[str, list[dict[str, Any]]] = {"dev": [], "test": [], "challenge": []}
    for spec in CASE_SPECS:
        case = {
            "id": spec["id"],
            "type": "text_to_sql",
            "question": spec["question"],
            "semantic_tags": spec["tags"],
            "numeric_tolerance": 0.02,
            "grading": "deterministic",
            "requires_clarification": bool(spec.get("clarify")),
            "expected_clarification_terms": spec.get("clarify", []),
        }
        if "sql" in spec:
            gold_sql = _sql(spec["sql"])
            duckdb_sql = gold_sql.replace(
                "TO_CHAR(DATE_TRUNC('month',f.sale_date),'YYYY-MM')",
                "STRFTIME(f.sale_date,'%Y-%m')",
            )
            cursor = conn.execute(duckdb_sql)
            columns = [item[0] for item in cursor.description]
            rows = [[_json_value(value) for value in row] for row in cursor.fetchall()]
            case["gold_sql"] = gold_sql
            case["gold_result"] = {"columns": columns, "rows": rows}
        else:
            case["gold_facts"] = {"behavior": "clarify_before_query"}
        grouped[spec["split"]].append(case)

    counts = {"dev": 18, "test": 8, "challenge": 4}
    for split, expected in counts.items():
        assert len(grouped[split]) == expected
        payload = {
            "dataset_version": "week1-sql-semantic-v1",
            "dataset_status": "frozen-before-model-run",
            "database_fingerprint": "529e9fc1e3d1d8f2dd5ca8721511eb8c0e8f4966b902cb2a041e2677f3aa0ada",
            "split": split,
            "cases": grouped[split],
        }
        path = OUT / f"sql_semantic_{split}.json"
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    build()

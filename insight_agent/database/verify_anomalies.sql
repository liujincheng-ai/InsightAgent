-- check: 1. 2026 Q2 各区域销售额及相对 2026 Q1、2025 Q2 的变化
SELECT
    r.region_name,
    ROUND(SUM(f.sales_amount) FILTER (
        WHERE f.sale_date >= DATE '2026-04-01' AND f.sale_date < DATE '2026-07-01'
    ), 2) AS sales_2026_q2,
    ROUND(SUM(f.sales_amount) FILTER (
        WHERE f.sale_date >= DATE '2026-01-01' AND f.sale_date < DATE '2026-04-01'
    ), 2) AS sales_2026_q1,
    ROUND(100 * (
        SUM(f.sales_amount) FILTER (
            WHERE f.sale_date >= DATE '2026-04-01' AND f.sale_date < DATE '2026-07-01'
        ) / NULLIF(SUM(f.sales_amount) FILTER (
            WHERE f.sale_date >= DATE '2026-01-01' AND f.sale_date < DATE '2026-04-01'
        ), 0) - 1
    ), 2) AS qoq_change_pct,
    ROUND(100 * (
        SUM(f.sales_amount) FILTER (
            WHERE f.sale_date >= DATE '2026-04-01' AND f.sale_date < DATE '2026-07-01'
        ) / NULLIF(SUM(f.sales_amount) FILTER (
            WHERE f.sale_date >= DATE '2025-04-01' AND f.sale_date < DATE '2025-07-01'
        ), 0) - 1
    ), 2) AS yoy_change_pct
FROM fact_sales f
JOIN dim_region r USING (region_id)
GROUP BY r.region_name
ORDER BY qoq_change_pct;

-- check: 2. 华东各产品类别销售变化
SELECT
    p.category,
    ROUND(SUM(f.sales_amount) FILTER (
        WHERE f.sale_date >= DATE '2026-04-01' AND f.sale_date < DATE '2026-07-01'
    ), 2) AS sales_2026_q2,
    ROUND(100 * (
        SUM(f.sales_amount) FILTER (
            WHERE f.sale_date >= DATE '2026-04-01' AND f.sale_date < DATE '2026-07-01'
        ) / NULLIF(SUM(f.sales_amount) FILTER (
            WHERE f.sale_date >= DATE '2026-01-01' AND f.sale_date < DATE '2026-04-01'
        ), 0) - 1
    ), 2) AS qoq_change_pct,
    ROUND(100 * (
        SUM(f.sales_amount) FILTER (
            WHERE f.sale_date >= DATE '2026-04-01' AND f.sale_date < DATE '2026-07-01'
        ) / NULLIF(SUM(f.sales_amount) FILTER (
            WHERE f.sale_date >= DATE '2025-04-01' AND f.sale_date < DATE '2025-07-01'
        ), 0) - 1
    ), 2) AS yoy_change_pct
FROM fact_sales f
JOIN dim_region r USING (region_id)
JOIN dim_product p USING (product_id)
WHERE r.region_name = '华东'
GROUP BY p.category
ORDER BY qoq_change_pct;

-- check: 3. 华东刹车系统各渠道变化及环比下降贡献
WITH channel_sales AS (
    SELECT
        f.channel,
        SUM(f.sales_amount) FILTER (
            WHERE f.sale_date >= DATE '2026-04-01' AND f.sale_date < DATE '2026-07-01'
        ) AS current_sales,
        SUM(f.sales_amount) FILTER (
            WHERE f.sale_date >= DATE '2026-01-01' AND f.sale_date < DATE '2026-04-01'
        ) AS baseline_sales
    FROM fact_sales f
    JOIN dim_region r USING (region_id)
    JOIN dim_product p USING (product_id)
    WHERE r.region_name = '华东' AND p.category = '刹车系统'
    GROUP BY f.channel
), totals AS (
    SELECT SUM(baseline_sales - current_sales) AS total_decline FROM channel_sales
)
SELECT
    channel,
    ROUND(baseline_sales, 2) AS sales_2026_q1,
    ROUND(current_sales, 2) AS sales_2026_q2,
    ROUND(100 * (current_sales / NULLIF(baseline_sales, 0) - 1), 2) AS qoq_change_pct,
    ROUND(100 * (baseline_sales - current_sales) / NULLIF(total_decline, 0), 2)
        AS decline_contribution_pct
FROM channel_sales CROSS JOIN totals
ORDER BY decline_contribution_pct DESC;

-- check: 4. 华东刹车系统客户采购变化
WITH customer_sales AS (
    SELECT
        c.customer_name,
        c.customer_level,
        c.channel,
        COALESCE(SUM(f.sales_amount) FILTER (
            WHERE f.sale_date >= DATE '2026-04-01' AND f.sale_date < DATE '2026-07-01'
        ), 0) AS current_sales,
        COALESCE(SUM(f.sales_amount) FILTER (
            WHERE f.sale_date >= DATE '2026-01-01' AND f.sale_date < DATE '2026-04-01'
        ), 0) AS baseline_sales
    FROM fact_sales f
    JOIN dim_region r USING (region_id)
    JOIN dim_product p USING (product_id)
    JOIN dim_customer c USING (customer_id)
    WHERE r.region_name = '华东' AND p.category = '刹车系统'
    GROUP BY c.customer_name, c.customer_level, c.channel
)
SELECT
    customer_name,
    customer_level,
    channel,
    ROUND(baseline_sales, 2) AS sales_2026_q1,
    ROUND(current_sales, 2) AS sales_2026_q2,
    ROUND(baseline_sales - current_sales, 2) AS decline_amount,
    ROUND(100 * (current_sales / NULLIF(baseline_sales, 0) - 1), 2) AS qoq_change_pct
FROM customer_sales
ORDER BY decline_amount DESC
LIMIT 10;

-- check: 5. 华东与华南刹车系统对比
SELECT
    r.region_name,
    ROUND(100 * (
        SUM(f.sales_amount) FILTER (
            WHERE f.sale_date >= DATE '2026-04-01' AND f.sale_date < DATE '2026-07-01'
        ) / NULLIF(SUM(f.sales_amount) FILTER (
            WHERE f.sale_date >= DATE '2026-01-01' AND f.sale_date < DATE '2026-04-01'
        ), 0) - 1
    ), 2) AS qoq_change_pct,
    ROUND(100 * (
        SUM(f.sales_amount) FILTER (
            WHERE f.sale_date >= DATE '2026-04-01' AND f.sale_date < DATE '2026-07-01'
        ) / NULLIF(SUM(f.sales_amount) FILTER (
            WHERE f.sale_date >= DATE '2025-04-01' AND f.sale_date < DATE '2025-07-01'
        ), 0) - 1
    ), 2) AS yoy_change_pct
FROM fact_sales f
JOIN dim_region r USING (region_id)
JOIN dim_product p USING (product_id)
WHERE r.region_name IN ('华东', '华南') AND p.category = '刹车系统'
GROUP BY r.region_name
ORDER BY r.region_name;

-- check: 6. 华东刹车系统毛利率与平均折扣变化
SELECT
    period,
    ROUND(100 * SUM(gross_profit) / NULLIF(SUM(sales_amount), 0), 2)
        AS gross_margin_pct,
    ROUND(100 * AVG(discount_rate), 2) AS average_discount_pct
FROM (
    SELECT
        CASE
            WHEN f.sale_date >= DATE '2026-04-01' AND f.sale_date < DATE '2026-07-01'
                THEN '2026Q2'
            WHEN f.sale_date >= DATE '2026-01-01' AND f.sale_date < DATE '2026-04-01'
                THEN '2026Q1'
            WHEN f.sale_date >= DATE '2025-04-01' AND f.sale_date < DATE '2025-07-01'
                THEN '2025Q2'
        END AS period,
        f.gross_profit,
        f.sales_amount,
        f.discount_rate
    FROM fact_sales f
    JOIN dim_region r USING (region_id)
    JOIN dim_product p USING (product_id)
    WHERE r.region_name = '华东'
      AND p.category = '刹车系统'
      AND (
          f.sale_date >= DATE '2026-01-01' AND f.sale_date < DATE '2026-07-01'
          OR f.sale_date >= DATE '2025-04-01' AND f.sale_date < DATE '2025-07-01'
      )
) periods
GROUP BY period
ORDER BY period;

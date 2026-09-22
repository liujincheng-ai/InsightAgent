BEGIN;

CREATE OR REPLACE VIEW insight_quarterly_sales AS
SELECT
    EXTRACT(YEAR FROM f.sale_date)::INTEGER AS sales_year,
    EXTRACT(QUARTER FROM f.sale_date)::INTEGER AS sales_quarter,
    r.region_name,
    p.category,
    f.channel,
    SUM(f.quantity)::BIGINT AS sales_quantity,
    ROUND(SUM(f.sales_amount), 2) AS sales_amount,
    ROUND(SUM(f.gross_profit), 2) AS gross_profit,
    ROUND(
        100 * SUM(f.gross_profit) / NULLIF(SUM(f.sales_amount), 0),
        4
    ) AS gross_margin_pct
FROM fact_sales f
JOIN dim_region r ON r.region_id = f.region_id
JOIN dim_product p ON p.product_id = f.product_id
GROUP BY 1, 2, 3, 4, 5;

COMMENT ON VIEW insight_quarterly_sales IS
'只读季度经营语义视图；区域为交易发生区域，毛利率为总毛利/总销售额';

CREATE OR REPLACE VIEW insight_quarterly_customer_sales AS
SELECT
    EXTRACT(YEAR FROM f.sale_date)::INTEGER AS sales_year,
    EXTRACT(QUARTER FROM f.sale_date)::INTEGER AS sales_quarter,
    r.region_name,
    p.category,
    f.channel,
    c.customer_id,
    c.customer_name,
    c.customer_level,
    ROUND(SUM(f.sales_amount), 2) AS sales_amount
FROM fact_sales f
JOIN dim_region r ON r.region_id = f.region_id
JOIN dim_product p ON p.product_id = f.product_id
JOIN dim_customer c ON c.customer_id = f.customer_id
GROUP BY 1, 2, 3, 4, 5, 6, 7, 8;

COMMENT ON VIEW insight_quarterly_customer_sales IS
'只读季度客户销售语义视图；用于客户跨期比较，禁止把风险预警表述为确认流失';

COMMIT;

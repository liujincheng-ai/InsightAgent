BEGIN;

-- A full Day 1 initialization intentionally rebuilds only these four tables.
-- Week 1 semantic views depend on the tables and are recreated by views.sql.
DROP VIEW IF EXISTS insight_quarterly_customer_sales;
DROP VIEW IF EXISTS insight_quarterly_sales;
DROP TABLE IF EXISTS fact_sales;
DROP TABLE IF EXISTS dim_customer;
DROP TABLE IF EXISTS dim_product;
DROP TABLE IF EXISTS dim_region;

CREATE TABLE dim_region (
    region_id SMALLINT PRIMARY KEY,
    region_name VARCHAR(20) NOT NULL UNIQUE,
    manager_name VARCHAR(50) NOT NULL
);

COMMENT ON TABLE dim_region IS '汽车配件销售区域维度表';
COMMENT ON COLUMN dim_region.region_id IS '区域主键';
COMMENT ON COLUMN dim_region.region_name IS '区域名称';
COMMENT ON COLUMN dim_region.manager_name IS '区域负责人（合成人名）';

CREATE TABLE dim_product (
    product_id INTEGER PRIMARY KEY,
    product_name VARCHAR(100) NOT NULL UNIQUE,
    category VARCHAR(30) NOT NULL,
    brand VARCHAR(50) NOT NULL,
    unit_cost NUMERIC(12, 2) NOT NULL CHECK (unit_cost > 0),
    list_price NUMERIC(12, 2) NOT NULL CHECK (list_price > unit_cost)
);

COMMENT ON TABLE dim_product IS '汽车配件产品与品类维度表';
COMMENT ON COLUMN dim_product.product_id IS '产品主键';
COMMENT ON COLUMN dim_product.product_name IS '合成产品名称';
COMMENT ON COLUMN dim_product.category IS '产品类别';
COMMENT ON COLUMN dim_product.brand IS '合成品牌';
COMMENT ON COLUMN dim_product.unit_cost IS '标准单位成本，人民币元';
COMMENT ON COLUMN dim_product.list_price IS '目录单价，人民币元';

CREATE TABLE dim_customer (
    customer_id INTEGER PRIMARY KEY,
    customer_name VARCHAR(100) NOT NULL UNIQUE,
    region_id SMALLINT NOT NULL REFERENCES dim_region(region_id),
    customer_type VARCHAR(30) NOT NULL,
    customer_level CHAR(1) NOT NULL CHECK (customer_level IN ('A', 'B', 'C')),
    channel VARCHAR(30) NOT NULL CHECK (
        channel IN ('经销商', '汽修连锁', '直营网点', '电商', '大客户直供')
    ),
    join_date DATE NOT NULL
);

COMMENT ON TABLE dim_customer IS '汽车配件客户、渠道与等级维度表';
COMMENT ON COLUMN dim_customer.customer_id IS '客户主键';
COMMENT ON COLUMN dim_customer.customer_name IS '合成客户名称';
COMMENT ON COLUMN dim_customer.region_id IS '所属销售区域';
COMMENT ON COLUMN dim_customer.customer_type IS '客户业务类型';
COMMENT ON COLUMN dim_customer.customer_level IS '客户等级：A、B、C';
COMMENT ON COLUMN dim_customer.channel IS '销售渠道';
COMMENT ON COLUMN dim_customer.join_date IS '成为客户的日期';

CREATE TABLE fact_sales (
    sale_id BIGINT PRIMARY KEY,
    sale_date DATE NOT NULL,
    region_id SMALLINT NOT NULL REFERENCES dim_region(region_id),
    product_id INTEGER NOT NULL REFERENCES dim_product(product_id),
    customer_id INTEGER NOT NULL REFERENCES dim_customer(customer_id),
    channel VARCHAR(30) NOT NULL CHECK (
        channel IN ('经销商', '汽修连锁', '直营网点', '电商', '大客户直供')
    ),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(12, 2) NOT NULL CHECK (unit_price > 0),
    discount_rate NUMERIC(7, 4) NOT NULL CHECK (
        discount_rate >= 0 AND discount_rate < 0.8
    ),
    sales_amount NUMERIC(14, 2) NOT NULL CHECK (sales_amount >= 0),
    cost_amount NUMERIC(14, 2) NOT NULL CHECK (cost_amount >= 0),
    gross_profit NUMERIC(14, 2) NOT NULL,
    CONSTRAINT ck_fact_sales_amount_formula CHECK (
        ABS(
            sales_amount
            - ROUND(quantity * unit_price * (1 - discount_rate), 2)
        ) <= 0.01
    ),
    CONSTRAINT ck_fact_gross_profit_formula CHECK (
        ABS(gross_profit - (sales_amount - cost_amount)) <= 0.01
    )
);

COMMENT ON TABLE fact_sales IS '汽车配件销售事实表，全部数据均为确定性合成数据';
COMMENT ON COLUMN fact_sales.sale_id IS '销售明细主键';
COMMENT ON COLUMN fact_sales.sale_date IS '销售日期';
COMMENT ON COLUMN fact_sales.region_id IS '销售区域';
COMMENT ON COLUMN fact_sales.product_id IS '销售产品';
COMMENT ON COLUMN fact_sales.customer_id IS '采购客户';
COMMENT ON COLUMN fact_sales.channel IS '销售渠道，与客户维度保持一致';
COMMENT ON COLUMN fact_sales.quantity IS '销售数量';
COMMENT ON COLUMN fact_sales.unit_price IS '未折扣成交单价，人民币元';
COMMENT ON COLUMN fact_sales.discount_rate IS '折扣率，0.1000 表示 10%';
COMMENT ON COLUMN fact_sales.sales_amount IS '销售额 = 数量 × 单价 × (1 - 折扣率)';
COMMENT ON COLUMN fact_sales.cost_amount IS '销售成本，人民币元';
COMMENT ON COLUMN fact_sales.gross_profit IS '毛利 = 销售额 - 销售成本';

CREATE INDEX idx_fact_sales_date ON fact_sales(sale_date);
CREATE INDEX idx_fact_sales_region_date ON fact_sales(region_id, sale_date);
CREATE INDEX idx_fact_sales_product_date ON fact_sales(product_id, sale_date);
CREATE INDEX idx_fact_sales_customer_date ON fact_sales(customer_id, sale_date);
CREATE INDEX idx_dim_product_category ON dim_product(category);
CREATE INDEX idx_dim_customer_region_channel
    ON dim_customer(region_id, channel);

COMMIT;

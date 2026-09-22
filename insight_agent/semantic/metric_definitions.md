# InsightAgent 业务指标定义

本文件是 `business_glossary.yaml` 的人工审阅版。机器运行以 YAML 为准；两者都只
定义口径，不保存 Benchmark 答案。

| 指标 | 定义 | SQL 核心口径 | 单位 |
|---|---|---|---|
| 销售额 | 成交后的销售收入 | `SUM(sales_amount)` | 元 |
| 销量 | 售出件数 | `SUM(quantity)` | 件 |
| 加权毛利率 | 总毛利 / 总销售额 | `SUM(gross_profit)/NULLIF(SUM(sales_amount),0)` | % |
| 环比 | 当前周期相对紧邻上一周期 | `(current-previous)/previous` | % |
| 同比 | 当前周期相对上年相同周期 | `(current-prior_year)/prior_year` | % |
| 下降贡献率 | 分项下降 / 查询范围整体净下降 | `component_decline/net_decline` | % |

口径边界：比例分母为零时返回 NULL 并说明无法计算；毛利率跨期变化使用百分点；
销售额已含折扣，不得再次扣减；下降贡献率允许增长分项呈负贡献。

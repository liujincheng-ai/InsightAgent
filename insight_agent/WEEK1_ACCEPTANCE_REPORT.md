# Week 1 Text-to-SQL 语义正确性验收报告

## 1. 验收结论

结论：**通过，带三项已知限制**。

Week 1 已完成业务语义层、语义视图、歧义门禁、通用语义预检、冻结评测集和真实 API 评测。唯一一次 DeepSeek V4 Pro 全量最终运行通过 **27/30（90%）**；SQL 执行成功率、歧义处理准确率和澄清前不查库率均为 **100%**；Day 7 两个失败回归题为 **2/2**。

本结论不等于生产可用，不把 30 题小样本外推为线上准确率，也不隐藏三个失败。

## 2. 验收范围

### 2.1 实现

- YAML 业务词典：指标定义、字段语义、时间边界和高风险歧义。
- 动态语义选择：只注入问题相关内容，支持四种 Profile。
- 两个 PostgreSQL 只读语义视图：交易区域季度聚合、客户所属区域季度聚合。
- SQL 语义预检：区域/品类/渠道范围、Join、时间范围、销售额与销量、加权指标、去重计数和贡献率。
- 歧义门禁：需要澄清时不向 Agent 提供 SQL Tool。
- 确定性呈现：对加权毛利率、渠道净下降贡献和无数据场景优先绑定 Observation。

### 2.2 数据集

| Split | 数量 | SHA-256 |
|---|---:|---|
| dev | 18 | `a912a70918cfcd838f77903895ca3dcc93bd29f09e099768edd3102fc5a23728` |
| test | 8 | `2d35eedb8000de6cb073bd23d91d7e6de70cf300fba5061a7509910c5f7cd647` |
| challenge | 4 | `562ad043ad7bb0c8550b189de56d5e13fddb94a9fd8dc162738e61da7dc49b4d` |

Gold 结果由时间范围为 2025-01-01 至 2026-06-30、固定随机种子 `20260904` 的 CSV 数据通过 DuckDB 确定性生成。PostgreSQL 语义视图另以 `insight_readonly` 角色完成真实只读抽查；不把该抽查描述成 30 条 Gold SQL 全量 PostgreSQL 复验。

覆盖项包括时间边界、同比/环比、Join、重复计数、交易区域/客户区域、销售额/销量、加权毛利率、加权折扣、净下降贡献、空值/无数据以及四类高风险歧义。

## 3. 评分口径

| 指标 | 定义 |
|---|---|
| SQL 执行成功率 | 非歧义题是否获得成功 SQL Observation |
| 严格结果集准确率 | 任一 Observation 表是否包含 Gold 列和值；允许列顺序变化和数值容差 |
| 答案事实准确率 | 最终答案是否完整包含题目要求的 Gold 事实 |
| 歧义处理准确率 | 是否提出命中预期要点的澄清问题 |
| 澄清前不查库率 | 歧义题是否在澄清前完全未调用 SQL |
| 总通过率 | 非歧义题需运行成功且结果集或证据绑定答案满足语义事实；歧义题需澄清正确且未查库 |

比例值支持 `0.2613` 与 `26.13%` 的单位归一化。严格结果集和答案事实刻意分开报告：SQL 返回额外/不同形状不必然说明用户答案错误，反之 SQL 正确也不保证最终答案完整。

离线重评分只允许改派生 Verdict、`records.json`、`summary.json/csv` 和 Manifest 中的评分信息；模型 `events`、`actual_answer`、`actual_sql` 保持不变。V2 评分器修正了小数比例与百分比等价，并将严格结果集与证据绑定答案拆开。

## 4. 最终运行

运行 ID：`week1-pro-final-combined-20260910-run1`

| 项目 | 值 |
|---|---|
| 模型 | `deepseek-v4-pro` |
| Temperature | `0.0` |
| Profile | `combined` |
| 题数 | 30 |
| 总通过率 | **27/30（90.00%）** |
| SQL 执行成功率 | **100.00%** |
| 严格结果集准确率 | **76.92%** |
| 答案事实准确率 | **88.46%** |
| 歧义处理准确率 | **100.00%** |
| 澄清前不查库率 | **100.00%** |
| 平均延迟 | **6.35 秒/题** |
| Day 7 回归 | **2/2** |

语义标签中：下降贡献 2/2、加权毛利率 2/2、事实完整性 4/4、销售额/销量区分 2/2、Top-N 6/6、歧义 4/4。无数据标签 0/2、加权平均标签 0/1，是下一阶段重点。

## 5. 探索与消融结果

以下运行用于工程探索，不作为严格因果实验。LLM 即使 temperature 0 仍存在路径波动；不同时间运行不能仅凭通过率差异归因于某个 Profile。

满足“相同模型、参数和冻结测试集”的主 Before/After 对照为：Flash、temperature 0、同一组三个数据集指纹，Before `week1-flash-baseline-20260910-run1` 为 **21/30（70%）**，After `week1-flash-final-combined-20260910-run2` 为 **24/30（80%）**，观察提升 **10 个百分点**。变量包含 Week 1 的完整语义实现与 Profile，不能把全部差异单独归因于词典。Run 1 的 26/30 作为路径波动证据，不选择它替代更晚冻结的 Run 2。

| 运行 | Profile | 通过率 | 平均延迟 |
|---|---|---:|---:|
| Flash 旧服务 Before | baseline | 21/30（70.00%） | 4.05 秒 |
| Flash 当前实现对照 | baseline | 23/30（76.67%） | 4.61 秒 |
| Flash Schema/字段说明 | comments | 22/30（73.33%） | 4.46 秒 |
| Flash 业务词典/歧义规则 | glossary | 25/30（83.33%） | 4.01 秒 |
| Flash 首轮组合 | combined | 23/30（76.67%） | 4.75 秒 |
| Flash 最终组合 Run 1 | combined | 26/30（86.67%） | 4.55 秒 |
| Flash 最终组合 Run 2 | combined | 24/30（80.00%） | 4.32 秒 |
| Pro 唯一最终运行 | combined | 27/30（90.00%） | 6.35 秒 |

可确认的工程事实是：组合实现能在真实 API 中做到歧义题先澄清且不查库，两个 Day 7 回归题在 Pro 最终运行中通过。不能确认“glossary 单独必然优于 combined”，因为没有多次随机重复和置信区间。

## 6. 三个最终失败

### 6.1 `w1-dev-12`：加权折扣率答案表达不完整

SQL 正确计算 `SUM(sales_amount * discount_rate) / SUM(sales_amount)`，结果集也正确返回刹车系统和 `0.1041326...`；最终答案只展示原始小数，没有明确写为 **10.41%**。分类为 `answer_fact_completeness`。这说明“有正确表格”仍不等于“用户能直接理解指标单位”。

### 6.2 `w1-dev-17`：超出数据覆盖范围未解释

查询 2027 Q1 时 SQL 用 `COALESCE(SUM(...), 0)` 返回 0，但最终答案没有说明数据只覆盖到 2026-06-30，无法区分“真实销售额为零”和“没有该周期数据”。分类为 `sql_semantic_result`。生产方案应返回数据覆盖元信息，并区分 `0`、`NULL` 与 out-of-range。

### 6.3 `w1-test-05`：虚构品类语义解析错误

问题明确要求“不存在品类”时说明无数据。模型把它理解为 `product_id` 无法关联维表的孤儿记录，首次 SQL 又组合了多条 SELECT，预检正确阻断；后续仍未得到目标品类过滤下的 0 行语义。分类为 `sql_semantic_result`。这同时验证安全门禁有效，但暴露实体不存在解析与无数据合同不足。

## 7. Day 7 回归闭环

- 加权毛利率题：Q1 **28.91%**、Q2 **26.13%**、变化 **-2.78 个百分点**，三个事实完整返回。
- 渠道下降贡献题：经销商下降 **395,312.25 元**，按区域品类整体净下降 **527,845.50 元** 为分母，贡献 **74.89%**。

原 Day 7 的两类问题已由通用语义定义、预检和确定性呈现覆盖，不使用问题文本到固定答案的硬编码映射。

## 8. 工程验收

- 数据集结构、ID 唯一性、Split 数量、指纹、Gold、Profile 和歧义门禁均有自动化测试。
- 多条 SELECT 在执行前被阻断并归类为可纠正语法问题；DML/DDL 和数据库权限错误仍不可重试。
- 结果目录禁止覆盖，每题使用独立会话并保留 SSE 原始事件、SQL、答案、延迟和 Manifest。
- 数据库视图随 Windows 初始化脚本创建并授权给配置的只读角色。
- 交付时 `tests/insight_agent` 共 **155 passed、0 failed**；3 条警告来自上游依赖弃用提示，Ruff 定向检查通过。

## 9. 风险与后续建议

1. 为查询结果增加 `data_min_date/data_max_date` 元信息，建立 `zero/null/out_of_range` 三态合同。
2. 增加实体链接层：先解析已知维度值，不存在实体返回可解释空集，不把自然语言字面值改写成孤儿记录条件。
3. 对百分比、百分点、币种和数量做统一格式化，不依赖模型解释原始小数。
4. 扩展到至少 100 题、多个 Schema 和真实脱敏业务问法；对每个配置执行重复运行并报告均值、方差和置信区间。
5. 在生产化前补齐 RBAC、Document ACL、租户隔离、审计与预算控制。

## 10. 复现命令

```powershell
.\.venv\Scripts\python.exe -m insight_agent.evaluation.build_week1_dataset
.\.venv\Scripts\python.exe -m insight_agent.evaluation.run_semantic_eval --split all --profile combined --model deepseek-v4-pro --temperature 0 --timeout 120 --output-dir insight_agent/evaluation/results/<new-run-id>
.\.venv\Scripts\python.exe -m insight_agent.evaluation.rescore_semantic insight_agent/evaluation/results/<existing-week1-run-id>
```

复现会产生新的模型运行，不应覆盖本报告所指的唯一最终目录。模型服务、数据集指纹、参数或代码状态不同，结果只能作为新实验，不能冒充同一次最终验收。

# InsightAgent Day 5 验收报告

验收日期：2026-09-08
验收结论：**技术验收通过；Git Commit 按用户明确要求豁免**
代码提交：**未创建**

## 1. 验收范围与结论

Day 5 已建立一套可重复运行、失败可追踪、dev/test 隔离的 30 条 InsightAgent V1 Benchmark。评测覆盖 Text-to-SQL、企业制度 RAG、三个领域 Tool 和综合任务，不再以一次 Web UI 演示代替效果证明。

本次完成：

1. 30 条任务均有人工校验的 Gold Truth 和明确判分规则；
2. 在模型运行前拆分为 20 条 dev 和 10 条冻结 test；
3. 一条命令可运行真实 InsightAgent SSE Agent；
4. 保存逐题原始事件、最终答案、Tool、SQL、引用、延迟和失败原因；
5. 完成 Flash dev 调试及 Pro 30 条冻结首轮；
6. 15 条需要判断语义和业务边界的任务完成人工复核并保存理由；
7. 最终回归 101 passed，Ruff 全部通过。

Pro 首轮结果为 **26/30（86.67%）**。冻结 test 为 **10/10**，dev 为 **16/20**。四个失败均保留，未选择性重跑，也未根据失败修改 Gold Truth。

## 2. 数据集构成

| 类型 | dev | test | 合计 | Pro 通过 |
|---|---:|---:|---:|---:|
| Text-to-SQL | 5 | 3 | 8 | 6/8 |
| 企业制度 RAG | 4 | 2 | 6 | 6/6 |
| `sales_diagnosis_tool` | 2 | 1 | 3 | 2/3 |
| `customer_loss_analysis_tool` | 2 | 1 | 3 | 3/3 |
| `dealer_health_analysis_tool` | 2 | 1 | 3 | 3/3 |
| 综合任务 | 5 | 2 | 7 | 6/7 |
| **合计** | **20** | **10** | **30** | **26/30** |

数据文件：

- `evaluation/dataset/v1_dev.json`，SHA-256：`2da1d03b62c4bacff1c1945f2169230526616d776494370a46b5e58edba3c213`；
- `evaluation/dataset/v1_test.json`，SHA-256：`bde8984de7ec74d170fa7640b0e2c70f2a9a09b90eadc24c96d1b85e39b393a2`。

Gold Truth 的来源分为三类：既有 Day 1/Day 4 Gold 文件、六份合成制度原文、真实 PostgreSQL 只读查询。针对 Pro 失败的区域销售题，再次独立查询确认华东 2026Q1/Q2 销售额为 15,727,133.31 / 15,228,822.09 元，环比 -3.1685%、同比 1.8485%，因此没有因模型失败修改 Gold。

## 3. 评测实现

| 文件 | 职责 |
|---|---|
| `evaluation/schemas.py` | 校验必填字段、唯一 ID、20/10 拆分、类型配额和 test 冻结状态 |
| `evaluation/metrics.py` | 判定数值容差、事实、Tool、SQL 成功 Observation、文档、章节及汇总指标 |
| `evaluation/run_eval.py` | 调用真实 SSE API、逐题新会话、超时继续、保存完整轨迹并拒绝覆盖结果 |
| `evaluation/rescore.py` | 判分器修复后从不可变事件重新生成派生分数 |
| `evaluation/apply_manual_reviews.py` | 校验并应用人工复核决定和理由 |
| `tests/insight_agent/test_day5_benchmark.py` | 数据契约、解析、容差、失败保留、资源隔离和结果输出测试 |

资源不是统一挂载，而是按任务隔离：

- Text-to-SQL：仅数据库；
- RAG：仅知识库；
- 三类领域 Tool、综合任务：数据库和知识库。

该隔离是有效评测的必要条件。InsightAgent 会根据资源组合选择不同 Agent 路由；错误挂载会改变被测系统，而不只是增加无关上下文。

## 4. 一条命令运行

```powershell
.\.venv\Scripts\python.exe -m insight_agent.evaluation.run_eval `
  --split all `
  --model deepseek-v4-pro `
  --temperature 0 `
  --timeout 120 `
  --output-dir insight_agent/evaluation/results/<new-run-id>
```

每条任务使用全新的 `conv_uid`。已有非空目录会触发 `FileExistsError`，防止覆盖冻结结果。

## 5. Flash 试跑

共保留三轮独立目录：

| 运行 | 结果 | 发现与处理 |
|---|---:|---|
| `day5-flash-dev-20260908-run1` | 14/20 | 所有题同时挂数据库和知识库，纯 SQL 被综合模式门禁污染 |
| `day5-flash-dev-20260908-run2` | 14/20 | SQL 修复为 5/5，但三类 Tool 只挂数据库，领域 Tool 未注册 |
| `day5-flash-dev-20260908-run3` | **20/20** | 冻结最终资源矩阵；平均延迟 13.322 秒 |

run1、run2 未删除。它们证明评测环境配置也必须版本化，并为面试中的故障分析提供原始案例。

## 6. Pro 冻结首轮指标

运行目录：`evaluation/results/day5-pro-all-20260908-frozen-run1`

| 指标 | 结果 |
|---|---:|
| 总任务通过率 | **26/30，86.67%** |
| SQL Execution Success | **7/8，87.50%** |
| Answer Fact Accuracy | **27/30，90.00%** |
| Expected Tool Call Rate | **14/16，87.50%** |
| RAG Document Hit Rate | **12/13，92.31%** |
| Citation Section Accuracy | **12/13，92.31%** |
| Integrated Task Pass Rate | **6/7，85.71%** |
| 平均延迟 | **15.316 秒** |
| 冻结 test | **10/10，100%** |

Tool 调用指标包含 9 条领域 Tool 任务和 7 条综合任务。RAG 指标包含 6 条纯 RAG 和 7 条综合任务。失败始终保留在分母中。

服务端没有返回可审计的计费 Token，因此 Token 和成本字段保持 `null`，没有用上下文长度或公开价格进行伪精确估算。

## 7. 四个失败及主要原因

| ID | 类型 | 主要原因 | 证据与解释 |
|---|---|---|---|
| `v1-dev-sql-01` | SQL | SQL 生成/执行 | 多次 SQL 被现有预执行校验拒绝，最终未得到成功 Observation；只保存 SQL 文本不能算执行成功 |
| `v1-dev-sql-02` | SQL | 答案事实错误 | SQL 成功执行，但最终把正确 Gold 的 -3.17% / +1.85% 汇总成 -2.79% / +2.25%，属于可执行不等于事实正确 |
| `v1-dev-sales-02` | 销售 Tool | Tool 选择/格式 | 数值最终正确，但实际动作是 `execute_tool`、`load_tools`，未按契约直接调用 `sales_diagnosis_tool` |
| `v1-dev-integrated-03` | 综合任务 | Tool 选择和虚假完成 | 只输出执行计划及“报告已完成”兜底，未真实调用经销商 Tool、未获得制度证据；人工复核失败 |

失败分类汇总：SQL 生成/执行 1、答案事实 1、Tool 选择 2。上述问题属于 Day 6 的 SQL 错误分类、有限重试和 Agent 防虚假完成输入，本日不通过修改 test 或选择性重跑掩盖。

## 8. 自动评分修正与审计性

Pro 首轮后只对派生评分做了两项必要修正：

1. 将 `30 日` 与 `30日` 等中文可读空白归一化，修复一条实际正确 RAG 的误判；
2. SQL 必须存在成功的执行 Observation 才算执行成功；文档未命中时章节不得单独记为命中。

重新评分由 `rescore.py` 从冻结的 `events` 生成。原始事件、答案、Tool、SQL、引用、会话 ID 和延迟均未改变；manifest 保存 `scoring_version`、重新评分时间和原因。

人工复核覆盖 15 条任务，复核理由保存在 `manual_reviews.json`。15 条均有 reviewer、decision 和 reason，不存在只给主观总分而无解释的记录。

## 9. 自动化与质量验收

| 检查项 | 结果 |
|---|---:|
| Day 5 专项测试 | 11 passed |
| InsightAgent 全量专项回归 | **101 passed, 3 warnings** |
| Ruff | **All checks passed** |
| 数据集契约 | **PASS** |
| Pro 原始文件/记录 | **30/30** |
| 人工复核 | **15/15** |

三条 warning 来自现有 pytest-asyncio、Starlette multipart 和 Pydantic 兼容代码，没有 InsightAgent 测试失败。证据见 `evidence/day5/automated-test-results.txt`。

## 10. Day 5 七项验收矩阵

| 主计划验收项 | 结果 | 说明 |
|---|:---:|---|
| 30 条问题均有 Gold Truth | ✅ | 数量与类型配额自动校验 |
| dev/test 已拆分 | ✅ | 20/10，test 未参与 Flash 调试 |
| 一条命令可运行评测 | ✅ | 真实 SSE API；支持 dev/test/all |
| 保存原始轨迹和汇总 | ✅ | 30 份 raw、JSON、CSV、manifest |
| 首轮 Pro 结果已冻结 | ✅ | 独立非覆盖目录；test 首次结果 10/10 |
| 每个失败至少一个主要原因 | ✅ | 四题全部分类，人工失败有具体理由 |
| 完成 Git Commit | ➖ | 用户明确要求“不提交”，因此按范围约束豁免 |

技术交付项为 6/6 全部通过；Git Commit 是经用户批准不执行的流程项，不能写成已完成。本次没有运行 `git commit`。

## 11. 已知边界

- 样本只有 30 条，不宣称统计代表性；test 10/10 也不代表生产准确率 100%。
- Gold 数据和制度全部为合成演示资产。
- 事实匹配以明确字段、容差、Tool/SQL/引用和人工复核组合判定，但仍不是通用语义评测器。
- API 未返回计费 Token，暂不能审计真实成本。
- 当前工作区包含 Day 4 与 Day 5 未提交修改；manifest 记录基准 Commit 和 `git_dirty=true`。
- 并发、长时间稳定性、租户权限和真实业务标签不在 Day 5 范围内。

## 12. 最终结论

Day 5 的目标已经达到：项目具备 30 条固定任务、冻结 test、真实模型运行、原始轨迹、确定性指标、人工评分理由和可复核失败分类。结果不是“全部成功”的包装，而是可解释的 **26/30 Pro 首轮基线**，并为 Day 6 精确指出 SQL 与 Agent 调用格式的四个待修问题。

Git Commit 未执行，完全遵循用户确认时的明确约束。

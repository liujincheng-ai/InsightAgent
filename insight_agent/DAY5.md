# InsightAgent Day 5 Benchmark 使用说明

Day 5 建立了 30 条 InsightAgent V1 固定评测集、可复现运行器、确定性指标和人工复核记录。
数据及制度均为合成演示资产，结果不具有统计代表性。

## 数据集

- `evaluation/dataset/v1_dev.json`：20 条，可用于调试评测器和系统实现。
- `evaluation/dataset/v1_test.json`：10 条，在 Pro 运行前冻结，不用于调参。
- 类型配额：8 条 Text-to-SQL、6 条制度 RAG、三类领域 Tool 各 3 条、7 条综合任务。

资源必须按任务类型隔离：Text-to-SQL 仅挂数据库，RAG 仅挂知识库，三类领域 Tool 与综合任务同时挂数据库和知识库。否则会改变 InsightAgent 的路由模式，产生不可比较的结果。

## 一条命令运行

在仓库根目录执行：

```powershell
.\.venv\Scripts\python.exe -m insight_agent.evaluation.run_eval `
  --split all `
  --model deepseek-v4-pro `
  --temperature 0 `
  --timeout 120 `
  --output-dir insight_agent/evaluation/results/<new-run-id>
```

`--split` 可选 `dev`、`test` 或 `all`。结果目录必须为空或不存在；运行器拒绝覆盖已有结果。

## 输出

每次运行生成：

- `raw/<case-id>.json`：任务定义、完整 SSE 事件、实际答案、Tool、SQL、引用和判分；
- `records.json`：全部逐题记录；
- `summary.json`：总体与分类指标；
- `summary.csv`：便于人工审阅的表格；
- `run_manifest.json`：模型、参数、数据哈希、Git 状态和运行摘要。

API 当前不返回可审计的计费 Token，因此 `token_usage` 和成本保持空值，不做推算。

## 评分与复核

确定性评分检查事实、数值容差、Tool、SQL 成功 Observation、文档和章节。RAG、综合任务及涉及业务边界的任务还必须人工复核，评分理由保存在冻结运行目录的 `manual_reviews.json`。

若只修复判分器而不重新请求模型，可对不可变原始事件重新评分：

```powershell
.\.venv\Scripts\python.exe -m insight_agent.evaluation.rescore <result-dir>
.\.venv\Scripts\python.exe -m insight_agent.evaluation.apply_manual_reviews <result-dir>
```

重新评分只能改变派生判分字段，不能改变原始 SSE `events`、答案、Tool、SQL、引用或延迟；manifest 必须记录重新评分版本和原因。

## 当前冻结结果

- Flash dev 最终试跑：`results/day5-flash-dev-20260908-run3`，20/20。
- Pro 首轮：`results/day5-pro-all-20260908-frozen-run1`，26/30。
- Pro 冻结 test：10/10；dev：16/20。

失败项保留在原始结果中，不选择性重跑。它们分别暴露 SQL 预检/事实汇总、领域 Tool 调用格式和综合流程兜底问题，作为 Day 6 的修复输入。

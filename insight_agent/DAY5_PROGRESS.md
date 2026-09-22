# InsightAgent Day 5 执行进度

开始时间：2026-09-08 +08:00

执行约束：用户已确认执行 Day 5，并明确要求不创建 Git Commit。

状态说明：`⬜ 待执行`、`🔄 执行中`、`✅ 已完成`、`⚠️ 有问题但已处理`、`⛔ 阻塞`。

| 步骤 | 状态 | 内容 | 结果 / 证据 |
|---:|:---:|---|---|
| 1 | ✅ | 建立执行清单并冻结基线 | `feature/insight-agent-v1`；Commit `692e9c9`；保留 Day 4 工作区 |
| 2 | ✅ | 冻结评测 Schema、指标和判分规则 | `evaluation/schemas.py`、`evaluation/metrics.py` |
| 3 | ✅ | 编写并校验 30 条 Gold Truth | 8 SQL、6 RAG、3+3+3 Tool、7 综合任务 |
| 4 | ✅ | 冻结 20 条 dev 与 10 条 test | `evaluation/dataset/v1_dev.json`、`v1_test.json` |
| 5 | ✅ | 实现一条命令运行的评测器 | `evaluation/run_eval.py`；独立会话、超时继续、拒绝覆盖 |
| 6 | ✅ | 补齐自动化测试 | Day 5 11 passed；InsightAgent 全量测试待最终复验 |
| 7 | ✅ | 执行 Flash 试跑 | run1/run2 保留；最终 run3 为 20/20，平均 13.322 秒 |
| 8 | ✅ | 执行 Pro 冻结首轮 | 30 条首轮 26/30；冻结 test 10/10；平均 15.316 秒 |
| 9 | ✅ | 失败分类与技术收口 | 4 个失败均已分类；101 passed；Ruff 全部通过 |
| 10 | ✅ | 最终文档验收 | `DAY5_ACCEPTANCE_REPORT.md`、`DAY5_INTERVIEW_GUIDE_DETAILED.md` |

## 基线保护

- Day 4 的代码、测试、证据和文档仍在当前工作区，属于需要保留的既有成果。
- 本次不清理、不覆盖、不回退 Day 4 修改。
- 本次不创建 Git Commit；最终验收会如实标注该项因用户约束未执行。

## 执行记录

- 2026-09-08：用户确认执行 Day 5，并明确要求不提交。
- 2026-09-08：冻结基线 Commit `692e9c985901ee2d7b50cfaf3fd755dcb1184392`，确认 InsightAgent 5670 与 PostgreSQL 5432 正常，服务端可见 `deepseek-v4-flash`、`deepseek-v4-pro`。
- 2026-09-08：建立 30 条数据集并在模型运行前拆分 dev 20 / test 10；Gold 来自既有 Gold 文件、制度原文和只读数据库复核。
- 2026-09-08：Flash run1 发现所有题同时挂数据库和知识库会污染纯 SQL 路由；原结果保留。
- 2026-09-08：Flash run2 验证纯 SQL 恢复 5/5，但发现领域 Tool 题需要同时挂数据库和知识库；原结果保留。
- 2026-09-08：冻结最终资源矩阵后 Flash run3 达到 20/20，平均延迟 13.322 秒。
- 2026-09-08：Pro 对 30 条任务完成不可覆盖的首轮运行，自动与人工复核后 26/30；test 10/10，dev 16/20。
- 2026-09-08：只读数据库独立复核确认华东 2026Q1/Q2 销售额为 15,727,133.31 / 15,228,822.09，环比 -3.1685%、同比 1.8485%；Pro 两条相关失败不是 Gold 错误。
- 2026-09-08：修正判分器的中文空白归一化、SQL 成功 Observation 判断和“先命中文档再判章节”规则；原始模型事件保持不变，manifest 记录重新评分。
- 2026-09-08：15 条人工判断任务均保存通过/失败理由；最终 4 个失败为 SQL 执行 1、答案事实 1、Tool 选择 2。
- 2026-09-08：最终 InsightAgent 回归 `101 passed, 3 warnings`，Ruff、数据集契约、30 份 raw/records 一致性检查全部通过。
- 2026-09-08：完成最终验收报告与详细面试文档；严格遵循用户要求，未创建 Git Commit。

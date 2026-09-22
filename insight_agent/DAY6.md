# InsightAgent Day 6 使用说明

Day 6 聚焦两类问题：SQL 失败后的安全恢复，以及综合 Agent “有证据才完成”。验收门槛按最终确认调整为：固定 30 题中不少于 **26/30**，且 Day 5 的四个已知失败全部修复。

## SQL 错误恢复

`dbgpt_app.insight_agent.sql_error` 将数据库/预检异常归一为八类：语法、表不存在、列不存在、类型或日期、分组、列歧义、权限、超时，其他错误落到未知类。对外 Observation 仅保留错误码、可行动提示和是否可重试，不回显连接串、账号、口令、主机、文件路径或完整语句。

恢复策略是严格预算：首次失败后最多纠正一次；相同失败 SQL 不重复执行；权限和未知错误立即停止；第三次尝试被拒绝。成功结果保存在会话状态中，最终答案由确定性 presenter 直接读取 Observation，避免模型二次抄错数字。

## 综合 Agent 完成条件

综合任务必须按以下顺序完成：

1. 直接调用匹配的领域 Tool；
2. 获得实际知识库证据；
3. 调用 `html_interpreter` 渲染报告；
4. 才允许输出完成结论。

题目要求经销商制度时，恢复检索会定向查询《经销商分级与考核管理制度》3.2/4.2，而不是把任意知识库结果当作正确证据。最终摘要从领域 Tool 的结构化结果生成，明确 2026Q2、2026Q1、2025Q2、环比、同比、风险边界、制度依据与管理建议。

## 运行命令

单题或全量 Benchmark：

```powershell
.\.venv\Scripts\python.exe -m insight_agent.evaluation.run_eval `
  --split all --model deepseek-v4-pro --temperature 0 --timeout 120 `
  --output-dir insight_agent/evaluation/results/<new-run-id>
```

可重复使用 `--case-id` 只运行指定任务。结果目录非空时拒绝覆盖。

故障基准：

```powershell
.\.venv\Scripts\python.exe -m insight_agent.evaluation.day6_fault_benchmark `
  --output-dir insight_agent/evaluation/results/<new-fault-run-id>
```

主链路稳定性：

```powershell
.\.venv\Scripts\python.exe -m insight_agent.evaluation.day6_stability `
  --model deepseek-v4-pro --runs 5 --start-index 1 `
  --output-dir insight_agent/evaluation/results/<new-stability-run-id>
```

## 当前结果

- 固定 Pro 30 题最终候选：30/30；四个 Day 5 已知失败 4/4 修复。
- SQL/预检故障：9/9 分类正确，9/9 安全 Observation，所有可重试样本一次纠正后成功。
- 自动化：139 passed、0 failed；Ruff 全部通过。
- 修复后 5 次主链路严格九项稳定性：5/5 全项通过，九个单项各自均为 5/5；平均延迟 68.040 秒。

汇总数据见 `evaluation/results/day6-final-summary.json`。原始 SSE、日志及截图保留在本地验收证据中，不进入最终提交。

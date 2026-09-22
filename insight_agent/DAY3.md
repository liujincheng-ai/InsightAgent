# InsightAgent Day 3

最终交付文档：

- [Day 3 验收报告](DAY3_ACCEPTANCE_REPORT.md)
- [源码主链路图](DAY3_SOURCE_CHAIN.md)
- [面试要点](DAY3_INTERVIEW_POINTS.md)
- [详细面试准备指南](DAY3_INTERVIEW_GUIDE_DETAILED.md)

## 交付内容

`sales_diagnosis_tool` 是第一个确定性汽车配件经营分析 Tool。它只接收
区域、品类、季度和 `top_n`，使用固定的参数化只读 SQL 返回：

- 当前季度、环比、同比销售额；
- 加权毛利率及百分点变化；
- 产品与渠道的下降贡献；
- 区域与全国同品类趋势对比；
- 查询范围标识（`evidence`）。

金额单位是 CNY；变化率为 decimal（例如 `-0.3268` 表示 -32.68%）；毛利率
变化单位为 percentage points。无数据返回 `status=no_data`，输入或数据库问题
返回结构化 `status=error`，不会由模型补造数据。

## 原生 Web 接入链路

```text
component_configs._initialize_resource_manager
  -> ResourceManager.register_resource(sales_diagnosis_tool)
  -> agentic_data_api._react_agent_stream 读取 tool 资源
  -> ToolPack([..., sales_diagnosis_tool, ...])
  -> ReActAgent 将 name / description / 参数 Schema 写入 Action Space
  -> ToolPack 依据 Action 名称执行 FunctionTool
  -> Observation 回到 ReActAgent，决定继续、生成报告或 terminate
```

这条链路使用 InsightAgent 的 `@tool`、`FunctionTool`、`ToolPack` 与
`ResourceManager`；项目没有创建平行的独立 Agent Runtime。

## 运行方式

1. 确认 Docker Desktop 已启动，容器 `insight-postgres` 正在运行。
2. 运行 `scripts/windows/start_insight_agent.ps1`。脚本会安全读取 DeepSeek API
   Key 与只读数据库密码，仅放入当前服务进程环境。
3. 在 Web 中同时选择 `InsightAgent汽车配件销售库` 和
   `汽车配件企业制度库`，模型选 `deepseek-v4-pro`。
4. 使用固定主问题：

   > 分析 2026 年第二季度华东区域刹车系统配件销售下滑的主要因素，并结合经销商管理制度提出改进建议，生成带图表和引用依据的经营分析报告。

5. 使用全新会话连续运行 5 次。每次记录 Tool 调用、SQL、引用、最终回答、
   延迟与失败原因；通过线为完成至少 4 次且调用 `sales_diagnosis_tool` 至少 4 次。

## Day 2 回归修复

- 数据库专用 Prompt 现在要求以数据范围、关键指标和结论的字段模板收尾，明确
  单位、比较基准与“未查询”状态。
- 知识检索会从稳定分块元数据提取 `primarySection`，在 SSE、会话历史与引用追问
  中保留它。引用汇总优先使用该字段，再回退到历史文本解析。

## 初始 Benchmark

`evaluation/dataset/day3_initial.json` 在 Pro 运行前冻结 15 条任务：5 条 SQL、4 条
RAG、3 条 Tool、3 条综合任务。`evaluation/day3_benchmark.py` 校验数据集契约并从
原始记录汇总通过率、SQL 执行率、预期 Tool 调用率、RAG 命中率、综合任务通过率、
延迟和估算成本；不会忽略失败记录。

## 面试要点

1. `@tool` 将函数包装为 `FunctionTool`，保留名称、描述、参数 Schema 与执行函数。
2. `FunctionTool` 是 `BaseTool` 的具体实现；`ToolPack` 用 Tool 名称定位并执行它。
3. ResourceManager 在启动时登记 Tool，Web ReAct 路径将所有 `tool` 类型实例加入
   当前回合的 ToolPack，因此模型能在原生 Action Space 中发现业务能力。
4. Action 执行结果以 Observation 回注；模型在下一轮决定继续调用、生成报告或
   `terminate`。业务 Tool 的确定性 SQL 与指标计算避免把可验证的口径交给模型临时
   编写代码。

# Week 2：Tool 选择与参数稳定性

## 目标

在三个业务 Tool 同时存在时，区分模型自主选择能力与生产规则兜底能力，系统评测误选、漏选、多余调用和参数错误，并保证无效参数在任何数据库访问前被阻断。

## 双轨设计

### 评测模式

- 同时暴露 `sales_diagnosis_tool`、`customer_loss_analysis_tool`、`dealer_health_analysis_tool` 和 `sql_query`。
- 关闭规则预选、强制首调用门禁和缺失 Action 自动恢复。
- 保留 InsightAgent 原生 ReAct 与 ToolPack 执行链路。
- 只用于可复现的 Tool Calling 专项实验。

### 生产模式

- 保留 `select_domain_tool()`、`SalesDiagnosisFirstToolPack` 和受控恢复。
- 将模型选择能力与端到端业务成功率分开报告。
- 不因评测实验降低正式 Web Demo 的可靠性。

## 冻结数据集

- 总计 40 条：三个业务 Tool 各 10 条、通用 SQL 5 条、组合 Tool 5 条。
- Split：24 dev、12 test、4 challenge。
- 只允许根据 dev 失败优化；test/challenge 冻结后不参与调参。
- 每题保存预期 Tool 序列、参数、边界标签和 SHA-256 指纹。

## 三组配置

1. `baseline`：Week 1 原始 description 与签名推断参数。
2. `positive`：精简正向适用场景，仍使用旧参数元数据。
3. `boundary`：正向描述、负向边界、完整参数 Schema 和执行前校验。

`baseline` 与 `positive` 隔离 description 变化；`boundary` 是包含 Schema 与安全校验的候选生产契约。报告不得把 `positive` 到 `boundary` 的全部差异只归因于 description。

## 指标

- Tool Selection Accuracy。
- 各 Tool Precision、Recall、F1。
- Argument Validity 与参数语义准确率。
- Execution Success。
- 组合 Tool 顺序准确率。
- 多余调用率。
- 单标签混淆矩阵。

## 验收线

- Tool 选择准确率至少 90%。
- 每个业务 Tool 的召回率至少 80%。
- 参数有效率至少 95%。
- 多余调用率不超过 5%。
- 非法参数进入数据库执行次数为 0。
- 原有回归和 Week 2 新增测试全部通过。

## 实验纪律

- 三组 Flash 配置各完整运行 3 次，报告均值、标准差和 95% 区间。
- 代码、数据集和评测器冻结后，只执行一次 Pro 40 题最终验收。
- 不覆盖原始轨迹，不挑选最好一次，不因 Pro 失败而补跑。
- 原始运行结果保存在 Git 忽略目录；提交数据集、实现、测试和汇总报告。

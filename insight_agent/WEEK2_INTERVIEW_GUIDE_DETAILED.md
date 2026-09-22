# Week 2 Tool Calling 稳定性面试指南

## 1. 这一周解决了什么问题

三个业务 Tool 同时存在后，模型不仅可能选错 Tool，还可能漏掉组合任务中的第二个 Tool、对普通聚合题滥用业务 Tool，或者生成字段名正确但值越界的参数。Week 2 将这些故障从主观演示转化为 40 条冻结数据集上的可测量问题。

## 2. 为什么生产成功率不能直接代表模型选择能力

生产链路包含 `select_domain_tool()`、首 Tool 门禁和缺失 Action 自动恢复。它们能提高用户最终成功率，但也会掩盖模型原始误选和漏选。如果直接在这条链路上计算准确率，结果主要反映规则路由，而不是 description 或 Schema 的效果。

因此项目使用双轨设计：

- 评测模式关闭规则预选、强制门禁和自动恢复，只保留 ReAct、ToolPack、SQL 与三个业务 Tool；
- 生产模式保留全部可靠性机制，单独验证端到端任务是否完成。

这不是为了让生产系统“裸奔”，而是为了让实验变量可解释。

## 3. LLM 如何知道有哪些 Tool

InsightAgent 将每个 `BaseTool` 的名称、description 和参数信息拼入 Agent 的资源 Prompt。模型按 ReAct 文本协议输出：

```text
Thought: ...
Action: customer_loss_analysis_tool
Action Input: {"region":"华东", ...}
```

`ReActOutputParser` 解析动作，`ToolPack` 按名称定位 `FunctionTool`，再把 JSON 参数交给具体函数。Week 2 的评测从 SSE `step.meta` 提取 Action 和 Action Input，从 `step.chunk` 提取 Observation，因此评分基于真实执行轨迹，而不是最终答案中模型自述“调用了什么”。

## 4. Tool description 为什么会影响选择

Tool 名称只提供粗粒度意图，description 才说明输入、输出、适用问题和边界。当两个 Tool 都出现“下降”“客户”“经销商”等词时，只写正向能力容易造成语义重叠；增加清晰的负向边界可以告诉模型何时不要调用。

三组消融分别是：

1. `baseline`：原始 description 和签名推断参数；
2. `positive`：精简正向职责，参数元数据保持不变；
3. `boundary`：增加负向边界、完整 Schema 和执行前校验。

`baseline` 对 `positive` 可以较集中地观察 description 变化；`positive` 对 `boundary` 同时改变负向边界和 Schema，因此只能称为组合工程改进，不能声称是单一因素因果结果。

## 5. 为什么没有修改三个 Tool 名称

现有名称已经明确区分销售诊断、客户流失和经销商健康，而且被注册、测试、Prompt 和恢复逻辑引用。为了“看起来优化”而重命名会引入兼容风险，却没有证据说明名称本身造成混淆。因此 Week 2 保持稳定 API 名称，只优化有真实缺口的 description 和参数契约。

## 6. 为什么不用一个万能 Tool

万能 Tool 会把大量可选参数集中到一个 Schema，导致职责模糊、参数组合爆炸和失败语义不清。三个 Tool 按经营问题拆分后，可以分别单测、维护固定 SQL 和定义业务口径。反过来，Tool 也不能无限拆分，所以用混淆矩阵验证当前边界，而不是继续增加第四个 Tool。

## 7. 参数 Schema 原来有什么缺口

原 `FunctionTool.args_schema` 能读取 Pydantic 字段的类型和描述，但没有完整保留 `enum`、`pattern`、`minimum`、`maximum` 等约束，也不会在通用 `FunctionTool` 执行前调用 Pydantic 校验。`ToolPack` 还会静默删除未知字段，使 `extra="forbid"` 无法生效。

Week 2 做了向后兼容的显式增强：

- `ToolParameter` 保存并展示 JSON Schema 约束；
- `FunctionTool` 增加可选 `validate_args=True`；
- 只有显式启用的 Tool 才在执行前验证，旧 Tool 行为不变；
- 启用验证的 Tool 不再由 ToolPack 静默删除未知参数；
- 校验失败返回 `invalid_arguments`、字段级 details 和 `retryable=true`；
- 失败发生在业务函数与数据库执行器创建之前。

## 8. 为什么校验必须在数据库前

如果错误参数先进入业务函数甚至 SQL，系统可能浪费数据库连接、得到误导性空结果，或者扩大注入与越权风险。Prompt 只能降低出错概率，不能构成安全边界；执行前 Schema 校验、参数化 SQL 和数据库只读权限分别承担输入、语句和权限三层防线。

## 9. 参数错误什么时候允许重试

季度格式、字段名或数值范围错误通常可从结构化 details 修复，因此最多允许一次修正。权限错误、数据库连接错误、未知错误或第二次相同失败不自动重试。这样既给模型有限恢复机会，又避免失败循环。

## 10. 数据集如何避免过拟合

40 题分为 24 dev、12 test、4 challenge。只允许查看 dev 失败来修改 description、Schema 或错误反馈；test/challenge 在冻结后不参与调参。数据集同时保存版本、状态和 SHA-256，运行 Manifest 保存数据集指纹、模型、温度、代码状态和配置。

题目构成包括：

- 三个业务 Tool 各 10 条；
- 5 条普通 SQL 题，验证不应调用业务 Tool；
- 5 条组合题，验证最小 Tool 集合与调用顺序；
- 同义改写、自然季度表达、干扰词和显式负向边界。

## 11. 为什么不能只看 Selection Accuracy

选对 Tool 但把 `2026Q2` 写成 `2026-Q2`，或者把 50% 阈值写成 50，任务仍然会失败。因此至少分开记录：

- Tool Selection Accuracy；
- 各 Tool Precision、Recall、F1；
- Argument Validity；
- 参数语义准确率；
- Execution Success；
- 组合 Tool 顺序准确率；
- 多余调用率。

选择、参数和执行分开后，才能判断问题来自路由、填参还是工具本身。

## 12. 混淆矩阵能说明什么

混淆矩阵以预期 Tool 为行、首个实际 Tool 为列，适合定位重复误选，例如客户流失题经常被路由到销售诊断。组合题不是单标签分类，因此另用 Tool 集合准确率和顺序准确率评分，避免强行塞入普通混淆矩阵。

## 13. 为什么重复运行三次

即使 temperature 为 0，远程模型、服务实现和 ReAct 路径仍可能存在波动。每组 Flash 配置重复三次，报告均值、标准差和 Wilson 95% 区间，可以避免把一次偶然结果包装成稳定提升。Pro 只运行一次，是为了控制成本并防止选择性补跑。

## 14. 原生 Function Calling 与 ReAct Tool Calling 的区别

原生 Function Calling 通常由模型 API 返回结构化 `tool_calls`；ReAct 则通过 Thought、Action、Action Input 文本协议解析。二者上游接口不同，但下游都需要 Tool 注册、参数 Schema、执行前校验、权限控制、Observation 和重试边界。InsightAgent 当前沿用 InsightAgent 的 ReAct 路径，没有为了简历名词额外重写一套原生调用框架。

## 15. 如何解释规则路由与 LLM 路由同时存在

评测模式回答“模型自身能否稳定选择”，生产模式回答“系统能否可靠完成”。在高价值、固定领域流程中，规则门禁是合理的可靠性层；在开放问题中，仍需要模型理解意图。工程上不应把两者对立，而应明确各自指标和失败责任。

## 16. 面试时不能夸大的内容

- 40 题是合成业务场景的小样本，不代表线上准确率；
- 三次重复只能观察当前模型和数据集上的波动；
- `boundary` 同时包含负向描述和 Schema，不能全部归因于 description；
- 参数校验不等于完整安全，数据库只读权限仍是最终防线；
- 最终数字必须来自冻结运行，不写“准确率 100%”或未实际测得的提升。

## 17. 最终结果与面试回答

首次 Flash 三次重复中，`boundary` 选择为 93.33%、参数有效率为 94.17%，未达到参数门槛。协议修复后的正式重新验收中，`baseline`、`positive`、`boundary` 选择均值分别为 100%、100%、99.17%，参数有效率均为 100%；`boundary` 三个业务 Tool 聚合召回率均为 100%。Schema 的直接价值仍是执行前阻断非法输入，不能只依据同集修复回归宣称它能提高未知样本准确率。

首次 Pro `boundary` 仅通过 14/40：Tool 选择 40%、参数有效率 42.5%。24 条选择失败中，23 条没有形成可执行 Tool Action。兼容一行式、JSON、蛇形字段和全角冒号 ReAct 后，正式重新验收为 38/40：选择 97.5%、参数有效率 100%、三个业务 Tool 召回率均为 100%。面试时必须同时披露首次失败，并说明后者是同一冻结集上的修复回归，不是新的独立盲测。

生产链路三条烟测为 3/3，通过纯 RAG、单业务 Tool 和综合 HTML 报告。综合轨迹依次调用销售诊断、制度检索和 HTML 工具。这证明规则门禁能保障当前演示链路，但生产 3/3 不能替代隔离评测指标。

推荐回答：

> 我把生产兜底和模型自主选择拆成两条链路。首次 Pro 只有 14/40，复盘发现 24 条选择失败中 23 条没有形成可执行 Action，根因是文本 ReAct 解析器不接受模型常用的结构化表达。我做了有边界的兼容：接受明确 Action 的一行式、JSON 和全角格式，但不根据裸业务参数猜 Tool。按预登记方案在同一冻结集复验后，Flash boundary 选择 99.17%、参数有效率 100%，Pro 38/40，生产烟测 3/3。我会明确说明这是已观察失败后的修复回归，不把它包装成独立盲测或生产准确率。

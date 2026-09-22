# InsightAgent Day 3 面试准备与项目讲解指南

> 用途：用于项目面试、自我介绍、技术追问和现场 Demo。文档中的数字来自当前合成演示数据，不对应真实企业。

## 一、30 秒项目概述

我在 InsightAgent 上开发了一个汽车配件经营分析 Agent。Day 3 的重点不是再做一个独立聊天机器人，而是把一个确定性的销售诊断能力，以 InsightAgent 原生 Tool 的方式接入现有 Web ReAct 流程。

用户同时选择销售数据库和企业制度知识库后，Agent 会先调用 `sales_diagnosis_tool` 获取销售、毛利、产品、渠道和全国对比事实，再检索《经销商分级与考核管理制度》，最后通过 `html_interpreter` 生成带图表和引用依据的经营分析报告。整个过程由原生 `ResourceManager`、`FunctionTool`、`ToolPack` 和 `ReActAgent` 串起来，并通过门禁避免模型跳过数据事实或用制度文本替代数据库分析。

## 二、Day 3 完成了什么

### 1. 原生销售诊断 Tool

新增 `insight_agent/tools/sales_diagnosis.py`，暴露固定接口：

```text
sales_diagnosis_tool(
    region: str,
    category: str,
    current_quarter: str,
    top_n: int = 5,
) -> dict
```

它执行固定的、参数化的只读 SQL，返回：

- 当前季度、上季度、去年同期销售额；
- 环比和同比金额、变化率；
- 当前及上季度加权毛利率、百分点变化；
- 产品下降贡献排名；
- 渠道下降贡献排名；
- 区域与全国同品类趋势对比；
- 每个结果对应的查询范围 `evidence`。

输入范围和错误均结构化处理：

- `top_n` 必须是 1 到 20 的整数；
- 季度必须符合 `YYYYQn`；
- 无数据返回 `status=no_data`；
- 参数或数据库异常返回 `status=error`；
- 不让模型自行补造缺失数字。

### 2. 原生 ResourceManager 注册

在 `component_configs.py` 启动初始化阶段登记 `sales_diagnosis_tool`。Web 请求组装 ToolPack 时，从 ResourceManager 获取 `tool` 类型资源，并将业务 Tool 放进当前 ReAct 回合的 Action Space。

因此模型看到的是 InsightAgent 原生工具，不是额外 HTTP 服务，也不是旁路 Agent。这个设计保留了 InsightAgent 的权限、日志、Observation 回注和生命周期管理能力。

### 3. 综合数据库 + 知识库流程

Day 3 的主问题同时选择数据库和知识库。新增综合 Prompt，明确要求：

1. 先建立三个任务：数据诊断、制度依据、报告输出；
2. 第一项数据动作直接调用 `sales_diagnosis_tool`；
3. 事实只能来自 Tool Observation 或只读 SQL；
4. 再检索制度库，重点引用 3.2 和 4.2 节；
5. 最后调用 `html_interpreter`，再 `terminate`。

### 4. 工作流门禁

新增 `SalesDiagnosisFirstToolPack`，它仍然是 `ToolPack` 子类，只增加了流程状态：

```text
sales_diagnosis_completed
knowledge_evidence_completed
html_report_completed
```

门禁规则：

- 未完成销售诊断时，只允许计划工具和 `sales_diagnosis_tool`；
- 销售诊断完成后，才允许知识库工具；
- HTML 报告完成前，阻止 `code_interpreter`、`shell_interpreter`、`execute_tool` 等绕过报告流程的工具；
- 所有证据和报告完成前，`terminate` 不能作为有效终点。

这不是另起一个 Agent，而是把业务约束放在原生 ToolPack 执行层，避免只依赖 Prompt。

### 5. DeepSeek DSML 调用兼容

DeepSeek Pro 的部分响应使用 DSML 格式，例如：

```text
<｜｜DSML｜｜invoke name="sales_diagnosis_tool">
<｜｜DSML｜｜parameter name="region" string="true">华东
```

InsightAgent 原解析器主要处理标准 ReAct/Kimi 格式，因此新增 DSML 解析分支，把 `invoke` 和 `parameter` 转换为统一的 `Action` / `Action Input`。这样业务代码不需要知道模型使用哪种协议。

### 6. Day 2 遗留问题修复

- SQL 结果 Prompt 增加数据范围、当前值、比较基准、单位和“未查询”字段；
- RAG 检索从分块元数据提取 `primarySection`，并贯穿 SSE、历史记录、引用汇总和引用追问；
- 引用优先使用稳定元数据，只有缺失时才回退到文本启发式解析。

### 7. HTML 兜底

实际运行中发现模型可能已经拿到销售事实和制度依据，却直接输出文字总结，没有真正发出 `html_interpreter` Action。于是增加服务端兜底：综合流程结束时检查 ToolPack 状态，如果 HTML 尚未完成，则使用已经采集的销售 Observation 构造报告并调用 `html_interpreter`。

这个兜底保证报告要求不会因为模型最后一轮输出习惯而失效，同时保留正常情况下由模型生成报告的路径。

## 三、真实演示数据与验收指标

固定主问题：

> 分析 2026 年第二季度华东区域刹车系统配件销售下滑的主要因素，并结合经销商管理制度提出改进建议，生成带图表和引用依据的经营分析报告。

一次真实 Tool Observation 的核心结果：

| 指标 | 结果 |
|---|---:|
| 2026Q2 销售额 | 1,087,378.79 元 |
| 环比变化 | -32.68% |
| 同比变化 | -29.27% |
| 当前毛利率 | 26.13% |
| 毛利率环比变化 | -2.7839 个百分点 |
| 经销商渠道下滑贡献率 | 74.89% |
| 全国刹车系统环比变化 | -4.47% |

制度库命中：

- 3.2 节：季度销售额环比下降超过 20% 触发经营预警；
- 4.2 节：1 个工作日预警、5 个工作日提交整改计划、10 个工作日联合拜访、30 日观察期和后续复核。

自动化回归结果：

```text
76 passed, 4 warnings
ruff check: All checks passed
```

最终验收目标是使用 DeepSeek Pro 新会话运行 5 次，至少 4/5 完成，并且至少 4/5 调用 `sales_diagnosis_tool`。

## 四、遇到的问题、定位过程与解决方案

### 问题 1：相对路径启动脚本失败

现象：在 `E:\agentDB` 执行 `./scripts/windows/start_insight_agent.ps1`，PowerShell 报找不到脚本。

原因：脚本实际位于 `E:\agentDB\InsightAgent\scripts\windows`，当前目录不对。

解决：先进入仓库目录，再执行脚本；同时在文档中固定完整启动路径。

面试表达：这是典型的运行上下文问题，不应把它误判成业务代码故障。先确认当前目录、脚本实际位置和 PowerShell 的相对路径解析规则。

### 问题 2：只读数据库密码不一致

现象：数据库连接提示密码认证失败。

定位：确认 PostgreSQL 角色存在、连接权限正确后，发现实际只读密码与 InsightAgent SQLite 数据源配置不一致。

解决：在 PostgreSQL 中将 `insight_readonly` 密码与运行时环境变量保持一致，同步更新 InsightAgent 数据源配置，并用主机 Python `psycopg2` 执行 `SELECT 1` 验证。真实密码不写入代码、文档或 Git。

安全措施：数据库 Tool 使用只读角色、`SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY`、参数化查询；密码不写入源码。

### 问题 3：模型只走知识库，不调用销售 Tool

现象：选择了数据库和知识库，但 Web 流程先调用 `kb_grep` / `kb_cat`，没有销售数字。

原因：`_is_knowledge_turn` 只根据知识库选择判断，把“数据库 + 知识库”错误地当成纯知识库快速路径。

解决：只有存在知识库且没有数据库时才进入知识库 Fast Path；数据库和知识库同时存在时走 integrated mode，并把销售 Tool 加入综合 ToolPack。

### 问题 4：ResourceManager 已注册，但请求 ToolPack 中找不到 Tool

现象：启动日志显示注册成功，模型 Action Space 仍然没有 `sales_diagnosis_tool`。

原因：启动初始化和请求资源组装存在时序差异，某些请求建立 ToolPack 时 ResourceManager 资源还没有被展开。

解决：ResourceManager 仍是正式注册来源，同时在综合请求组装处做一次显式资源确认；如果当前 ToolPack 中缺失，就把已注册的原生 `sales_diagnosis_tool` 加入，而不是创建旁路执行器。

### 问题 5：专用 ToolPack 被核心代码重新包装

现象：虽然构造了 `SalesDiagnosisFirstToolPack`，但执行时门禁不生效。

原因：`ToolPack.from_resource` 把已有的专用 ToolPack 当作普通 ResourcePack 重新构造成普通 `ToolPack`，丢失了子类状态。

解决：当传入对象本身已经是 `ToolPack` 时直接保留；当 ResourcePack 中只有一个嵌套 ToolPack 时也保留该实例。这样执行链路不会丢掉门禁状态。

### 问题 6：模型通过 `execute_tool` 间接调用业务 Tool

现象：模型先调用 `execute_tool` 或 `load_tools`，而不是直接调用 `sales_diagnosis_tool`。

解决：门禁在执行层阻止所有非计划、非销售诊断动作，并返回结构化错误，明确告诉模型必须先直接调用销售 Tool。这样即使模型偏离 Prompt，也能通过 Observation 自我纠正。

### 问题 7：DeepSeek 输出 DSML，标准解析器无法识别

现象：日志中能看到 DSML `invoke` 文本，但 InsightAgent 没有形成有效 Action。

解决：在 `react_parser.py` 增加 DSML 正则解析，并转换到现有 Action 模型；用单元测试覆盖字符串参数、JSON 参数和完整工具调用。

### 问题 8：模型拿到证据后提前结束，没有 HTML

现象：销售 Tool 和制度库调用成功，但页面没有 `html_interpreter` 步骤。

解决分两层：

1. Prompt 和 ToolPack 门禁要求报告必须最后渲染；
2. 服务端在综合流程结束时检查状态，若模型提前总结，则用已采集事实自动调用 `html_interpreter`。

面试重点：不要只说“加了更强 Prompt”。真正可靠的约束应放在工具执行层和服务端状态机，Prompt 负责引导，代码负责兜底。

## 五、源码主链路讲解

```text
服务启动
  -> component_configs 初始化 ResourceManager
  -> register_resource(sales_diagnosis_tool)
  -> Web 请求判断 database + knowledge integrated mode
  -> 组装原生 ToolPack / SalesDiagnosisFirstToolPack
  -> ReActAgent 构建 Action Space
  -> DeepSeek 输出 ReAct 或 DSML
  -> react_parser 解析 Action
  -> ToolPack 执行 FunctionTool
  -> Observation 回注模型
  -> kb_grep / kb_cat 获取制度证据
  -> html_interpreter 渲染报告
  -> terminate 返回结果
```

面试时建议按“入口、资源注册、工具执行、状态门禁、结果回注、报告输出”六个点讲，不要一开始陷入 SQL 细节。

## 六、高频面试问题与参考回答

### Q1：为什么不直接让大模型写 SQL？

参考回答：销售经营分析需要稳定口径。若让模型临时写 SQL，时间范围、同比基准、毛利率加权方式和空值处理都可能变化，结果难以审计。我把高价值、可复用的指标封装成固定参数化只读 SQL，模型只负责选择区域、品类和季度，结果由代码计算并结构化返回。这样兼顾了自然语言交互和数据口径稳定性。

### Q2：`sales_diagnosis_tool` 和普通函数有什么区别？

参考回答：它通过 InsightAgent 的 `@tool` 装饰器注册为 `FunctionTool`，拥有标准名称、描述、参数 Schema 和执行入口，随后被放入原生 `ToolPack`。因此 ReActAgent 能在 Action Space 里发现和调用它，Observation 也走 InsightAgent 原生链路。

### Q3：如何确保模型一定先查数据库？

参考回答：Prompt 只是第一层引导，真正的约束是 `SalesDiagnosisFirstToolPack`。它记录销售诊断、制度证据和 HTML 报告三个状态。未完成销售诊断时，其他工具直接返回结构化 blocked 结果；报告前也禁止用 Python、Shell 或通用 execute_tool 绕过 HTML 步骤。

### Q4：为什么综合流程不能复用知识库 Fast Path？

参考回答：知识库 Fast Path 的设计目标是制度问答，默认不会暴露数据库工具。综合任务同时需要数据库事实和制度依据，如果复用该路径，模型可能只检索制度而没有销售事实，所以我把“有数据库”作为排除条件，单独走 integrated mode。

### Q5：ResourceManager 注册了工具，为什么还要显式加入 ToolPack？

参考回答：ResourceManager 是正式注册源，但请求资源组装存在启动时序问题。为保证第一次请求也能看到业务 Tool，我在综合请求组装处做资源存在性确认，缺失时加入同一个原生 Tool 实例。它不是重复注册，也不是旁路执行器，而是对请求级 ToolPack 的确定性补全。

### Q6：如果模型输出不符合 ReAct 格式怎么办？

参考回答：解析层做协议适配。我增加了 DeepSeek DSML 解析，把 `invoke`、`parameter` 转换成 InsightAgent 统一 Action；工具层再根据名称和参数 Schema 执行。这样模型协议变化不会扩散到业务 Tool。

### Q7：为什么需要 HTML 兜底？

参考回答：真实测试发现模型可能已经完成事实和制度检索，却直接输出总结，导致用户没有可交互报告。于是服务端在综合流程结束时检查 HTML 状态，缺失时用已采集 Observation 调用 `html_interpreter`。这体现了 Agent 系统中“模型负责规划、程序负责关键不变量”的原则。

### Q8：如何避免幻觉数据？

参考回答：第一，销售数字只能来自固定 SQL Tool Observation；第二，返回值带单位、比较基准和 evidence；第三，无数据和异常使用结构化状态，不返回伪造零值；第四，制度建议和数据库事实在 Prompt 与报告模板中分开标记。

### Q9：数据库安全怎么做？

参考回答：使用最小权限只读角色，连接后设置只读事务，所有 SQL 使用参数化占位符，区域、品类和季度只作为参数传入。凭据只放在当前服务进程环境，不写入仓库；代码和测试不打印 API Key 或数据库密码。

### Q10：为什么返回贡献率，而不是只返回下降金额？

参考回答：下降金额告诉我们损失规模，贡献率告诉我们优先级。例如经销商渠道贡献 74.89%，说明经营动作应优先围绕经销商，而不是平均分配资源给所有渠道。贡献率还能直接支持报告排序和管理建议。

### Q11：为什么要做区域与全国对比？

参考回答：它用于区分系统性市场下滑和区域经营问题。当前华东刹车系统环比下降 32.68%，全国同品类只下降 4.47%，因此更像区域渠道或客户经营问题，而不是全行业同步下滑。这个对比提升了建议的针对性。

### Q12：如何测试 Agent，不只是测试函数？

参考回答：分三层测试：Tool 层测试输入校验、SQL 参数和指标计算；集成层测试 ResourceManager 注册、ToolPack 门禁、ReAct 解析和引用链路；验收层用 15 条冻结 benchmark 覆盖 SQL、RAG、Tool 和综合任务，并记录完成率、Tool 调用率、延迟和失败原因。

### Q13：为什么不把所有约束写在 Prompt 里？

参考回答：Prompt 对模型是软约束，模型可能误解、截断或输出另一种协议。涉及权限、顺序、只读和报告生成的不变量必须放在代码层；Prompt 负责解释任务，ToolPack 和服务端状态机负责执行安全边界。

### Q14：如果知识库证据不足怎么办？

参考回答：报告必须明确“证据不足”，不能从制度文本推断销售数字。引用链路优先使用检索分块的 `primarySection`；找不到稳定章节时才回退到文本解析，并在最终报告区分数据库事实、制度原文和管理判断。

### Q15：这个项目最大的工程难点是什么？

参考回答：不是单个 SQL，而是把确定性业务能力嵌入已有 Agent 生命周期，同时处理路径选择、资源注册时序、ToolPack 子类保留、模型协议差异和最终报告不变量。最终方案是“原生接入 + 执行层门禁 + 协议适配 + 服务端兜底”，而不是另起一套 Agent。

## 七、面试现场 Demo 讲法

1. 先展示数据库和制度库同时选中，强调这是综合模式。
2. 输入固定主问题。
3. 指出第一步是 `sales_diagnosis_tool`，展示结构化销售、毛利和渠道贡献。
4. 指出全国对比说明这是区域性问题。
5. 展示知识库命中 3.2、4.2 节，并说明建议中的时间节点来自制度，而不是模型臆测。
6. 展示 `html_interpreter` 报告，强调报告同时包含图表、引用和事实范围。
7. 最后说明门禁和兜底：即使模型想跳过步骤，执行层也会阻止；即使模型提前总结，服务端也会补齐 HTML 渲染。

## 八、容易被追问的不足与诚实回答

### 1. 5 次 Pro 实测是否全部完成？

回答：自动化测试和真实 Tool 诊断已经通过；5 次 Pro 统计是 Day 3 最终验收指标，需要在加载最新服务进程后按固定问题完成连续记录。当前报告不会把尚未完成的 5 次统计伪装成已完成。

### 2. 为什么使用合成数据？

回答：为了让演示口径、异常场景和验收结果可重复，同时避免真实企业数据泄露。生产化时只需替换数据源和权限配置，Tool 接口和报告链路保持不变。

### 3. 兜底报告是否意味着模型不可靠？

回答：兜底不是替代模型，而是保障业务不变量。模型仍负责理解问题、选择工具和组织建议；服务端只对“必须发生的报告渲染”做最后检查，这和支付、审批系统中的状态校验是同一类工程思想。

## 九、项目亮点总结

- 把自然语言经营问题拆成确定性的可审计指标 Tool；
- 使用 InsightAgent 原生资源体系，没有平行 Agent Runtime；
- 用 ToolPack 执行层实现“先事实、后制度、再报告”；
- 兼容 DeepSeek DSML 与标准 ReAct 输出；
- 将 SQL 事实、RAG 章节和 HTML 报告串成可追溯证据链；
- 用自动化测试和冻结 benchmark 衡量 Agent，而不是只看一次 Demo；
- 凭据、只读权限、参数化 SQL 和失败状态都纳入工程设计。

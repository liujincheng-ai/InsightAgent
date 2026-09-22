# Day 3 面试要点

## 架构与接入

1. 为什么使用原生 Tool：通过 InsightAgent 的 `@tool`、`FunctionTool`、`ToolPack` 和 `ResourceManager` 接入，模型在原生 Action Space 中发现能力，不另起一套 Agent Runtime。
2. ResourceManager 的职责：启动时登记业务资源；Web 请求组装当前回合的 ToolPack。
3. 为什么 ToolPack 需要门禁：综合任务必须先取得可审计的销售事实，再查制度、再生成报告，避免 RAG 文本替代数据库事实。

## 数据与可靠性

4. 为什么固定 SQL：销售口径、时间范围和指标计算必须可复现；模型只填白名单参数，不能临时编写任意 SQL。
5. 为什么返回结构化结果：金额、变化率、毛利百分点、贡献率和 evidence 分开返回，便于 UI、测试和报告复用。
6. 如何处理无数据和异常：统一返回 `status=no_data` 或 `status=error`，不让模型猜测数字。

## Agent 行为与兼容性

7. DeepSeek DSML 兼容：解析器把 DSML `invoke/parameter` 映射为 InsightAgent 标准 Action，兼容不同模型输出协议。
8. 为什么要 HTML 兜底：模型可能在拿到证据后直接输出总结；服务端检查综合流程是否已渲染，缺失时用已采集事实调用 `html_interpreter`。
9. 为什么保留 `primarySection`：引用章节来自检索分块元数据，比从最终回答文本猜章节稳定，并贯穿 SSE、历史和追问。

## 验收与取舍

10. 自动化测试覆盖 Tool 输入校验、SQL 口径、门禁、注册、解析器、引用和 benchmark 契约；当前回归为 76 个通过。
11. 真实验收关注两类指标：任务完成率和业务 Tool 调用率；Pro 五次运行目标至少 4/5 完成且至少 4/5 调用 `sales_diagnosis_tool`。
12. 安全边界：数据库连接使用只读角色、参数化查询、短生命周期连接；API Key 和数据库密码只存在服务进程环境，不写入仓库。

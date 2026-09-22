# InsightAgent Day 4 执行进度

开始时间：2026-09-08 02:11:56 +08:00

状态说明：`⬜ 待执行`、`🔄 执行中`、`✅ 已完成`、`⚠️ 有问题但已处理`、`⛔ 阻塞`。

| 步骤 | 状态 | 内容 | 结果 / 证据 |
|---:|:---:|---|---|
| 1 | ✅ | 创建 Day4 进度清单 | 本文档 |
| 2 | ✅ | 固化客户流失业务口径 | `DAY4_RULES.md` 第 1 节 |
| 3 | ✅ | 固化经销商健康度评分规则 | `DAY4_RULES.md` 第 2 节 |
| 4 | ✅ | 建立制度条款映射 | `DAY4_RULES.md` 制度依据与规则边界 |
| 5 | ✅ | 生成数据库 Gold Truth | `data/gold/day4_gold_truth.json`；真实 PostgreSQL 只读查询 |
| 6 | ✅ | 补充公共指标函数 | `tools/metrics.py` |
| 7 | ✅ | 验证公共指标函数 | `29 passed` |
| 8 | ✅ | 实现客户流失分析 Service | `tools/customer_loss_analysis.py` |
| 9 | ✅ | 封装客户流失 Tool | 原生 `@tool` 与结构化契约 |
| 10 | ✅ | 测试客户流失 Tool | `7 passed` |
| 11 | ✅ | 实现经销商健康度 Service | `tools/dealer_health_analysis.py` |
| 12 | ✅ | 封装经销商健康度 Tool | 原生 `@tool` 与四项评分契约 |
| 13 | ✅ | 测试经销商健康度 Tool | `8 passed` |
| 14 | ✅ | 注册三个业务 Tool | `tools/__init__.py`、`component_configs.py` |
| 15 | ✅ | 改造 Agent 工具路由门禁 | 按问题选择领域 Tool；综合任务保留证据链 |
| 16 | ⚠️ | 测试三类 Tool 选择 | 首轮 1 个 Day3 Prompt 回归失败；恢复制度 4.2 约束后 `35 passed` |
| 17 | ✅ | 运行 InsightAgent 全量回归 | `90 passed, 3 warnings` |
| 18 | ⚠️ | 执行代码质量检查 | 首轮 11 个行长问题；格式化并修正测试迭代后 Ruff 通过 |
| 19 | ✅ | 启动或重启 InsightAgent | 5670 端口监听；HTTP 200；PostgreSQL `accepting connections` |
| 20 | ✅ | 销售诊断 Web UI 验收 | `sales_diagnosis_tool`；1,087,378.79 元；环比 -32.68%；同比 -29.27%；经销商贡献 74.89% |
| 21 | ✅ | 客户流失 Web UI 验收 | `customer_loss_analysis_tool`；默认 `2026Q2`；A级客户 Top 3 与 Gold Truth 一致 |
| 22 | ✅ | 经销商健康 Web UI 验收 | `dealer_health_analysis_tool`；一号 62/100、medium；扣分 28/6/4 |
| 23 | ✅ | 汇总 Day4 验收证据 | `evidence/day4/`：三张截图、三份原始 Tool 输出、数据库结果、测试日志及会话清单 |
| 24 | ✅ | 编写 Day4 详细面试指南 | `DAY4_INTERVIEW_GUIDE_DETAILED.md` |
| 25 | ✅ | 更新 Day4 使用说明 | `DAY4.md` |
| 26 | ✅ | 生成最终 Day4 验收文档 | `DAY4_ACCEPTANCE_REPORT.md` |

## 执行记录

- 2026-09-08 02:11:56：确认分支为 `feature/insight-agent-v1`，执行前工作区干净；按用户要求不创建 Git Commit。
- 2026-09-08：冻结客户风险、经销商四项评分、风险分级及制度映射；未由制度规定的阈值均明确标为 V1 演示规则。
- 2026-09-08：首次 Gold Truth 查询因容器不存在默认 `postgres` 角色失败；改用容器声明的 `insight` 用户后完成只读查询，未输出密码。
- 2026-09-08：公共指标函数 29 项边界测试通过。
- 2026-09-08：客户流失 Tool 7 项测试通过。
- 2026-09-08：经销商健康度 Tool 8 项测试通过。
- 2026-09-08：路由集成首轮 35 项中 1 项失败，原因是重构 Prompt 时遗漏 Day3 制度 4.2 显式要求；恢复约束后 35 项全部通过。
- 2026-09-08：复核发现制度 4.2 约束不能泛化到所有报告问题；改为按销售、客户流失、经销商健康意图动态选择制度章节，并增加换题回归测试。
- 2026-09-08：全量专项回归 `81 passed, 2 warnings`；Ruff 检查通过。两条警告来自既有第三方弃用提示。
- 2026-09-08：真实 PostgreSQL 验证与 Gold Truth 一致；只读角色仅有 SELECT 权限。证据保存至 `evidence/day4/`。
- 2026-09-08：首轮 Web UI 销售题失败：通用 `execute_tool` 被误选并产生虚构结果。根因是资源前缀触发完整报告误判，且间接入口与领域 Tool 同时暴露；已清理前缀、移除间接入口并补充准确参数契约。
- 2026-09-08：第二轮 Web UI 在执行前被 Jinja JSON 示例解析错误阻断；将双花括号改为普通 JSON 花括号，并新增 Prompt 渲染测试。
- 2026-09-08：旧 InsightAgent 进程未加载 Day4 代码且随后停止；当前执行环境没有继承 DeepSeek API Key 和只读数据库密码，无法非交互重启服务。未尝试读取或输出旧进程中的敏感凭据。
- 2026-09-08：新服务 PID 16972 启动成功并返回 HTTP 200；首轮销售 Web 复验发现客户端即使同时选择数据库和知识库，也可能把 `tool_mode` 标为 `knowledge`，导致仅知识库路由。已将综合模式判断改为以实际数据库连接、知识库和 `insight_agent` 数据库名为准，并增加回归测试（专项 26 passed）。
- 2026-09-08：后续复验发现 Docker Desktop 未运行，数据库 5432 拒绝连接，系统因此降级为知识库模式；启动 Docker Desktop 和现有 `insight-postgres` 容器后，PostgreSQL 恢复为 `accepting connections`。
- 2026-09-08：销售 Web UI 最终复验通过；客户题正确识别 `customer_loss_analysis_tool` 和默认 `2026Q2`，但 DeepSeek 仅输出调用意图、漏写 ReAct Action。增加聚焦业务 Tool 确定性兜底及参数解析的失败关闭规则；全量专项回归 `90 passed, 3 warnings`，Ruff 通过。
- 2026-09-08：重启后在真实 Web UI 使用 DeepSeek 完成销售诊断、客户流失、经销商健康三类验收，三题均直接命中各自原生领域 Tool，答案与 Gold Truth 一致。
- 2026-09-08：经销商答案一度因页面快照显示范围被误判为截断；通过会话历史 API 与重新获取可访问性树确认后端和页面均保存完整答案，无需修改业务代码。
- 2026-09-08：三类 Web UI 截图、原始 Observation 和会话 ID 已归档至 `evidence/day4/`；最终回归为 `90 passed, 3 warnings`，Ruff 全部通过。
- 2026-09-08 19:20 +08:00：Day4 全部 26 个步骤完成；按约定最后生成验收文档，未创建 Git Commit。

# InsightAgent Day 7 V1 验收报告

验收日期：2026-09-10

发布状态：**候选版；Day 7 Pro 首次完整结果和运行态首页均已验收，本报告随唯一 V1 本地提交固化，等待用户发布决策**

## 1. 验收范围

Day 7 只收口 V1：当前仓库 Quick Start、首页品牌、根 README、架构、独立 Pro 复验、代码质量、安全扫描、两套简历和两套详细面试文档。录屏经用户确认移出范围。

## 2. Day 1–Day 7 总体矩阵

| 阶段 | 核心交付 | 结果 |
|---|---|:---:|
| Day 1 | InsightAgent、PostgreSQL、4 表、60,000 条数据、Gold Truth | 通过 |
| Day 2 | 只读数据源、Text-to-SQL、6 制度、RAG | 通过 |
| Day 3 | 销售诊断 Tool 与 SQL+Tool+RAG+HTML 链路 | 通过 |
| Day 4 | 客户流失与经销商健康 Tool，三 Tool 路由 | 通过 |
| Day 5 | 30 条冻结 Benchmark，Pro 基线 26/30 | 通过 |
| Day 6 | SQL 有限恢复、确定性事实和防虚假完成 | 通过 |
| Day 7 | 文档、品牌、独立复验与 V1 发布 | 候选验收通过，待用户发布决策 |

## 3. 数据库和 Quick Start 验收

2026-09-10 在当前仓库清理运行状态后恢复 Docker Desktop 与 `insight-postgres`：

| 检查 | 结果 |
|---|---:|
| PostgreSQL `pg_isready` | accepting connections |
| `dim_region` | 5 |
| `dim_product` | 36 |
| `dim_customer` | 150 |
| `fact_sales` | 60,000 |
| `insight_readonly` SELECT | 成功，60,000 行 |
| `insight_readonly` INSERT | `permission denied`，符合预期 |
| Agent HTTP 首页 | `200 OK` |
| DeepSeek Pro / Flash | 已加载 |
| 本地 BGE Embedding | 已加载 |

发布收口时又发现既有 Day 3 面试文档写入了具体数据库密码，且数据初始化代码存在固定密码默认值。已完成：

- 移除文档中的具体值；
- `INSIGHT_DB_PASSWORD` 未设置时失败关闭；
- 数据初始化脚本用 SecureString 读取 owner/只读密码；
- 新增只读角色幂等配置，授予 CONNECT、USAGE 和 SELECT，默认只读；
- 新增环境变量与角色名校验测试。

## 4. Web 展示层

已完成以下静态改造：

- 标题 `InsightAgent`；
- 副标题“企业经营数据与知识协同分析智能体”；
- 汽车配件场景标识；
- 主 Demo、制度、客户流失和经销商健康度 4 个预设问题；
- 点击预设卡片将问题填入输入框；
- 保留 `Powered by InsightAgent` 与版本致谢。

运行态浏览器已验证标题、副标题、四张业务卡片和 `InsightAgent` 页脚。点击“华东销售下滑诊断”后，完整问题正确填入输入框且未自动发送。

前端构建首先暴露本地依赖将 Monaco 解析到 0.56.0，而仓库锁文件为 0.34.1；已将依赖精确固定到 0.34.1。Next 13 在 Node 24/Windows 上又出现静态 Worker 偶发超时，增加单 Worker 构建配置后完成 56 个页面生产构建和 54 个页面静态导出，并镜像到实际服务目录。全仓 lint 仍受既有 CRLF/Prettier 问题影响；首页相关目标文件单独 ESLint 为 0 error，仅 `pages/index.tsx` 保留一条既有 Hook 依赖 warning。仓库 TypeScript 5.1 在 Node 24 下执行全项目检查时出现编译器自身 `Debug Failure`，不记为本次首页功能通过。

## 5. 自动化质量

| 检查 | 结果 |
|---|---:|
| InsightAgent pytest | **143 passed，0 failed** |
| 上游弃用 warning | 3 |
| Ruff | All checks passed |
| 前端目标文件 ESLint | 0 error，1 条既有 Hook warning |
| Next 生产构建 / 静态导出 | 56/56，54/54 |
| 运行态首页与卡片交互 | passed |
| `git diff --check` | passed |

3 条 warning 来自 Starlette multipart 和 InsightAgent/Pydantic V1 兼容层，不是 InsightAgent 功能失败。

## 6. 历史指标提升

| 指标 | Day 5 Pro 基线 | Day 6 修复候选 |
|---|---:|---:|
| 总任务 | 26/30（86.67%） | 30/30（100%） |
| SQL 执行成功率 | 87.50% | 100% |
| 事实准确率 | 90.00% | 100% |
| 预期 Tool 调用率 | 87.50% | 100% |
| RAG 文档命中率 | 92.31% | 100% |
| 引用章节准确率 | 92.31% | 100% |
| 综合任务 | 6/7（85.71%） | 7/7（100%） |
| 主链路严格九项 | 0/5 | 5/5 |

主要改进链：JOIN/派生表别名预检修复 → SQL 错误分类与一次纠正 → Observation 确定性事实呈现 → 直接领域 Tool 门禁 → 真实事件完成绑定 → 制度定向恢复与 HTML 轮数预算。

## 7. Day 7 Pro 首次独立发布复验

状态：**已完成并冻结，未重跑**。

复验规则：

- 同一冻结 30 题，`deepseek-v4-pro`，temperature 0；
- 每题新会话，数据库/知识库资源按题型隔离；
- 首次完整结果无论高低立即冻结；
- 不改 Gold、题目或判分口径，不选择性重跑；
- 原始轨迹留在本地 results 目录，不提交 Git。

| 指标 | Day 7 首次结果 |
|---|---:|
| Run ID | `day7-pro-all-20260910-release-run1` |
| 总任务 | **28/30（93.33%）** |
| SQL 执行成功率 | **100%** |
| 事实准确率 | **93.33%** |
| 预期 Tool 调用率 | **100%** |
| RAG 文档/章节 | **100% / 100%** |
| 综合任务 | **7/7（100%）** |
| Text-to-SQL | **6/8（75%）** |
| 平均延迟 | **17.78 秒** |
| 失败分类 | `answer_fact_accuracy` × 2 |

与 Day 5 基线相比，首次发布复验总通过率由 86.67% 提升到 93.33%（+6.66 个百分点、+2 题）；SQL 执行率由 87.50% 提升到 100%，事实准确率由 90.00% 提升到 93.33%，Tool 调用率由 87.50% 提升到 100%，RAG 文档/章节由 92.31% 提升到 100%，综合任务由 85.71% 提升到 100%。Day 6 修复候选曾达到 30/30，但 Day 7 独立结果回落，说明 temperature 0 不能消除 Agent 路径波动。

两项失败均保留原始 SSE、SQL 和判分记录：

1. `v1-dev-sql-05`：SQL 正确返回毛利率变化 `-2.7839` 个百分点，但回答没有同时呈现 Gold 要求的 Q1 `28.91%` 与 Q2 `26.13%`，属于最终事实字段不完整。
2. `v1-test-sql-07`：主要渠道“经销商”和下降金额 `395,312.25` 元正确；SQL 以“所有下降渠道之和”为分母得到 `73.99%`，Gold 以“区域净下降”为分母要求 `74.89%`，属于贡献率口径不一致。

发布结论不是“模型退化”或“系统失败”：领域 Tool、制度 RAG、章节引用和全部综合任务保持 100%；但 Text-to-SQL 自由生成仍需用指标字典、结构化输出 Schema 和口径级断言继续收敛。按照发布前承诺，本次不修改 Gold、不补跑，也不以 Day 6 的峰值覆盖 Day 7 首次结果。

## 8. 文档交付

- [x] 根 README 改造为 InsightAgent 项目首页；
- [x] 独立架构与源码调用链；
- [x] 私企 Agent 开发岗项目简历；
- [x] 央国企 AI 岗项目简历；
- [x] 私企 Agent 开发岗完整面试文档；
- [x] 央国企 AI 岗完整面试文档；
- [x] Day 7 执行、进度和验收文档。

## 9. 发布决策

Day 7 Pro 复验、运行态 Web 验收和本地 V1 收口均已完成。提交完成后将 Commit ID、最终工作区状态和全部验收结果交给用户；只有用户明确确认，才推送 GitHub 并创建/推送 `insight-agent-v1.0.0` Tag。

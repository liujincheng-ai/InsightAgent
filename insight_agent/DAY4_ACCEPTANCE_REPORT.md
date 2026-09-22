# InsightAgent Day 4 验收报告

验收日期：2026-09-08
验收结论：**通过**
代码提交：按要求**未创建 Git Commit**

## 1. 验收范围与完成结果

Day 4 在 Day 3 销售诊断能力基础上，完成了客户流失预警和经销商健康度分析，
并把三个领域 Tool 接入 InsightAgent 原生 ReAct Agent。最终形成以下能力：

1. `sales_diagnosis_tool`
   - 查询指定区域、品类和季度的销售额、同比、环比和毛利率变化。
   - 输出产品与渠道下降贡献，支持销售诊断和综合经营报告。
2. `customer_loss_analysis_tool`
   - 按客户比较当前季度和上一季度。
   - 识别停止采购或大幅下滑预警，计算客户对区域净下降的贡献。
   - 支持按 A 级客户过滤展示，且明确“风险预警不等于确认流失”。
3. `dealer_health_analysis_tool`
   - 按销售变化、采购活跃度、折扣和毛利四个维度评分。
   - 输出健康度、风险等级和逐项扣分原因。
   - 明确评分分段属于 `insight-agent-v1-demo`，不是公司制度原文或行业标准。
4. 原生 Agent 集成
   - 三个 Tool 统一注册到 InsightAgent `ResourceManager`。
   - 根据问题意图选择正确的首个领域 Tool，避免通用工具绕过业务契约。
   - 聚焦问题允许直接返回；要求制度、建议或完整报告的问题继续执行知识检索和报告流程。
   - 制度章节按问题动态映射，不再把“经销商制度 4.2 节”强制用于所有问题。
5. 稳定性与安全边界
   - 数据库访问沿用短连接、参数化 SQL 和只读校验。
   - 缺少季度时使用当前数据集最新完整季度 `2026Q2`，基准期为 `2026Q1`。
   - DeepSeek 未生成合法 ReAct Action 时，仅允许通过同一受控 ToolPack 执行已选中的原生领域 Tool；参数解析失败时关闭失败，不猜测数据库事实。

详细业务口径见 [DAY4_RULES.md](DAY4_RULES.md)，运行方法见 [DAY4.md](DAY4.md)。

## 2. 关键业务口径

### 2.1 客户流失预警

- 当前期与基准期：请求季度与其上一季度。
- 停止采购预警：基准期有销售、当前期无销售。
- 大幅下滑预警：当前期销售下降率达到配置阈值，默认 50%。
- 下降贡献：客户正向下降额 / 区域品类净下降额。
- 如果区域没有净下降，贡献率返回空值，不制造零或无穷值。
- 交易数据只能产生风险预警；确认流失仍需核对沟通、库存、价格和售后事实。

### 2.2 经销商健康度

总分 100 分，由销售变化 40 分、采购活跃度 20 分、折扣 20 分和毛利 20 分组成。
折扣阈值来自价格制度；其余评分区间及风险分段是版本化的 V1 演示规则。结果用于确定
调查优先级，不替代客户核验、经销商等级调整或审批。

## 3. 自动化验收

| 检查项 | 结果 |
|---|---:|
| 公共 Day 4 指标测试 | 29 passed |
| 客户流失 Tool 测试 | 7 passed |
| 经销商健康 Tool 测试 | 8 passed |
| 路由及相关集成测试 | 35 passed |
| InsightAgent 全量专项回归 | **90 passed, 3 warnings** |
| Ruff 代码质量检查 | **All checks passed** |

三条 warning 来自现有第三方依赖的弃用提示：pytest-asyncio、Starlette multipart 兼容层
和 Pydantic 兼容层；最终测试没有 Day 4 失败项。完整结果见
[automated-test-results.txt](evidence/day4/automated-test-results.txt)。

## 4. 真实数据库与 Web UI 验收

真实 PostgreSQL 查询结果与冻结的
[day4_gold_truth.json](data/gold/day4_gold_truth.json) 一致；只读角色具备 SELECT 权限，
不具备 INSERT、UPDATE 或 DELETE 权限。数据库验证记录见
[real-db-results.json](evidence/day4/real-db-results.json)。

真实 InsightAgent Web UI 使用 `insight_agent` 数据库、汽车配件企业制度库和 DeepSeek 模型完成：

| 场景 | 会话 ID | 首个 Tool | 核心结果 | 验收 |
|---|---|---|---|:---:|
| 销售诊断 | `892ba2dc-c402-463a-a416-5015a5e4e027` | `sales_diagnosis_tool` | 销售额 1,087,378.79 元；环比 -32.68%；同比 -29.27%；经销商下降贡献 74.89% | 通过 |
| 客户流失 | `fc736f6f-8b62-460b-8af1-6cca3b6653e5` | `customer_loss_analysis_tool` | 净下降 527,845.50 元；7 个风险客户；A级客户 Top 3 与 Gold Truth 一致 | 通过 |
| 经销商健康 | `2e6bfd82-6282-45c5-8c5c-497df59b1ce2` | `dealer_health_analysis_tool` | 一号 62/100、medium；销售/折扣/毛利分别扣 28/6/4 分 | 通过 |

结构化 UI 验收清单见 [web-ui-results.json](evidence/day4/web-ui-results.json)。

截图：

- [销售诊断 Web 截图](evidence/day4/web-sales.png)
- [客户流失 Web 截图](evidence/day4/web-customer-loss.png)
- [经销商健康 Web 截图](evidence/day4/web-dealer-health.png)

原始 Tool 输出：

- [销售诊断 Observation](evidence/day4/web-sales-tool-output.json)
- [客户流失 Observation](evidence/day4/web-customer-loss-tool-output.json)
- [经销商健康 Observation](evidence/day4/web-dealer-health-tool-output.json)

## 5. 遇到的问题与解决方案

| 问题 | 根因 | 解决方案与验证 |
|---|---|---|
| Gold Truth 首次查询失败 | 容器中不存在默认 `postgres` 角色 | 使用容器声明的 `insight` 用户执行只读查询，未读取或输出密码；结果已冻结并复核 |
| Day 3 制度用例一度回归 | 重构 Prompt 时遗漏原有 4.2 节约束 | 先恢复回归，再把制度引用改为按意图动态映射；新增换题测试，避免无关问题仍被强制命中 4.2 |
| Ruff 首轮报告 11 个行长问题 | 新增 Prompt 和测试断言过长 | 拆分字符串和断言，修正测试迭代写法；最终 Ruff 全部通过 |
| 测试出现 `.items()` 迭代错误 | 测试把序列当作映射处理 | 按真实返回结构修正迭代逻辑并重新执行全量测试 |
| 首轮销售 Web 问题误选 `execute_tool` 并产生虚构值 | UI 资源前缀中的“制度”触发完整报告误判，同时暴露了间接工具入口 | 路由前先剥离资源前缀；集成模式移除通用 `execute_tool`/`load_tools`；给三个领域 Tool 增加精确 Action/Input 契约 |
| 第二轮 Web 执行被 Jinja 解析错误阻断 | Prompt 中 JSON 示例使用了双花括号 | 改为普通 JSON 花括号，并增加 Prompt 渲染测试 |
| 同时选择数据库和知识库却进入知识库模式 | 客户端可能仍发送 `tool_mode=knowledge` | 后端以实际数据库连接、知识库和 `insight_agent` 数据库名识别集成模式，并增加回归测试 |
| 重启后数据库连接被拒绝 | Docker Desktop 与 `insight-postgres` 容器未运行 | 启动 Docker Desktop 和原容器，使用 `pg_isready` 验证 PostgreSQL 恢复 |
| 未写季度的问题被模型选成 2025Q1 | LLM 自由补全缺失时间参数 | 在受控参数解析中固定缺省为数据集最新完整季度 `2026Q2`，基准期自动推导为 `2026Q1` |
| DeepSeek 有时只输出 Tool 调用意图，不输出合法 Action | 模型 ReAct 格式不稳定 | 在同一 `SalesDiagnosisFirstToolPack` 内增加确定性兜底：只执行路由已选中的原生 Tool，并用确定性格式化器展示已验证 Observation |
| 经销商答案看似被截断 | 当时页面快照只返回可见范围，后端持久化内容实际完整 | 使用会话历史 API 和重新获取页面可访问性树双重核验；完整答案已在 Web UI 和截图中确认，无需修改业务数据逻辑 |
| 一次 UI 选择命中了知识搜索容器 | 页面元素 ID 在刷新后变化 | 丢弃该无效会话，重新按可访问性树选择数据库和知识库资源后复验 |

## 6. 已知边界

- 当前数据为项目合成数据，不包含回款、投诉、联系人沟通、库存或审批记录。
- 客户结果是交易异常预警，不是确认流失名单。
- 经销商健康度权重与部分阈值是 `insight-agent-v1-demo`，上线前需要业务评审、历史回测、版本审计和阈值稳定性分析。
- 当前验收覆盖单轮聚焦问题和现有综合报告路径；生产环境还应补充并发、长时间运行、权限隔离和真实业务标签评估。

## 7. Day 4 高频面试题与参考回答

### 1）为什么拆成三个领域 Tool，而不是一个万能 Tool？

三个场景的输入、输出和错误语义不同。拆分可以缩小模型 Action Space、提高工具选择准确率，
也便于独立测试；季度解析、安全除法等公共逻辑仍复用，不造成基础代码复制。

### 2）为什么不直接把风险客户叫作“已流失客户”？

订单数据只能证明停止采购或大幅下滑，不能证明合作关系结束。系统区分数据事实、风险
预警和人工确认，避免模型把相关性包装成已确认的业务结论。

### 3）客户下降贡献度怎样计算？

客户下降贡献度 = 客户正向下降额 / 区域品类净下降额。分母采用区域净下降是为了反映
增长客户抵消后的真实经营缺口；没有净下降时返回空值并说明口径。

### 4）为什么比较上一季度，而不是让模型自由选基准期？

固定基准期能保证同一问题结果可复现、可建立 Gold Truth，也符合季度经营监控目标。
如果业务需要同比或滚动 12 个月，应显式扩展 Tool 参数和契约。

### 5）经销商评分为什么使用规则而不是机器学习？

当前没有真实的违约、流失或恶化标签，机器学习无法可靠训练和评估。规则评分可解释、
可复现、能展示扣分原因；获得真实标签后再与模型比较召回率、准确率、校准度和干预收益。

### 6）如何防止大模型调用错误 Tool 或编造数字？

先用确定性路由限定首个领域 Tool，再用 ToolPack 校验工具顺序、参数和重复调用；所有数字
必须来自 SQL 或领域 Tool Observation。模型 ReAct 格式失败时，也只允许调用路由已选定的
原生 Tool，不允许自由生成数据库结果。

### 7）为什么“必须命中经销商制度 4.2 节”不能写成全局约束？

它只对特定经销商整改流程有效。全局硬编码会让换题后仍检索无关条款，降低答案相关性。
正确方式是先识别销售、客户流失或经销商健康意图，再映射对应制度和章节，并通过换题
回归测试验证约束仍有效。

### 8）加权毛利率为什么不能平均每笔毛利率？

订单金额不同，简单平均会放大小额订单影响。项目使用总毛利除以总销售额的加权毛利率；
销售额为零时返回空值，不伪造 0% 毛利率。

### 9）怎样保证 SQL 安全？

业务 Tool 使用固定参数化 SQL 和短生命周期只读连接；通用 SQL 入口执行单语句 SELECT
校验；数据库角色没有写权限。应用校验和数据库最小权限共同形成纵深防御。

### 10）你怎样证明 Agent 集成真的工作，而不是只测 Python 函数？

验收分两层：自动化测试验证指标、Tool 契约和路由；真实 Web UI 使用 DeepSeek、实际
PostgreSQL 与知识库执行三个代表性问题，并保存会话 ID、截图和原始 Observation，结果
与 Gold Truth 逐项对比。

更多追问与扩展回答见
[DAY4_INTERVIEW_GUIDE_DETAILED.md](DAY4_INTERVIEW_GUIDE_DETAILED.md)。

## 8. 复验命令

```powershell
.\.venv\Scripts\python.exe -m pytest tests\insight_agent -q
.\.venv\Scripts\ruff.exe check insight_agent\tools insight_agent\agent tests\insight_agent packages\dbgpt-app\src\dbgpt_app\openapi\api_v1\agentic_data_api.py packages\dbgpt-app\src\dbgpt_app\component_configs.py
```

## 9. 最终结论

Day 4 计划中的 26 个步骤均已完成。两个新增领域 Tool、三类动态路由、只读数据访问、
确定性兜底、自动化回归、真实 Web UI 验收、证据归档和面试指南均满足本次验收目标。
在明确保留 V1 演示评分和合成数据限制的前提下，本版本可作为 Day 4 学习与演示成果验收通过。

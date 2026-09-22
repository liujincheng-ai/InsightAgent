# Week 1：Text-to-SQL 语义正确性

## 目标

在 Day 7 可运行 V1 之上，把 Text-to-SQL 从“SQL 能执行”推进到“业务口径、结果事实和歧义处理可验证”。本周工作量约等于此前 3–4 个完整开发日，按一个连续迭代统一交付。

## 完成定义

1. 建立可版本化业务词典，覆盖销售额、销量、加权毛利率、同比/环比、下降贡献、活跃经销商和加权折扣率。
2. 明确交易区域与客户所属区域、日期边界、Join 和去重语义。
3. 对会改变经营结论的歧义先澄清，且澄清前不执行 SQL。
4. 建立 18 dev + 8 test + 4 challenge 的冻结评测集，Gold 结果由固定 CSV 数据确定性生成。
5. 分离 SQL 执行、严格结果集、答案事实、歧义处理和澄清前不查库五类指标。
6. 提供 `baseline/comments/glossary/combined` 四种配置，支持消融分析。
7. 唯一一次 Pro 最终运行冻结，不因结果不理想而补跑或选择性修复。
8. 形成完整验收文档和面试文档。

## 执行顺序

1. 复盘 Day 7 两个 Text-to-SQL 失败并抽象为通用问题。
2. 建设 YAML 业务词典、指标文档和歧义规则。
3. 创建只读语义视图并接入数据库初始化脚本。
4. 将语义选择、预检、澄清门禁和确定性呈现接入真实 ReAct API。
5. 构建并冻结 Week 1 数据集、评分器、运行器和重评分工具。
6. 执行 Flash 探索/消融，dev 阶段仅做通用修复。
7. 执行且只执行一次 Pro 全量最终评测，冻结原始轨迹。
8. 完成自动化回归、README/架构更新、验收报告和面试材料。

## 不做事项

- 不针对单道 test/challenge 题硬编码 SQL 或答案。
- 不把 SQL 可执行率当作语义准确率。
- 不把小样本 90% 外推为生产准确率。
- 不在查看 Pro 最终失败后继续调参并覆盖“最终”结果。
- 不提交本地结果目录、密钥或数据库密码。

## 交付物

- `semantic/`：业务词典、指标与歧义规则。
- `database/views.sql`、`database/apply_views.py`：语义视图。
- `evaluation/dataset/sql_semantic_*.json`：冻结数据集。
- `evaluation/run_semantic_eval.py`、`semantic_metrics.py`、`rescore_semantic.py`：评测链路。
- `WEEK1_ACCEPTANCE_REPORT.md`：完整验收证据。
- `WEEK1_INTERVIEW_GUIDE_DETAILED.md`：完整面试文档。


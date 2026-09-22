# InsightAgent Week 1 Text-to-SQL 语义评测

该评测用于区分“SQL 能执行”和“业务答案正确”。数据集为 18 条 dev、8 条 test 和 4 条 challenge，分别测试普通语义、冻结泛化与高风险歧义。

## 运行

```powershell
.\.venv\Scripts\python.exe -m insight_agent.evaluation.build_week1_dataset
.\.venv\Scripts\python.exe -m insight_agent.evaluation.run_semantic_eval --split all --profile combined --model deepseek-v4-pro --temperature 0 --timeout 120 --output-dir insight_agent/evaluation/results/<new-run-id>
```

输出包含每题 `raw/*.json`、`records.json`、`summary.json`、`summary.csv` 和 `run_manifest.json`。输出目录非空时程序拒绝覆盖。

## 配置

| Profile | 注入内容 |
|---|---|
| `baseline` | 不注入 Week 1 语义内容 |
| `comments` | Schema 和字段说明 |
| `glossary` | 指标定义与歧义规则 |
| `combined` | comments + glossary |

需要澄清的问题在本轮不提供 SQL Tool，因此可以直接测量“澄清前不查库”。评分分别报告 SQL 执行、严格结果集、答案事实、歧义处理和不查库率。

## 冻结最终结果

DeepSeek V4 Pro、temperature 0、combined、30 题的唯一最终运行是 27/30（90%）。SQL 执行、歧义处理和澄清前不查库均为 100%；严格结果集为 76.92%，答案事实为 88.46%。详细边界和三个失败见 `insight_agent/WEEK1_ACCEPTANCE_REPORT.md`。


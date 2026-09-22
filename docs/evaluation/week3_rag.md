# Week 3 RAG 评测说明

## 运行入口

构建并校验冻结集：

```powershell
.\.venv\Scripts\python.exe -m insight_agent.evaluation.build_week3_dataset
```

运行 54 组开发集检索矩阵：

```powershell
.\scripts\windows\run_week3_rag.ps1 -Split dev -RunPrefix <new-prefix>
```

运行单组检索或答案评测：

```powershell
.\.venv\Scripts\python.exe -m insight_agent.evaluation.run_rag_eval `
  --mode answer --retriever vector --chunk-size 512 --chunk-overlap 50 `
  --top-k 5 --query-strategy decompose --split dev `
  --model deepseek-v4-flash --output-dir <new-output-dir>
```

结果目录必须为空或不存在。每次运行保存 `records.json`、`summary.json`、
`run_manifest.json` 和逐题 `raw/*.json`；不得覆盖旧运行。

## 评分合同

- 文档与章节命中只对 `should_answer=true` 的题统计。
- MRR 取第一个 Gold 文档或章节的倒数排名。
- Citation Precision 要求 Claim 引用的文档/章节确实出现在检索 Context，且证据短句
  可以在对应 Chunk 原文定位。
- 无答案题必须设置 `insufficient_evidence=true`、包含明确拒答语句且 `claims=[]`。
- 伪造引用指引用了本次检索 Context 中不存在的文档/章节。
- 自动事实分数采用预登记的 `accepted_values` 字符串匹配；语义等价假阴性单独人工
  裁决，不能改写原始模型输出。

## 最终配置与结果

冻结配置见 `insight_agent/evaluation/week3_final_config.json`。唯一 Pro 全量运行的
检索结果为 Document Hit@5 100%、MRR 98.10%；引用精度 100%、拒答 5/5、伪造
引用 0。自动事实准确率 81.90%，人工逐题复核为 92.86%。详细边界与失败列表见
`insight_agent/WEEK3_ACCEPTANCE_REPORT.md`。

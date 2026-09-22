# csv-data-analysis

## 概览

`csv-data-analysis` 是一个面向 CSV、Excel 和 TSV 文件的内置深度分析 skill。

它把统计提取、异常发现、图表数据准备和 HTML 报告生成整合在一起。

## 仓库路径

```text
skills/csv-data-analysis/
├── SKILL.md
├── scripts/
│   └── csv_analyzer.py
├── references/
│   └── reference.md
└── templates/
    └── report_template.html
```

## 适用场景

- 分析上传的 CSV 文件
- 分析 Excel 工作簿
- 计算统计指标并发现异常
- 生成更完整、可交互的数据分析报告

## 核心工作流

1. 使用 `execute_skill_script_file` 运行 `scripts/csv_analyzer.py`。
2. 读取返回的统计摘要结果。
3. 配合 `html_interpreter` 使用 `csv-data-analysis/templates/report_template.html`。
4. 只填写模板要求的文本占位部分。
5. 让后端自动注入图表 marker 数据。

## 关键资源

| 资源 | 作用 |
|---|---|
| `scripts/csv_analyzer.py` | 提取统计信息、数据质量信号和图表 marker 数据 |
| `references/reference.md` | skill 的补充使用说明 |
| `templates/report_template.html` | 最终交互式报告模板 |

## 输出预期

这个 skill 的目标是生成一份包含以下内容的分析报告：

- 执行摘要
- 数据质量评估
- 分布分析
- 相关性分析
- 类别与结构分析
- 异常概览
- 结论与建议

## 说明

模板本身属于 skill 契约的一部分。智能体应优先使用 skill 自带的 HTML 模板，而不是手写一套新的报告渲染逻辑。

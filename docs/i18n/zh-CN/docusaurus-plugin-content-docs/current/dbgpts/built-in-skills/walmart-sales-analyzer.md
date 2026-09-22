# walmart-sales-analyzer

## 概览

`walmart-sales-analyzer` 是一个面向 Walmart 销售数据集的内置分析 skill。

它重点分析周销售额与失业率之间的关系趋势，并最终生成一份面向业务场景的 HTML 报告。

## 仓库路径

```text
skills/walmart-sales-analyzer/
├── SKILL.md
├── scripts/
│   ├── generate_html_report.py
│   ├── generate_correlation_heatmap.py
│   ├── generate_sales_unemployment_scatter.py
│   ├── generate_time_series_trend.py
│   ├── generate_store_avg_comparison.py
│   └── font_setup.py
└── templates/
    └── report_template.html
```

## 适用场景

- 分析 Walmart 销售 CSV 数据
- 研究销售额与失业率之间的关系
- 生成对比图表与趋势图
- 输出适合业务阅读的 HTML 报告

## 核心工作流

1. 先校验上传文件是否属于 Walmart 销售数据。
2. 运行 `generate_html_report.py` 或相关图表脚本。
3. 将分析文本和标题传给 `html_interpreter`。
4. 使用 skill 自带模板渲染最终报告。

## 关键资源

| 资源 | 作用 |
|---|---|
| `scripts/generate_html_report.py` | 端到端报告生成入口 |
| `scripts/generate_correlation_heatmap.py` | 相关性热力图 |
| `scripts/generate_sales_unemployment_scatter.py` | 销售额与失业率回归散点图 |
| `scripts/generate_time_series_trend.py` | 门店时间序列趋势图 |
| `scripts/generate_store_avg_comparison.py` | 门店平均值对比 |
| `templates/report_template.html` | 最终响应式报告模板 |

## 输出预期

这个 skill 重点强调：

- 趋势的可视化解释
- 面向业务的分析解读
- 区域与门店对比
- 执行摘要与建议结论

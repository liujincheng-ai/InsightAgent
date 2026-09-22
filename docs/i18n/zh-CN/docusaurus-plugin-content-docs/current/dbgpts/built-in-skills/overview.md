# Built-in Skills 总览

InsightAgent 在项目级 `skills/` 目录下内置了一批可直接使用的 skills。

这个小节按照仓库结构组织，为每一个 built-in skill 提供单独页面说明。

## 仓库映射

```text
skills/
├── agent-browser/
├── csv-data-analysis/
├── financial-report-analyzer/
├── skill-creator/
└── walmart-sales-analyzer/
```

## Built-in skills 提供什么能力

Built-in skill 会把可重复工作流打包成可复用单元。

- `SKILL.md` 定义 skill 应该何时使用、如何执行
- `scripts/` 存放在需要确定性处理时用到的可执行脚本
- `references/` 存放按需加载的领域参考资料
- `templates/` 或 `assets/` 存放 HTML 报告模板等输出资源

## 当前内置 skills

| Skill | 主要用途 | 关键资源 |
|------|----------|----------|
| `agent-browser` | 面向 agent 的浏览器自动化 | `SKILL.md` 中的命令式工作流 |
| `csv-data-analysis` | CSV / Excel / TSV 数据分析 | `scripts/csv_analyzer.py`、`templates/report_template.html`、`references/reference.md` |
| `financial-report-analyzer` | 财报提取、分析与报告生成 | 提取、比率分析、图表脚本，以及财务参考资料与模板 |
| `skill-creator` | 创建并打包新的 skill | `init_skill.py`、`package_skill.py`、设计参考资料 |
| `walmart-sales-analyzer` | Walmart 销售趋势分析与报告 | 报告生成脚本与 `templates/report_template.html` |

## 如何阅读这一节

每个 built-in skill 页面通常会包含：

- skill 的用途
- 适用场景
- 核心工作流
- 附带的重要脚本、参考资料与模板
- 预期输出形式

## 下一步

继续打开本小节下的具体页面，查看每个已内置 skill 如何映射到仓库中的 `skills/` 目录。

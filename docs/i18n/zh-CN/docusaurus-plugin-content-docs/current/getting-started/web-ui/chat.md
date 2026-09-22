---
sidebar_position: 1
title: 聊天
---

# 聊天

InsightAgent 在 Web UI 中提供了多种聊天模式，每种模式都针对不同的使用场景进行了设计。

## 聊天模式

| 模式 | 说明 | 要求 |
|---|---|---|
| **Chat Normal** | 与 LLM 进行通用对话 | 已配置 LLM |
| **Chat Data** | 对 SQL 数据库发起自然语言查询（Text2SQL） | 已连接数据库 |
| **Chat Excel** | 上传并查询 Excel/CSV 文件 | 已配置 LLM |
| **Chat Knowledge** | 基于文档的 RAG 对话 | 已创建知识库 |

## 开始对话

1. 打开 Web UI：**[http://localhost:5670](http://localhost:5670)**
2. 点击侧边栏中的 **Chat**
3. 从下拉菜单中选择聊天模式，或新建一个会话
4. 输入消息并按 Enter

:::tip 快速测试
建议先从 **Chat Normal** 开始，确认 LLM 工作正常后，再尝试其他模式。
:::

## Chat Normal

默认模式，直接与已配置的 LLM 对话。

**功能特点：**
- 支持多轮对话与上下文保持
- 支持 Markdown 格式渲染
- 支持代码高亮
- 支持流式响应

## Chat Data (Text2SQL)

你可以使用自然语言查询已连接的数据库。InsightAgent 会将问题转换为 SQL，执行查询，并展示结果。

**使用方式：**

1. 先在侧边栏的 **Database** 区域连接数据库
2. 新建一个 **Chat Data** 会话
3. 从下拉菜单中选择目标数据库
4. 使用自然语言提问

**示例：**

```
User: Show me the top 10 customers by total order amount
InsightAgent: [生成 SQL，执行后以表格形式展示结果]
```

:::info 支持的数据库
包括 MySQL、PostgreSQL、SQLite、ClickHouse、DuckDB、MSSQL、Oracle 等。完整列表请参考 [Data Sources](/docs/getting-started/concepts/data-sources)。
:::

## Chat Excel

上传 Excel 或 CSV 文件，并使用自然语言对其进行查询。

**使用方式：**

1. 新建一个 **Chat Excel** 会话
2. 上传文件（`.xlsx`、`.xls` 或 `.csv`）
3. 针对数据提问

**示例：**

```
User: What is the average sales amount per region?
InsightAgent: [分析文件并展示结果]
```

## Chat Knowledge

对话式 RAG：围绕你上传的文档进行提问，并获得有依据的回答。

**使用方式：**

1. 先创建知识库并上传文档（参考 [Knowledge Base](/docs/getting-started/web-ui/knowledge-base)）
2. 新建一个 **Chat Knowledge** 会话
3. 从下拉菜单中选择知识库
4. 开始提问

**功能特点：**
- 回答会引用来源文档
- 支持多种文件格式（PDF、Word、Markdown、TXT 等）
- 结合向量检索与 LLM 生成能力

## 会话管理

- **History**：历史会话会保存在侧边栏中
- **Delete**：右键某个会话即可删除
- **Export**：可从聊天窗口中复制会话内容

## 下一步

| 主题 | 链接 |
|---|---|
| 为 Chat Knowledge 配置知识库 | [Knowledge Base](/docs/getting-started/web-ui/knowledge-base) |
| 为 Chat Data 连接数据库 | [Data Sources](/docs/getting-started/concepts/data-sources) |
| 构建自定义对话工作流 | [AWEL Flow](/docs/getting-started/tools/awel-flow) |

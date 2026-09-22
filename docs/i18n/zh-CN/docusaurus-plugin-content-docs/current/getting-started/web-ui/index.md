---
sidebar_position: 0
title: Web UI 总览
summary: "了解 InsightAgent Web UI 中有哪些主要能力，以及它们分别在哪里"
read_when:
  - 你已经启动了 InsightAgent，想知道先点哪里
  - 你想快速了解 chat、knowledge、dashboard 和 app 界面的分布
---

# Web UI 总览

InsightAgent 默认自带 Web 界面，地址为 **[http://localhost:5670](http://localhost:5670)**。

## 主要区域

- [Chat](/docs/getting-started/web-ui/chat) —— 普通对话、数据对话、Excel 对话、知识库对话
- [Knowledge Base](/docs/getting-started/web-ui/knowledge-base) —— 上传文件并构建 RAG 数据集
- [Dashboard](/docs/getting-started/web-ui/dashboard) —— 从自然语言生成图表和报告
- [App Management](/docs/getting-started/web-ui/app-management) —— 创建和管理 InsightAgent 应用

## 功能地图

| 功能 | 描述 | 所在区域 |
|---|---|---|
| **Chat** | 与 LLM 进行多轮对话 | [Chat](/docs/getting-started/web-ui/chat) |
| **Chat Data** | 基于已连接数据库进行自然语言问数（Text2SQL） | [Chat](/docs/getting-started/web-ui/chat) |
| **Chat Excel** | 上传并用自然语言分析 Excel 文件 | [Chat](/docs/getting-started/web-ui/chat) |
| **Chat Knowledge** | 基于上传文档做 RAG 对话 | [Knowledge Base](/docs/getting-started/web-ui/knowledge-base) |
| **Dashboard** | 自动生成图表和数据报告 | [Dashboard](/docs/getting-started/web-ui/dashboard) |
| **App Store** | 浏览并安装社区应用 | [App Management](/docs/getting-started/web-ui/app-management) |
| **AWEL Flow** | 可视化工作流编辑器 | [AWEL Flow](/docs/getting-started/tools/awel-flow) |
| **Agent Workspace** | 配置并运行多智能体任务 | [App Management](/docs/getting-started/web-ui/app-management) |

## 访问 Web UI

启动 InsightAgent 服务后，可以通过以下地址访问 Web UI：

```
http://localhost:5670
```

:::tip 单独运行前端
如果你要做前端开发，也可以单独运行 Next.js 应用：

```bash
cd web && npm install
cp .env.template .env
# 设置 API_BASE_URL=http://localhost:5670
npm run dev
```

然后访问 [http://localhost:3000](http://localhost:3000)。
:::

## 建议先尝试什么

1. 打开 **Chat**，确认配置的模型能正常回复
2. 如果你想做文档问答，打开 **Knowledge Base**
3. 如果你想做 Text2SQL 和图表分析，打开 **Dashboard**
4. 如果你想复用应用配置，打开 **Apps**

## 下一步

| 主题 | 链接 |
|---|---|
| 开始聊天 | [Chat](/docs/getting-started/web-ui/chat) |
| 搭建知识库 | [Knowledge Base](/docs/getting-started/web-ui/knowledge-base) |
| 构建工作流 | [AWEL Flow](/docs/getting-started/tools/awel-flow) |

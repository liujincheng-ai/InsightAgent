---
sidebar_position: 4
title: 应用管理
---

# 应用管理

在 InsightAgent 中创建、配置并管理 AI 应用。应用会将 LLM、工具、知识库与工作流组合成可复用的配置。

## 应用类型

| 类型 | 说明 |
|---|---|
| **Native App** | InsightAgent 内置应用 |
| **Community App** | 来自 dbgpts 社区仓库的应用 |
| **Custom App** | 你基于 Agent 和 AWEL 自定义构建的应用 |

## 浏览应用

### App Store

1. 点击侧边栏中的 **Apps**
2. 浏览可用应用
3. 点击某个应用查看详情，包括说明、所需资源和配置信息

### 已安装应用

**My Apps** 标签页会显示你已安装或已创建的应用。

## 创建应用

### 第一步：定义应用

1. 进入 **Apps** → **Create**
2. 填写以下信息：
   - **Name**：应用显示名称
   - **Description**：应用功能说明
   - **Language**：Prompt 使用的自然语言（例如英文、中文）

### 第二步：配置资源

为应用添加所需资源：

- **LLM**：选择语言模型
- **Knowledge Base**：为 RAG 绑定一个或多个知识库
- **Database**：连接用于 Text2SQL 的数据源
- **Tools**：添加外部工具（MCP 工具、自定义函数等）

### 第三步：设置 Agent

对于多 Agent 应用：

1. 选择 Agent 团队模式：
   - **Single Agent**：由单个 Agent 处理所有任务
   - **Auto-Plan**：多个 Agent 自动协作并规划任务
   - **Sequential**：多个 Agent 按固定顺序执行

2. 配置每个 Agent：
   - **Role**：Agent 的角色设定与专长
   - **Prompt**：系统指令
   - **Resources**：该 Agent 可访问的工具与数据

### 第四步：测试与部署

1. 点击 **Save** 保存配置
2. 使用 **Test** 在沙箱环境中测试应用
3. 应用会出现在 **My Apps** 列表中，供后续使用

## 管理应用

| 操作 | 说明 |
|---|---|
| **Edit** | 点击任意应用卡片上的编辑图标 |
| **Delete** | 点击删除图标（仅自定义应用可删除） |
| **Share** | 导出应用配置用于分享 |
| **Duplicate** | 复制现有应用作为新应用起点 |

## AWEL Flow 集成

应用可以使用 AWEL 工作流作为执行引擎：

1. 在 **Flow** 编辑器中创建工作流
2. 创建应用时，将该 AWEL Flow 选为应用后端
3. 应用 UI 会自动映射该 Flow 的输入与输出

关于工作流构建的更多说明，请参考 [AWEL Flow](/docs/getting-started/tools/awel-flow)。

## 社区应用（dbgpts）

你可以使用 `dbgpts` CLI 安装社区贡献的应用：

```bash
# 列出可用应用
dbgpts list-remote

# 安装应用
dbgpts install <app-name>
```

:::info
社区应用维护在 [dbgpts repository](https://github.com/eosphoros-ai/dbgpts) 中。更多信息请参考 [dbgpts](/docs/getting-started/tools/dbgpts)。
:::

## 下一步

| 主题 | 链接 |
|---|---|
| 构建工作流 | [AWEL Flow](/docs/getting-started/tools/awel-flow) |
| 了解 Agent | [Agents Concept](/docs/getting-started/concepts/agents) |
| 社区应用 | [dbgpts](/docs/getting-started/tools/dbgpts) |
| 应用开发指南 | [App Development](/docs/cookbook/app/data_analysis_app_develop) |

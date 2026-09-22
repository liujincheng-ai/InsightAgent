---
sidebar_position: 2
title: dbgpts 生态
---

# dbgpts 生态

**[dbgpts](https://github.com/eosphoros-ai/dbgpts)** 是 InsightAgent 官方的社区组件仓库，包含可复用的应用、AWEL 算子、工作流模板以及 Agent。

## dbgpts 中包含什么？

| 组件类型 | 说明 | 示例 |
|---|---|---|
| **Apps** | 可直接安装的完整应用 | 数据分析应用、报告生成器 |
| **Operators** | 可在工作流中使用的 AWEL 算子 | 文本切分、HTTP 请求、LLM 调用 |
| **Workflow Templates** | 预构建的 AWEL 工作流 DAG | RAG 流程、多 Agent 对话 |
| **Agents** | 预配置的 Agent 定义 | SQL 分析师、代码审查助手 |

## 安装

当你安装带有 `dbgpts` extra 的 InsightAgent 时，会同时安装 `dbgpts` CLI：

```bash
uv sync --all-packages --extra "dbgpts" ...
```

## CLI 命令

### 浏览可用包

```bash
# 列出所有远程包
dbgpts list-remote

# 列出已安装的包
dbgpts list
```

### 安装包

```bash
dbgpts install <package-name>
```

### 更新包

```bash
dbgpts update <package-name>
```

### 卸载包

```bash
dbgpts uninstall <package-name>
```

## 在 Web UI 中使用

安装完成后，dbgpts 组件会自动出现在 Web UI 中：

- **Apps** 会出现在 App Store 中
- **Operators** 会出现在 AWEL Flow 编辑器的算子面板中
- **Workflow templates** 可以导入到 Flow 编辑器中
- **Agents** 可以在创建多 Agent 应用时直接选择

## 仓库结构

dbgpts 仓库按照组件类型进行组织：

```
dbgpts/
├── apps/           # 完整应用
├── operators/      # AWEL 算子
├── workflow/       # 工作流模板
└── agents/         # Agent 定义
```

## 创建你自己的 dbgpts 包

你也可以向这个生态贡献自己的组件：

1. 遵循 [dbgpts repository](https://github.com/eosphoros-ai/dbgpts) 中的包结构
2. 添加包含元数据的 `manifest.json`
3. 提交 Pull Request

:::info
如需查看详细的开发说明，请参考 [dbgpts Introduction](/docs/dbgpts/introduction)。
:::

## 下一步

| 主题 | 链接 |
|---|---|
| 构建 AWEL 工作流 | [AWEL Flow](/docs/getting-started/tools/awel-flow) |
| MCP 工具集成 | [MCP Protocol](/docs/getting-started/tools/mcp) |
| dbgpts 开发 | [dbgpts Introduction](/docs/dbgpts/introduction) |

---
sidebar_position: 0
title: InsightAgent
summary: "快速开始总览：了解 InsightAgent、最短上手路径，以及下一步阅读建议"
read_when:
  - 你希望从 clone 仓库到跑通 InsightAgent 对话，走最短路径
  - 你希望在深入之前先了解核心文档地图
---

# InsightAgent

InsightAgent 是一个开源框架，用于构建结合 **LLM、RAG、智能体、AWEL 工作流与数据库集成** 的 AI Native 数据应用。

如果你想最快跑通：选择一个 API 模型提供方，启动 webserver，然后打开 Web UI。

## 最快路径

1. 检查环境要求：[前置条件](/docs/getting-started/prerequisites)
2. 按 5 分钟上手流程操作：[快速开始](/docs/getting-started/quick-start)
3. 选择模型提供方：[模型提供方](/docs/getting-started/providers/)
4. 确认 UI 能在 `http://localhost:5670` 打开

## 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/liujincheng-ai/InsightAgent.git
cd InsightAgent

# 2. 安装依赖（以 OpenAI 代理模式为例）
uv sync --all-packages \
  --extra "base" \
  --extra "proxy_openai" \
  --extra "rag" \
  --extra "storage_chromadb" \
  --extra "dbgpts"

# 3. 配置 API Key
# 编辑 configs/dbgpt-proxy-openai.toml 并设置 api_key

# 4. 启动服务
uv run dbgpt start webserver --config configs/dbgpt-proxy-openai.toml
```

打开浏览器访问 [http://localhost:5670](http://localhost:5670)。

如果 UI 能正常打开，并且你可以发起对话，说明基础环境已经可用。

## InsightAgent 包含什么

- **SMMF**：模型管理与提供方切换
- **RAG**：文档与知识检索
- **Agents**：工具调用、任务规划与多智能体协作
- **AWEL**：基于 DAG 的工作流编排
- **Data sources**：SQL、分析与 Text2SQL 场景的数据源能力

## 接下来读什么

- **核心概念**
  - [架构](/docs/getting-started/concepts/architecture)
  - [AWEL](/docs/getting-started/concepts/awel)
  - [智能体](/docs/getting-started/concepts/agents)
  - [RAG](/docs/getting-started/concepts/rag)
- **安装与部署**
  - [模型提供方](/docs/getting-started/providers/)
  - [源码部署](/docs/getting-started/deploy/source-code)
  - [Docker 部署](/docs/getting-started/deploy/docker)
- **产品使用**
  - [Web UI 概览](/docs/getting-started/web-ui/)
  - [工具与插件](/docs/getting-started/tools/)
  - [故障排查](/docs/getting-started/troubleshooting/)
- **参考资料**
  - [开发指南](/docs/agents/introduction/)
  - [API 参考](/docs/api/introduction)
  - [配置参考](/docs/config/config-reference)
  - [FAQ](/docs/faq/install)

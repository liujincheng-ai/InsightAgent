---
sidebar_position: 4
title: SiliconFlow
---

# SiliconFlow

配置 InsightAgent 使用 SiliconFlow 托管模型 API。SiliconFlow 提供统一 API，可接入多种开源模型，并且服务位于国内环境中。

## 前置条件

- 一个可用的 [SiliconFlow API key](https://siliconflow.cn/)
- 已安装带 `proxy_openai` 扩展的 InsightAgent

## 安装依赖

```bash
uv sync --all-packages \
  --extra "base" \
  --extra "proxy_openai" \
  --extra "rag" \
  --extra "storage_chromadb" \
  --extra "dbgpts"
```

## 配置方式

编辑 `configs/dbgpt-proxy-siliconflow.toml`：

```toml
[models]
[[models.llms]]
name = "Qwen/Qwen2.5-Coder-32B-Instruct"
provider = "proxy/siliconflow"
api_key = "${env:SILICONFLOW_API_KEY}"

[[models.embeddings]]
name = "BAAI/bge-large-zh-v1.5"
provider = "proxy/openai"
api_url = "https://api.siliconflow.cn/v1/embeddings"
api_key = "${env:SILICONFLOW_API_KEY}"

[[models.rerankers]]
name = "BAAI/bge-reranker-v2-m3"
provider = "proxy/siliconflow"
api_key = "${env:SILICONFLOW_API_KEY}"
```

:::tip
建议使用环境变量：

```bash
export SILICONFLOW_API_KEY="your-siliconflow-api-key"
```
:::

## 可用模型

SiliconFlow 托管了很多开源模型，常见可选模型包括：

| 模型 | 配置名 | 说明 |
|---|---|---|
| Qwen2.5-Coder-32B | `Qwen/Qwen2.5-Coder-32B-Instruct` | 偏代码场景 |
| Qwen2.5-72B | `Qwen/Qwen2.5-72B-Instruct` | 通用用途 |
| DeepSeek-V3 | `deepseek-ai/DeepSeek-V3` | 推理能力强 |
| GLM-4-9B | `THUDM/glm-4-9b-chat` | 中英文兼顾 |

:::info
最新模型列表和价格请参考 [SiliconFlow 官方页面](https://siliconflow.cn/)。
:::

## 特性

SiliconFlow 配置还支持 **reranker**，用于增强 RAG 检索效果：

```toml
[[models.rerankers]]
name = "BAAI/bge-reranker-v2-m3"
provider = "proxy/siliconflow"
api_key = "${env:SILICONFLOW_API_KEY}"
```

## 启动服务

```bash
uv run dbgpt start webserver --config configs/dbgpt-proxy-siliconflow.toml
```

## 故障排查

| 问题 | 解决方法 |
|---|---|
| 鉴权失败 | 检查 SiliconFlow API key 是否正确 |
| 模型不可用 | 查看 SiliconFlow 当前支持的模型列表 |
| 响应较慢 | 大模型通常延迟更高，属于正常现象 |

## 下一步

- [Getting Started](/docs/getting-started/quick-start) —— 查看完整首跑流程
- [Model Providers](/docs/getting-started/providers/) —— 继续查看其他提供方

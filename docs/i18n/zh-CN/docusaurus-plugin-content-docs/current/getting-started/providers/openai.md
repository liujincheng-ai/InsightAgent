---
sidebar_position: 1
title: OpenAI
---

# OpenAI

配置 InsightAgent 使用 OpenAI 的 GPT 模型与 embedding 模型。

## 前置条件

- 一个可用的 [OpenAI API key](https://platform.openai.com/api-keys)
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

编辑 `configs/dbgpt-proxy-openai.toml`：

```toml
[models]
[[models.llms]]
name = "gpt-4o"
provider = "proxy/openai"
api_base = "https://api.openai.com/v1"
api_key = "sk-your-openai-api-key"

[[models.embeddings]]
name = "text-embedding-3-small"
provider = "proxy/openai"
api_url = "https://api.openai.com/v1/embeddings"
api_key = "sk-your-openai-api-key"
```

:::tip 使用环境变量
建议不要把 API key 直接写死在配置文件里，而是使用环境变量：

```toml
api_key = "${env:OPENAI_API_KEY}"
```

```bash
export OPENAI_API_KEY="sk-your-openai-api-key"
```
:::

## 可用模型

### LLM

| 模型 | 配置名 | 说明 |
|---|---|---|
| GPT-4o | `gpt-4o` | 推荐，效果最好 |
| GPT-4o mini | `gpt-4o-mini` | 更快、更便宜 |
| GPT-4 Turbo | `gpt-4-turbo` | 上一代方案 |
| GPT-3.5 Turbo | `gpt-3.5-turbo` | 预算敏感场景 |

### Embedding

| 模型 | 配置名 | 维度 |
|---|---|---|
| text-embedding-3-small | `text-embedding-3-small` | 1536 |
| text-embedding-3-large | `text-embedding-3-large` | 3072 |
| text-embedding-ada-002 | `text-embedding-ada-002` | 1536 |

## 启动服务

```bash
uv run dbgpt start webserver --config configs/dbgpt-proxy-openai.toml
```

## Azure OpenAI

如果你要使用 Azure OpenAI，可以把 `api_base` 改成 Azure endpoint：

```toml
[[models.llms]]
name = "gpt-4o"
provider = "proxy/openai"
api_base = "https://your-resource.openai.azure.com/openai/deployments/your-deployment"
api_key = "your-azure-api-key"
```

## 故障排查

| 问题 | 解决方法 |
|---|---|
| `AuthenticationError` | 检查 API key 是否有效，以及账号是否已开通计费 |
| `RateLimitError` | 降低请求频率，或升级 OpenAI 套餐 |
| Connection timeout | 检查网络连接，必要时配置代理 |
| Model not found | 检查模型名称是否与 OpenAI 当前提供的模型一致 |

## 下一步

- [Getting Started](/docs/getting-started/quick-start) —— 完整首跑流程
- [Config Reference](/docs/config/config-reference) —— 全部配置项说明
- [More Proxy LLMs](/docs/installation/advanced_usage/More_proxyllms) —— 更多 API 提供方

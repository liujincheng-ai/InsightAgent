---
sidebar_position: 3
title: Qwen (Tongyi)
---

# Qwen (Tongyi)

配置 InsightAgent 通过 DashScope API 使用阿里云的 Qwen 模型。

## 前置条件

- 一个可用的 [DashScope API key](https://dashscope.console.aliyun.com/)
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

编辑 `configs/dbgpt-proxy-tongyi.toml`：

```toml
[models]
[[models.llms]]
name = "qwen-plus"
provider = "proxy/tongyi"
api_base = "https://dashscope.aliyuncs.com/compatible-mode/v1"
api_key = "${env:DASHSCOPE_API_KEY}"

[[models.embeddings]]
name = "text-embedding-v3"
provider = "proxy/tongyi"
api_url = "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings"
api_key = "${env:DASHSCOPE_API_KEY}"
```

:::tip
建议通过环境变量传入密钥，避免直接写进配置文件：

```bash
export DASHSCOPE_API_KEY="your-dashscope-api-key"
```
:::

## 可用模型

### LLM

| 模型 | 配置名 | 说明 |
|---|---|---|
| Qwen-Max | `qwen-max` | 旗舰模型，效果最好 |
| Qwen-Plus | `qwen-plus` | 性能与成本平衡 |
| Qwen-Turbo | `qwen-turbo` | 更快、更便宜 |
| Qwen-Long | `qwen-long` | 更长上下文窗口 |

### Embedding

| 模型 | 配置名 | 说明 |
|---|---|---|
| text-embedding-v3 | `text-embedding-v3` | 推荐 |
| text-embedding-v2 | `text-embedding-v2` | 上一代方案 |

## 启动服务

```bash
uv run dbgpt start webserver --config configs/dbgpt-proxy-tongyi.toml
```

## 故障排查

| 问题 | 解决方法 |
|---|---|
| `InvalidAPIKey` | 检查 DashScope API key 是否正确且已激活 |
| 模型额度不足 | 到 DashScope 控制台检查使用额度 |
| 响应较慢 | 可以尝试 `qwen-turbo` |

## 下一步

- [Getting Started](/docs/getting-started/quick-start) —— 查看完整首跑流程
- [Model Providers](/docs/getting-started/providers/) —— 继续查看其他提供方

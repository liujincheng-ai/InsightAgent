---
sidebar_position: 5
title: Ollama
---

# Ollama

配置 InsightAgent 使用 [Ollama](https://ollama.ai) 在本地运行模型。Ollama 是在个人机器上部署开源模型最简单的方式之一。

## 前置条件

- 已安装并启动 [Ollama](https://ollama.ai)
- 已安装带 `proxy_ollama` 扩展的 InsightAgent

## 安装 Ollama

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

<Tabs>
  <TabItem value="mac" label="macOS" default>

```bash
# Download from https://ollama.ai or use Homebrew:
brew install ollama
```

  </TabItem>
  <TabItem value="linux" label="Linux">

```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

  </TabItem>
  <TabItem value="windows" label="Windows">

Download the installer from [ollama.ai](https://ollama.ai).

  </TabItem>
</Tabs>

### 拉取模型

```bash
# 拉取聊天模型
ollama pull deepseek-r1:1.5b

# 拉取 embedding 模型
ollama pull bge-m3:latest
```

:::tip
使用 `ollama list` 可以查看已下载模型。
:::

## 安装 InsightAgent 依赖

```bash
uv sync --all-packages \
  --extra "base" \
  --extra "proxy_ollama" \
  --extra "rag" \
  --extra "storage_chromadb" \
  --extra "dbgpts"
```

## 配置方式

编辑 `configs/dbgpt-proxy-ollama.toml`：

```toml
[models]
[[models.llms]]
name = "deepseek-r1:1.5b"
provider = "proxy/ollama"
api_base = "http://localhost:11434"
api_key = ""

[[models.embeddings]]
name = "bge-m3:latest"
provider = "proxy/ollama"
api_url = "http://localhost:11434"
api_key = ""
```

:::info
对于本地 Ollama，`api_key` 可以留空。如果 Ollama 运行在另一台机器上，则需要把 `api_base` 改成对应地址。
:::

## 常见模型选择

### 聊天模型

| 模型 | 拉取命令 | 大小 | 说明 |
|---|---|---|---|
| DeepSeek-R1 1.5B | `ollama pull deepseek-r1:1.5b` | ~1 GB | 小模型、速度快、推理能力不错 |
| Qwen2.5 7B | `ollama pull qwen2.5:7b` | ~4.7 GB | 综合平衡较好 |
| Llama 3.1 8B | `ollama pull llama3.1:8b` | ~4.7 GB | Meta 新一代模型 |
| Mistral 7B | `ollama pull mistral:7b` | ~4.1 GB | 通用场景、速度快 |

### Embedding 模型

| 模型 | 拉取命令 | 说明 |
|---|---|---|
| bge-m3 | `ollama pull bge-m3:latest` | 多语言 |
| nomic-embed-text | `ollama pull nomic-embed-text` | 更偏英文场景 |

## 启动服务

先确保 Ollama 已经在运行：

```bash
# 如果没有以服务方式启动，则手动启动 Ollama
ollama serve
```

然后启动 InsightAgent：

```bash
uv run dbgpt start webserver --config configs/dbgpt-proxy-ollama.toml
```

## 故障排查

| 问题 | 解决方法 |
|---|---|
| Connection refused | 确认 Ollama 已启动：`ollama serve` |
| Model not found | 先执行 `ollama pull model-name` 拉取模型 |
| 响应较慢 | 尝试更小模型，或确认是否使用了 GPU |
| 内存不足 | 换更小的量化模型，例如 `qwen2.5:7b-q4_0` |

## 下一步

- [Getting Started](/docs/getting-started/quick-start) —— 查看完整首跑流程
- [Ollama Advanced](/docs/installation/advanced_usage/ollama) —— 查看 Ollama 进阶配置
- [Model Providers](/docs/getting-started/providers/) —— 继续查看其他提供方

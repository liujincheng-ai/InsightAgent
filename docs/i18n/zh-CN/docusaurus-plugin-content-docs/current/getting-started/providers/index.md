---
sidebar_position: 0
title: 模型提供方
summary: "了解 InsightAgent 支持哪些模型提供方，以及首次部署应该如何选择"
read_when:
  - 你第一次部署时需要选择模型提供方
  - 你想判断应该使用 API 模型、Ollama 还是 vLLM
---

# 模型提供方

InsightAgent 同时支持 API 模型提供方和本地运行时。对于第一次部署，除非你明确需要本地推理，否则建议优先选择 API 提供方。

:::info 快速建议
如果你不确定该选哪个，建议先从 **OpenAI** 或 **DeepSeek** 开始：它们配置快、无需 GPU。若你希望在本地运行模型且尽量简化配置，可以选择 **Ollama**。
:::

## 提供方对比

| 提供方 | 类型 | 是否需要 GPU | 适合场景 |
|---|---|---|---|
| [**OpenAI**](./openai) | API 代理 | 否 | 生产质量、最快完成首跑 |
| [**DeepSeek**](./deepseek) | API 代理 | 否 | 性价比高、推理能力强 |
| [**Qwen (Tongyi)**](./qwen) | API 代理 | 否 | 中文场景、阿里云用户 |
| [**SiliconFlow**](./siliconflow) | API 代理 | 否 | 国内可用、模型选择多 |
| [**Ollama**](./ollama) | 本地代理 | 可选 | 本地模型、注重隐私、部署简单 |
| [**vLLM**](./vllm) | 本地运行时 | 是（NVIDIA） | 更高吞吐的生产级本地推理 |

## 模型配置是如何组织的

所有模型都通过 `configs/` 目录下的 TOML 文件配置。一个配置文件通常定义：

- **LLM(s)**：聊天与推理使用的大模型
- **Embedding(s)**：RAG 和知识检索使用的向量模型
- **Reranker(s)**：可选的重排序模型，用于提高检索质量

```toml
[models]

# 语言模型
[[models.llms]]
name = "model-name"
provider = "provider-type"
api_key = "your-api-key"

# 向量模型
[[models.embeddings]]
name = "embedding-model-name"
provider = "provider-type"
api_key = "your-api-key"
```

:::tip 环境变量
你可以在 TOML 中使用环境变量语法：`"${env:VARIABLE_NAME:-default_value}"`，避免把密钥直接写死在配置文件中。
:::

## 提供方指南

- [OpenAI](/docs/getting-started/providers/openai) —— 首次部署最常见、最省心的默认方案
- [DeepSeek](/docs/getting-started/providers/deepseek) —— 强推理能力，兼容 OpenAI 代理模式
- [Qwen (Tongyi)](/docs/getting-started/providers/qwen) —— 阿里云 / DashScope 方案
- [SiliconFlow](/docs/getting-started/providers/siliconflow) —— 适合国内环境的 API 方案
- [Ollama](/docs/getting-started/providers/ollama) —— 简单本地模型运行方式
- [vLLM](/docs/getting-started/providers/vllm) —— GPU 驱动的高性能本地推理方案

## 更多提供方

InsightAgent 还可以通过代理体系接入更多模型提供方。详见 [Advanced LLM Configuration](/docs/installation/advanced_usage/More_proxyllms)，包括：

- Azure OpenAI
- Google Gemini
- Anthropic Claude
- Baichuan
- Spark（讯飞星火）
- 以及更多兼容提供方

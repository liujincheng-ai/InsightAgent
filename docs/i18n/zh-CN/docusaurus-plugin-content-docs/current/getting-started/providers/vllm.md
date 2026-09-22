---
sidebar_position: 6
title: vLLM
---

# vLLM

配置 InsightAgent 使用 [vLLM](https://docs.vllm.ai/) 在 NVIDIA GPU 上进行高吞吐本地推理。

## 前置条件

- 安装了 CUDA 12.1+ 的 **NVIDIA GPU**
- 模型所需显存足够（7B 模型通常至少 8 GB+）
- 已安装带 `vllm` 扩展的 InsightAgent

## 安装依赖

```bash
uv sync --all-packages \
  --extra "base" \
  --extra "hf" \
  --extra "cuda121" \
  --extra "vllm" \
  --extra "rag" \
  --extra "storage_chromadb" \
  --extra "quant_bnb" \
  --extra "dbgpts"
```

## 配置方式

编辑 `configs/dbgpt-local-vllm.toml`：

```toml
[models]
[[models.llms]]
name = "DeepSeek-R1-Distill-Qwen-1.5B"
provider = "vllm"
# Download from HuggingFace automatically, or specify local path:
# path = "models/DeepSeek-R1-Distill-Qwen-1.5B"

[[models.embeddings]]
name = "BAAI/bge-large-zh-v1.5"
provider = "hf"
# path = "models/bge-large-zh-v1.5"
```

:::info 模型下载
如果没有指定 `path`，模型会自动从 HuggingFace Hub 下载。对于大模型，建议提前下载：

```bash
# Using huggingface-cli
huggingface-cli download deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B --local-dir models/DeepSeek-R1-Distill-Qwen-1.5B
```
:::

## 常见模型选择

| 模型 | 显存需求 | 说明 |
|---|---|---|
| DeepSeek-R1-Distill-Qwen-1.5B | ~4 GB | 小模型，适合测试 |
| GLM-4-9B-Chat | ~20 GB | 中英文能力都不错 |
| Qwen2.5-7B-Instruct | ~16 GB | 平衡性好 |
| Qwen2.5-Coder-7B-Instruct | ~16 GB | 偏代码场景 |

## 启动服务

```bash
uv run dbgpt start webserver --config configs/dbgpt-local-vllm.toml
```

:::tip 指定 GPU
如果你想指定某张 GPU：

```bash
CUDA_VISIBLE_DEVICES=0 uv run dbgpt start webserver --config configs/dbgpt-local-vllm.toml
```
:::

## 故障排查

| 问题 | 解决方法 |
|---|---|
| CUDA not found | 安装 CUDA 12.1+，并用 `nvidia-smi` 验证 |
| GPU 显存不足 | 使用更小模型，或启用量化（`quant_bnb`） |
| 模型下载失败 | 提前下载模型，或配置 HuggingFace 镜像 |
| 首次请求较慢 | vLLM 首次运行会编译 kernel，后续请求会明显更快 |

## 下一步

- [Getting Started](/docs/getting-started/quick-start) —— 查看完整首跑流程
- [vLLM Advanced](/docs/installation/advanced_usage/vLLM_inference) —— 查看 vLLM 进阶配置
- [Model Providers](/docs/getting-started/providers/) —— 继续查看其他提供方

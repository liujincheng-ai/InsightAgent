---
sidebar_position: 1
title: 快速安装
summary: "使用 README 中的安装脚本，以最快方式安装 InsightAgent"
read_when:
  - 你希望以最短路径跑通 InsightAgent Web UI
  - 你希望优先使用安装脚本而不是手动源码部署
---

import CommandCopyCard from "@site/src/components/mdx/CommandCopyCard";

# 快速安装

这是让 InsightAgent 跑起来的最快方式。安装脚本会帮你准备本地 InsightAgent 工作目录、生成 provider profile，并给出可直接运行的 webserver 启动命令。

## 推荐：安装脚本

如果你想从零开始，以最短路径获得一个可用的 InsightAgent Web UI，推荐直接使用安装脚本。

<CommandCopyCard command={`curl -fsSL https://raw.githubusercontent.com/liujincheng-ai/InsightAgent/main/scripts/install/install.sh | bash`} />

## 系统要求

这个快速安装流程主要面向以下环境：

- **macOS** 或 **Linux**
- 可运行 `bash` 的 shell 环境
- 可以联网下载依赖
- 如果你要直接使用托管模型 provider，需要提前准备好 API Key

:::tip 适用场景
如果你想快速体验 InsightAgent，而不是手动管理仓库结构和依赖细节，这条路径最合适。
:::

## 使用 provider profile 安装

如果你已经明确要使用哪个 provider，可以在安装时直接传入 profile 和 API Key。

### OpenAI 兼容 profile

<CommandCopyCard command={`curl -fsSL https://raw.githubusercontent.com/liujincheng-ai/InsightAgent/main/scripts/install/install.sh \
  | OPENAI_API_KEY=sk-xxx bash -s -- --profile openai`} />

### 通过 Moonshot API 使用 Kimi 2.5

<CommandCopyCard command={`curl -fsSL https://raw.githubusercontent.com/liujincheng-ai/InsightAgent/main/scripts/install/install.sh \
  | MOONSHOT_API_KEY=sk-xxx bash -s -- --profile kimi`} />

### 通过 OpenAI 兼容接口使用 MiniMax

<CommandCopyCard command={`curl -fsSL https://raw.githubusercontent.com/liujincheng-ai/InsightAgent/main/scripts/install/install.sh \
  | MINIMAX_API_KEY=sk-xxx bash -s -- --profile minimax`} />

## 复用已有本地仓库

如果你已经有一个本地 InsightAgent 仓库，可以直接复用，而不是重新克隆到 `~/.dbgpt/InsightAgent`。

### 使用本地仓库 + OpenAI

<CommandCopyCard command={`OPENAI_API_KEY=sk-xxx \
  bash scripts/install/install.sh --profile openai --repo-dir "$(pwd)" --yes`} />

### 使用本地仓库 + Kimi

<CommandCopyCard command={`MOONSHOT_API_KEY=sk-xxx \
  bash scripts/install/install.sh --profile kimi --repo-dir "$(pwd)" --yes`} />

### 使用本地仓库 + MiniMax

<CommandCopyCard command={`MINIMAX_API_KEY=sk-xxx \
  bash scripts/install/install.sh --profile minimax --repo-dir "$(pwd)" --yes`} />

## 安装脚本会准备什么

安装脚本会帮你准备一套通用运行布局：

- 在 `~/.dbgpt/InsightAgent` 下放置一个 InsightAgent checkout（如果没有使用 `--repo-dir`）
- 在 `~/.dbgpt/configs/` 下生成 provider 配置文件
- 在 `~/.dbgpt/` 下准备 InsightAgent home 目录
- 给出一个基于生成 profile 的 webserver 启动命令

## 安装完成后启动 InsightAgent

安装完成后，使用生成的 profile 配置启动 webserver：

<CommandCopyCard command={`cd ~/.dbgpt/InsightAgent && uv run dbgpt start webserver --profile <profile>`} />

然后打开 [http://localhost:5670](http://localhost:5670)。

## 验证安装是否成功

如果满足以下条件，就说明安装成功：

- webserver 启动时没有配置错误
- Web UI 能在 `http://localhost:5670` 打开
- 你可以在浏览器中发起聊天

## 先查看安装脚本

如果你希望先审查脚本内容，再决定是否执行：

```bash
curl -fsSL https://raw.githubusercontent.com/liujincheng-ai/InsightAgent/main/scripts/install/install.sh -o install.sh
less install.sh
bash install.sh --profile openai
```

## 其他安装方式

如果安装脚本不适合你的环境：

- 使用 [CLI 安装](/docs/getting-started/cli-quickstart)，通过 PyPI 安装并使用 `dbgpt` 命令
- 使用 [源码安装](/docs/getting-started/deploy/source-code)，用于开发、调试和自定义部署

## 故障排查

### 安装脚本不适合我的 shell 或平台

请改用 [CLI 安装](/docs/getting-started/cli-quickstart) 或 [源码安装](/docs/getting-started/deploy/source-code)。

### 我想更细粒度地控制依赖和配置

请使用 [源码安装](/docs/getting-started/deploy/source-code)。它会暴露完整仓库结构和 `uv sync` 安装流程。

### 安装完成了，但 InsightAgent 启动不正常

先检查 `~/.dbgpt/configs/` 下生成的配置文件，然后参考 [安装问题排查](/docs/getting-started/troubleshooting/installation)。

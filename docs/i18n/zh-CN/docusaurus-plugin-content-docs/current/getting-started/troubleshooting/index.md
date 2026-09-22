---
sidebar_position: 0
title: Troubleshooting
summary: "安装、模型和环境问题的首要检查项与常见修复方式"
read_when:
  - 遇到问题，想先走最快的排查路径
  - InsightAgent 启动不稳定、UI 白屏或模型加载失败
---

# Troubleshooting

这里整理了使用 InsightAgent 时的常见问题和解决方法。

## 前 60 秒先做什么

先执行下面这些检查：

```bash
curl http://localhost:5670/api/health
dbgpt model list
docker logs dbgpt -f
```

如果你不是用 Docker 部署的，请直接查看你启动 webserver 的那个终端输出。

## 常见快速修复方式

- **服务无法启动**
  - 重新执行带正确 extras 的 `uv sync`
  - 参考 [Installation Issues](/docs/getting-started/troubleshooting/installation)
- **Web UI 白屏**
  - 先等待启动完全结束
  - 确认服务在 `http://localhost:5670` 可访问
- **模型不存在 / 鉴权错误**
  - 重新检查 TOML 配置和 provider 名称
  - 参考 [Model Issues](/docs/getting-started/troubleshooting/llm)
- **5670 端口被占用**
  - 使用 `lsof -i :5670` 找到冲突进程
- **内存不足**
  - 换更小的本地模型，或改用 API 代理模型

## 更具体的排查指南

- [Installation Issues](/docs/getting-started/troubleshooting/installation)
- [Model Issues](/docs/getting-started/troubleshooting/llm)
- [Environment Variables](/docs/getting-started/troubleshooting/environment)

## Logs

```bash
# 源码部署
# 默认日志直接输出到 stdout

# Docker 部署
docker logs dbgpt -f

# Docker Compose 部署
docker logs db-gpt-webserver-1 -f
```

## 获取帮助

如果这些排查文档仍然无法解决问题：

1. **搜索已有 issue**：[GitHub Issues](https://github.com/liujincheng-ai/InsightAgent/issues)
2. **向社区提问**：[GitHub Discussions](https://github.com/liujincheng-ai/InsightAgent/discussions)
3. **加入 Slack**：[InsightAgent Slack](https://join.slack.com/t/slack-inu2564/shared_invite/zt-29rcnyw2b-N~ubOD9kFc7b7MDOAM1otA)
4. **查看 FAQ**：[Installation FAQ](/docs/faq/install) · [LLM FAQ](/docs/faq/llm) · [KBQA FAQ](/docs/faq/kbqa)

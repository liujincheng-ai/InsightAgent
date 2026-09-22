---
sidebar_position: 3
title: 环境变量
---

# 环境变量

这里汇总了 InsightAgent 中常用的环境变量。

:::tip
大部分配置都通过 TOML 配置文件完成。环境变量更适合用于密钥、Docker 部署以及覆盖默认值。
:::

## 模型配置

| 变量 | 说明 | 示例 |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI API key | `sk-...` |
| `OPENAI_API_BASE` | OpenAI 兼容 API 的基础地址 | `https://api.openai.com/v1` |
| `DEEPSEEK_API_KEY` | DeepSeek API key | `sk-...` |
| `SILICONFLOW_API_KEY` | SiliconFlow API key | `sk-...` |
| `DASHSCOPE_API_KEY` | 阿里云 DashScope API key | `sk-...` |
| `AIMLAPI_API_KEY` | AI/ML API key | — |
| `LLM_MODEL` | 默认 LLM 模型名称（集群模式） | `glm-4-9b-chat` |
| `MODEL_SERVER` | 模型控制器地址（集群模式） | `http://127.0.0.1:8000` |

## 服务端配置

| 变量 | 说明 | 默认值 |
|---|---|---|
| `DBGPT_LOG_LEVEL` | 日志级别 | `INFO` |
| `LOCAL_DB_TYPE` | 元数据库类型 | `sqlite` |
| `LOCAL_DB_PATH` | SQLite 数据库路径 | `data/default_sqlite.db` |
| `MYSQL_HOST` | MySQL host | `127.0.0.1` |
| `MYSQL_PORT` | MySQL port | `3306` |
| `MYSQL_USER` | MySQL 用户名 | `root` |
| `MYSQL_PASSWORD` | MySQL 密码 | — |
| `MYSQL_DATABASE` | MySQL 数据库名 | `dbgpt` |

## GPU 与硬件

| 变量 | 说明 | 示例 |
|---|---|---|
| `CUDA_VISIBLE_DEVICES` | 限制可见 GPU | `0,1` |
| `DEVICE` | 强制指定设备类型 | `cuda`, `cpu`, `mps` |

## 网络与代理

| 变量 | 说明 | 示例 |
|---|---|---|
| `UV_INDEX_URL` | uv 使用的 PyPI 镜像地址 | `https://pypi.tuna.tsinghua.edu.cn/simple` |
| `HTTP_PROXY` | 外部请求的 HTTP 代理 | `http://proxy:8080` |
| `HTTPS_PROXY` | 外部请求的 HTTPS 代理 | `http://proxy:8080` |
| `NO_PROXY` | 不走代理的主机列表 | `localhost,127.0.0.1` |

## 在 TOML 配置中使用环境变量

InsightAgent 支持在 TOML 配置文件中引用环境变量：

```toml
[[models.llms]]
api_key = "${env:OPENAI_API_KEY}"

[[models.embeddings]]
api_key = "${env:OPENAI_API_KEY:-default-key}"
```

**语法：**

| 写法 | 行为 |
|---|---|
| `${env:VAR_NAME}` | 从环境变量读取（缺失时报错） |
| `${env:VAR_NAME:-default}` | 从环境变量读取，若未设置则使用 `default` |

## Docker 环境变量

使用 Docker 运行时，可以通过 `-e` 传递环境变量：

```bash
docker run -it --rm \
  -e SILICONFLOW_API_KEY=your-key \
  -e DBGPT_LOG_LEVEL=DEBUG \
  -p 5670:5670 \
  eosphorosai/dbgpt-openai
```

或者在 `docker-compose.yml` 中配置：

```yaml
services:
  webserver:
    environment:
      - SILICONFLOW_API_KEY=${SILICONFLOW_API_KEY}
      - DBGPT_LOG_LEVEL=INFO
```

## 下一步

| 主题 | 链接 |
|---|---|
| 完整配置参考 | [Config Reference](/docs/config/config-reference) |
| 模型提供方 | [Providers](/docs/getting-started/providers/) |
| 故障排查总览 | [Troubleshooting](/docs/getting-started/troubleshooting/) |

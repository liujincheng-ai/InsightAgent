---
sidebar_position: 2
title: Docker Compose 部署
---

# Docker Compose 部署

通过 Docker Compose 搭配 MySQL 部署 InsightAgent。这种方式适合生产场景，并支持持久化存储。

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

## 前置条件

- 已安装 [Docker](https://docs.docker.com/get-docker/) 和 [Docker Compose](https://docs.docker.com/compose/install/)
- 已获取一个受支持 provider 的 API Key

## 快速开始

根目录下的 `docker-compose.yml` 会部署一个带 MySQL 数据库的 InsightAgent，并默认使用 SiliconFlow 作为 LLM provider。

### 第一步：设置 API Key

<Tabs>
  <TabItem value="siliconflow" label="SiliconFlow" default>

```bash
export SILICONFLOW_API_KEY="your-siliconflow-api-key"
```

可在 [SiliconFlow](https://cloud.siliconflow.cn/account/ak) 获取 API Key。

  </TabItem>
  <TabItem value="aiml" label="AI/ML API">

```bash
export AIMLAPI_API_KEY="your-aiml-api-key"
```

可在 [AI/ML API](https://aimlapi.com/) 获取 API Key。

  </TabItem>
</Tabs>

### 第二步：启动服务

<Tabs>
  <TabItem value="siliconflow" label="SiliconFlow" default>

```bash
SILICONFLOW_API_KEY=${SILICONFLOW_API_KEY} docker compose up -d
```

  </TabItem>
  <TabItem value="aiml" label="AI/ML API">

```bash
AIMLAPI_API_KEY=${AIMLAPI_API_KEY} docker compose up -d
```

  </TabItem>
</Tabs>

你应该会看到类似下面的输出：

```
[+] Running 3/3
 ✔ Network dbgptnet              Created   0.0s
 ✔ Container db-gpt-db-1         Started   0.2s
 ✔ Container db-gpt-webserver-1  Started   0.2s
```

### 第三步：打开 Web UI

在浏览器中访问 **[http://localhost:5670](http://localhost:5670)**。

:::warning 首次启动可能需要一点时间
Webserver 会等待 MySQL 初始化完成。如果第一次启动失败，容器通常会自动重启。你可以通过 `docker logs db-gpt-webserver-1 -f` 查看日志。
:::

## 部署内容

默认的 `docker-compose.yml` 会创建以下服务：

| 服务 | 镜像 | 端口 | 用途 |
|---|---|---|---|
| `db` | `mysql/mysql-server` | 3306 | 用于元数据存储的 MySQL 数据库 |
| `webserver` | `eosphorosai/dbgpt-openai:latest` | 5670 | InsightAgent 应用服务 |

## 常见操作

### 查看日志

```bash
# Webserver 日志
docker logs db-gpt-webserver-1 -f

# 数据库日志
docker logs db-gpt-db-1 -f
```

### 停止服务

```bash
docker compose down
```

### 重启服务

```bash
docker compose restart
```

### 重置所有内容（包括数据）

```bash
docker compose down -v
```

:::warning
`-v` 参数会删除所有 volumes，包括 MySQL 数据库数据。所有数据都会丢失。
:::

## 自定义配置

### 使用不同的配置文件

你可以挂载自己的 TOML 配置，并覆盖启动命令：

```yaml
webserver:
  image: eosphorosai/dbgpt-openai:latest
  command: dbgpt start webserver --config /app/configs/your-config.toml
  volumes:
    - ./your-config.toml:/app/configs/your-config.toml
```

### 挂载本地模型

对于 GPU 部署，可以挂载本地模型目录：

```yaml
webserver:
  volumes:
    - /data/models:/app/models
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            capabilities: [gpu]
```

## 其他 Compose 示例

InsightAgent 还提供了适用于不同场景的 Compose 文件：

| 文件 | 适用场景 |
|---|---|
| `docker-compose.yml` | 默认代理模式 + MySQL 部署 |
| `docker/compose_examples/cluster-docker-compose.yml` | 带 GPU 的多 Worker 集群 |
| `docker/compose_examples/ha-cluster-docker-compose.yml` | 高可用集群 |
| `docker/compose_examples/dbgpt-oceanbase-docker-compose.yml` | OceanBase 数据库后端 |

示例：

```bash
docker compose -f docker/compose_examples/cluster-docker-compose.yml up -d
```

## 下一步

| 主题 | 链接 |
|---|---|
| 集群部署 | [Cluster](/docs/getting-started/deploy/cluster) |
| Docker（单容器）部署 | [Docker](/docs/getting-started/deploy/docker) |
| 源码部署 | [Source Code](/docs/getting-started/deploy/source-code) |

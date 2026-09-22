---
id: docker-build-guide
title: InsightAgent Docker 镜像构建指南
sidebar_label: Docker 镜像构建
description: 全面介绍如何使用各种配置构建 InsightAgent Docker 镜像
keywords:
  - InsightAgent
  - Docker
  - Build
  - CUDA
  - OpenAI
  - VLLM
  - Llama-cpp
---

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';
import CodeBlock from '@theme/CodeBlock';

# InsightAgent Docker 镜像构建指南

本指南详细介绍如何使用 `docker/base/build_image.sh` 脚本，以各种配置构建 InsightAgent Docker 镜像。

## 概述

InsightAgent 构建脚本允许你根据具体需求创建定制化的 Docker 镜像。你可以选择预定义的安装模式，也可以通过指定额外依赖、环境变量等参数来自定义构建。

## 可用安装模式

<Tabs>
  <TabItem value="default" label="默认模式" default>
    基于 CUDA 的标准功能镜像。
    
    ```bash
    bash docker/base/build_image.sh
    ```
    
    包含：CUDA 支持、代理集成（OpenAI、Ollama、智谱、Anthropic、千帆、通义）、RAG 能力、Graph RAG、Hugging Face 集成以及量化支持。
  </TabItem>
  <TabItem value="openai" label="OpenAI 模式">
    基于 CPU 的 OpenAI API 优化镜像。
    
    ```bash
    bash docker/base/build_image.sh --install-mode openai
    ```
    
    包含：基础功能、所有代理集成以及 RAG 能力，无需 GPU 加速。
  </TabItem>
  <TabItem value="vllm" label="VLLM 模式">
    基于 CUDA 的 VLLM 优化推理镜像。
    
    ```bash
    bash docker/base/build_image.sh --install-mode vllm
    ```
    
    包含：所有默认功能以及 VLLM 高性能推理支持。
  </TabItem>
  <TabItem value="llama-cpp" label="Llama-cpp 模式">
    基于 CUDA 的 Llama-cpp 支持镜像。
    
    ```bash
    bash docker/base/build_image.sh --install-mode llama-cpp
    ```
    
    包含：所有默认功能以及 Llama-cpp 和 Llama-cpp Server，通过 `CMAKE_ARGS="-DGGML_CUDA=ON"` 启用 CUDA 加速。
  </TabItem>
  <TabItem value="full" label="完整模式">
    基于 CUDA 的全功能镜像。
    
    ```bash
    bash docker/base/build_image.sh --install-mode full
    ```
    
    包含：其他所有模式的功能以及 Embedding 能力。
  </TabItem>
</Tabs>

## 基本用法

### 查看可用模式

查看所有可用的安装模式及其配置：

```bash
bash docker/base/build_image.sh --list-modes
```

### 获取帮助

显示所有可用选项：

```bash
bash docker/base/build_image.sh --help
```

## 自定义选项

### Python 版本

InsightAgent 要求 Python 3.10 或更高版本。默认使用 Python 3.11，你也可以指定其他版本：

```bash
bash docker/base/build_image.sh --python-version 3.10
```

### 自定义镜像名称

为构建的镜像设置自定义名称：

```bash
bash docker/base/build_image.sh --image-name mycompany/dbgpt
```

### 镜像名称后缀

添加后缀用于版本标识或环境区分：

```bash
bash docker/base/build_image.sh --image-name-suffix v1.0
```

默认模式下会生成 `eosphorosai/dbgpt-v1.0`，指定模式下会生成 `eosphorosai/dbgpt-MODE-v1.0`。

### PIP 镜像源

指定不同的 PIP 索引地址：

```bash
bash docker/base/build_image.sh --pip-index-url https://pypi.org/simple
```

### Ubuntu 镜像源

控制是否使用清华 Ubuntu 镜像源：

```bash
bash docker/base/build_image.sh --use-tsinghua-ubuntu false
```

### 语言偏好

设置首选语言（默认为英文）：

```bash
bash docker/base/build_image.sh --language zh
```

## 高级自定义

### 自定义额外依赖

你可以自定义镜像中安装的 Python 包额外依赖：

<Tabs>
  <TabItem value="override" label="覆盖依赖" default>
    完全替换默认的额外依赖：
    
    ```bash
    bash docker/base/build_image.sh --extras "base,proxy_openai,rag,storage_chromadb"
    ```
  </TabItem>
  <TabItem value="add" label="追加依赖">
    保留默认依赖并追加更多：
    
    ```bash
    bash docker/base/build_image.sh --add-extras "storage_milvus,storage_elasticsearch,datasource_postgres"
    ```
  </TabItem>
  <TabItem value="mode-specific" label="按模式追加">
    为特定安装模式追加额外依赖：
    
    ```bash
    bash docker/base/build_image.sh --install-mode vllm --add-extras "storage_milvus,datasource_postgres"
    ```
  </TabItem>
</Tabs>

#### 可用的额外依赖

以下是一些常用的额外依赖：

| 依赖包 | 说明 |
|--------|------|
| `storage_milvus` | Milvus 向量存储集成 |
| `storage_elasticsearch` | Elasticsearch 向量存储集成 |
| `datasource_postgres` | PostgreSQL 数据库连接器 |
| `vllm` | VLLM 优化推理集成 |
| `llama_cpp` | Llama-cpp Python 绑定 |
| `llama_cpp_server` | Llama-cpp HTTP 服务器 |

你可以在本地 InsightAgent 仓库中运行 `uv run install_help.py list` 查看所有可用的额外依赖。

### 环境变量

InsightAgent 构建支持通过环境变量进行特殊配置。主要使用的环境变量是 `CMAKE_ARGS`，对于 Llama-cpp 编译尤为重要。

<Tabs>
  <TabItem value="override-env" label="覆盖环境变量" default>
    替换默认的环境变量：
    
    ```bash
    bash docker/base/build_image.sh --env-vars "CMAKE_ARGS=\"-DGGML_CUDA=ON -DLLAMA_CUBLAS=ON\""
    ```
  </TabItem>
  <TabItem value="add-env" label="追加环境变量">
    追加额外的环境变量：
    
    ```bash
    bash docker/base/build_image.sh --install-mode llama-cpp --add-env-vars "FORCE_CMAKE=1"
    ```
  </TabItem>
</Tabs>

:::note
在 Llama-cpp 模式下，`CMAKE_ARGS="-DGGML_CUDA=ON"` 会自动设置以启用 CUDA 加速。
:::

### Docker 网络

指定构建时使用的 Docker 网络：

```bash
bash docker/base/build_image.sh --network host
```

### 自定义 Dockerfile

使用自定义 Dockerfile：

```bash
bash docker/base/build_image.sh --dockerfile Dockerfile.custom
```

## 使用场景示例

### 企业版：集成 PostgreSQL 和 Elasticsearch

构建集成 PostgreSQL 和 Elasticsearch 的全功能企业版：

```bash
bash docker/base/build_image.sh --install-mode full \
  --add-extras "storage_elasticsearch,datasource_postgres" \
  --image-name-suffix enterprise \
  --python-version 3.10 \
  --load-examples false
```

### 针对特定硬件优化的 Llama-cpp

使用自定义 Llama-cpp 优化参数进行构建：

```bash
bash docker/base/build_image.sh --install-mode llama-cpp \
  --env-vars "CMAKE_ARGS=\"-DGGML_CUDA=ON -DGGML_AVX2=OFF -DGGML_AVX512=ON\"" \
  --python-version 3.11
```

### 轻量级 OpenAI 代理

构建最小化的 OpenAI 代理镜像：

```bash
bash docker/base/build_image.sh --install-mode openai \
  --use-tsinghua-ubuntu false \
  --pip-index-url https://pypi.org/simple \
  --load-examples false
```

### 集成 Milvus 的开发版

构建集成 Milvus 的开发版镜像：

```bash
bash docker/base/build_image.sh --install-mode vllm \
  --add-extras "storage_milvus" \
  --image-name-suffix dev
```

## 常见问题排查

<details>
<summary>常见构建问题</summary>

### 找不到 CUDA

如果遇到 CUDA 相关错误：

```bash
# 尝试使用不同的 CUDA 基础镜像
bash docker/base/build_image.sh --base-image nvidia/cuda:12.1.0-devel-ubuntu22.04
```

### 依赖包安装失败

如果额外依赖安装失败：

```bash
# 尝试减少依赖以定位问题
bash docker/base/build_image.sh --extras "base,proxy_openai,rag"
```

### 网络问题

如果遇到网络问题：

```bash
# 使用指定网络
bash docker/base/build_image.sh --network host
```

</details>

## 参数参考

### 脚本选项

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `--install-mode` | 安装模式 | `default` |
| `--base-image` | 基础 Docker 镜像 | `nvidia/cuda:12.4.0-devel-ubuntu22.04` |
| `--image-name` | Docker 镜像名称 | `eosphorosai/dbgpt` |
| `--image-name-suffix` | 镜像名称后缀 | ` ` |
| `--pip-index-url` | PIP 镜像源地址 | `https://pypi.tuna.tsinghua.edu.cn/simple` |
| `--language` | 界面语言 | `en` |
| `--load-examples` | 加载示例数据 | `true` |
| `--python-version` | Python 版本 | `3.11` |
| `--use-tsinghua-ubuntu` | 使用清华 Ubuntu 镜像源 | `true` |
| `--extras` | 安装的额外依赖包 | 取决于安装模式 |
| `--add-extras` | 追加的额外依赖包 | ` ` |
| `--env-vars` | 构建环境变量 | 取决于安装模式 |
| `--add-env-vars` | 追加的环境变量 | ` ` |
| `--dockerfile` | 使用的 Dockerfile | `Dockerfile` |
| `--network` | 使用的 Docker 网络 | ` ` |

## 相关资源

- [InsightAgent 文档](https://github.com/liujincheng-ai/InsightAgent)
- [Docker 文档](https://docs.docker.com/)
- [CUDA 文档](https://docs.nvidia.com/cuda/)
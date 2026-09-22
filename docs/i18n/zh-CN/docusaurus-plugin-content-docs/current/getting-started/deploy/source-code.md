---
sidebar_position: 0
title: 源码部署
summary: "Run InsightAgent from source with uv, configure a provider, and verify the webserver"
read_when:
  - You want the repo-based install instead of Docker
  - You need the most flexible setup for development or customization
---

# 源码部署

直接通过源码部署 InsightAgent。这是最灵活的方式，适合开发、调试以及自定义集成场景。

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

## 硬件要求

| 模式 | CPU × 内存 | GPU | 说明 |
|---|---|---|---|
| API proxy | 4C × 8 GB | 无 | 代理模式不使用本地 GPU |
| Local model | 8C × 32 GB | ≥ 24 GB VRAM | 需要支持 CUDA 的 NVIDIA GPU |

## 第一步：克隆仓库

```bash
git clone https://github.com/liujincheng-ai/InsightAgent.git
cd InsightAgent
```

## 第二步：安装 uv

<Tabs>
  <TabItem value="sh" label="macOS / Linux" default>

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

  </TabItem>
  <TabItem value="pypi" label="PyPI (pipx)">

```bash
python -m pip install --upgrade pip
python -m pip install --upgrade pipx
python -m pipx ensurepath
pipx install uv --global
```

  </TabItem>
</Tabs>

验证：

```bash
uv --version
```

## 第三步：安装依赖

<Tabs>
  <TabItem value="openai" label="OpenAI (proxy)" default>

```bash
uv sync --all-packages \
  --extra "base" \
  --extra "proxy_openai" \
  --extra "rag" \
  --extra "storage_chromadb" \
  --extra "dbgpts"
```

  </TabItem>
  <TabItem value="deepseek" label="DeepSeek (proxy)">

```bash
uv sync --all-packages \
  --extra "base" \
  --extra "proxy_openai" \
  --extra "rag" \
  --extra "storage_chromadb" \
  --extra "dbgpts"
```

:::info
DeepSeek 使用 OpenAI 兼容代理，因此所需 extras 与 OpenAI 相同。
:::

  </TabItem>
  <TabItem value="ollama" label="Ollama (local)">

```bash
uv sync --all-packages \
  --extra "base" \
  --extra "proxy_ollama" \
  --extra "rag" \
  --extra "storage_chromadb" \
  --extra "dbgpts"
```

  </TabItem>
  <TabItem value="gpu" label="Local GPU (HuggingFace)">

```bash
uv sync --all-packages \
  --extra "base" \
  --extra "cuda121" \
  --extra "hf" \
  --extra "rag" \
  --extra "storage_chromadb" \
  --extra "quant_bnb" \
  --extra "dbgpts"
```

  </TabItem>
</Tabs>

<details>
<summary><strong>使用交互式安装辅助工具</strong></summary>

InsightAgent 提供了一个交互式辅助工具，用于生成合适的 `uv sync` 命令：

```bash
uv run install_help.py install-cmd --interactive
```

或者列出所有可用的 extras：

```bash
uv run install_help.py list
```

</details>

## 第四步：配置模型

编辑与你所选 provider 对应的 TOML 配置文件。详情请参考 [Model Providers](/docs/getting-started/providers/)。

<Tabs>
  <TabItem value="openai" label="OpenAI" default>

编辑 `configs/dbgpt-proxy-openai.toml`：

```toml
[models]
[[models.llms]]
name = "chatgpt_proxyllm"
provider = "proxy/openai"
api_key = "your-openai-api-key"    # <-- 替换为你的 key

[[models.embeddings]]
name = "text-embedding-3-small"
provider = "proxy/openai"
api_key = "your-openai-api-key"    # <-- 替换为你的 key
```

  </TabItem>
  <TabItem value="deepseek" label="DeepSeek">

编辑 `configs/dbgpt-proxy-deepseek.toml`：

```toml
[models]
[[models.llms]]
name = "deepseek-reasoner"
provider = "proxy/deepseek"
api_key = "your-deepseek-api-key"  # <-- 替换为你的 key

[[models.embeddings]]
name = "BAAI/bge-large-zh-v1.5"
provider = "hf"
```

:::info
如果使用 HuggingFace Embedding，请在安装命令中额外加入 `--extra "hf"` 和 `--extra "cpu"`。
:::

  </TabItem>
  <TabItem value="ollama" label="Ollama">

请先确保 [Ollama](https://ollama.ai) 已运行，然后编辑 `configs/dbgpt-proxy-ollama.toml`：

```toml
[models]
[[models.llms]]
name = "qwen2.5:latest"
provider = "proxy/ollama"
api_base = "http://localhost:11434"

[[models.embeddings]]
name = "nomic-embed-text:latest"
provider = "proxy/ollama"
api_base = "http://localhost:11434"
```

  </TabItem>
</Tabs>

:::tip 环境变量
你可以在 TOML 中使用 `"${env:OPENAI_API_KEY}"` 这样的写法从环境变量读取 key，而不是将密钥硬编码到文件里。
:::

## 第五步：启动服务

<Tabs>
  <TabItem value="openai" label="OpenAI" default>

```bash
uv run dbgpt start webserver --config configs/dbgpt-proxy-openai.toml
```

  </TabItem>
  <TabItem value="deepseek" label="DeepSeek">

```bash
uv run dbgpt start webserver --config configs/dbgpt-proxy-deepseek.toml
```

  </TabItem>
  <TabItem value="ollama" label="Ollama">

```bash
uv run dbgpt start webserver --config configs/dbgpt-proxy-ollama.toml
```

  </TabItem>
</Tabs>

## 第六步：打开 Web UI

在浏览器中访问 **[http://localhost:5670](http://localhost:5670)**。

:::tip 验证是否成功
如果 Web UI 能正常打开，且你可以发起聊天会话，就说明 InsightAgent 已成功运行。
:::

## 首次运行常见问题

- **`uv sync` fails**
  - 重新检查 Python 与 uv： [Prerequisites](/docs/getting-started/prerequisites)
  - 如果你在中国大陆，可通过 `UV_INDEX_URL` 使用镜像源
- **Provider auth fails**
  - 确认 `configs/` 下所选 TOML 文件是否正确
  - 参考对应 provider 指南：[Model Providers](/docs/getting-started/providers/)
- **Server starts but UI is blank**
  - 确认终端中服务已正常启动且没有报错
  - 检查是否有其他进程占用了 `5670` 端口

## 数据库配置

<Tabs>
  <TabItem value="sqlite" label="SQLite (default)" default>

SQLite 是默认选项，相关表会自动创建，无需额外配置。

```toml
[service.web.database]
type = "sqlite"
path = "pilot/meta_data/dbgpt.db"
```

  </TabItem>
  <TabItem value="mysql" label="MySQL">

1. 创建数据库：

```bash
mysql -h127.0.0.1 -uroot -p{your_password} < ./assets/schema/dbgpt.sql
```

2. 更新 TOML 配置：

```toml
[service.web.database]
type = "mysql"
host = "127.0.0.1"
port = 3306
user = "root"
database = "dbgpt"
password = "your-password"
```

  </TabItem>
</Tabs>

## 加载测试数据（可选）

```bash
# Linux / macOS
bash ./scripts/examples/load_examples.sh

# Windows
.\scripts\examples\load_examples.bat
```

## 单独运行前端（可选）

如果你需要进行前端开发或自定义 UI：

```bash
cd web && npm install
cp .env.template .env
# 编辑 .env，将 API_BASE_URL 设为 http://localhost:5670
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## 下一步

| 主题 | 链接 |
|---|---|
| 配置更多模型提供方 | [Model Providers](/docs/getting-started/providers/) |
| 使用 Docker 部署 | [Docker](/docs/getting-started/deploy/docker) |
| 以集群方式部署 | [Cluster](/docs/getting-started/deploy/cluster) |
| 了解 Web UI | [Web UI Guide](/docs/getting-started/web-ui/) |

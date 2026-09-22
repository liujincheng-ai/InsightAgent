---
sidebar_position: 1
title: CLI 安装
summary: "通过 PyPI 安装 InsightAgent，并用单条命令启动它，无需源码 checkout"
read_when:
  - 你想直接从 PyPI 安装 InsightAgent
  - 你希望通过 `dbgpt` CLI 完成交互式配置
---

# CLI 安装

通过 PyPI 安装 InsightAgent，并使用单条命令启动它 —— 无需检出源码仓库。

:::tip 前置条件
- Python **3.10** 或更高版本
- 推荐使用 [uv](https://docs.astral.sh/uv/getting-started/installation/) 包管理器，也支持 pip
:::

## 1. 安装

```bash
# 推荐：使用 uv
uv pip install dbgpt-app

# 或者使用 pip
pip install dbgpt-app
```

:::tip 配置 PyPI 镜像源
如果下载速度较慢，可在安装时指定镜像源加速：

```bash
uv pip install dbgpt-app --index-url https://pypi.tuna.tsinghua.edu.cn/simple  # uv

pip install dbgpt-app -i https://pypi.tuna.tsinghua.edu.cn/simple              # pip
```

也可以通过环境变量，让当前终端会话中的**所有**安装命令自动使用镜像源：

```bash
export UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple   # uv

export PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple  # pip
```
:::

:::info 默认包含内容
默认安装会包含 **核心框架**（CLI、FastAPI、SQLAlchemy、Agent）、**OpenAI 兼容 LLM 支持**（也适用于 Kimi、Qwen、MiniMax、Z.AI）、**DashScope / Tongyi** 支持、**RAG 文档解析** 和 **ChromaDB** 向量存储。

如果你需要更多 provider 或数据源，可参考 [可选模块](#8-可选模块)。
:::

安装完成后，终端中就可以直接使用 `dbgpt` 命令。

## 2. 启动 InsightAgent

```bash
dbgpt start
```

首次运行时，InsightAgent 会自动启动一个 **交互式配置向导**，帮助你：

1. 选择 LLM provider（OpenAI、Kimi、Qwen、MiniMax、Z.AI 或自定义 endpoint）
2. 输入 API Key（或改用环境变量）
3. 确认模型名称和 API Base URL

完成后，系统会把 TOML 配置写入 `~/.dbgpt/configs/<profile>.toml`，并自动启动 webserver。

### 启动后的样子

```
    ____  ____        ____ ____ _____
   |  _ \| __ )      / ___|  _ \_   _|
   | | | |  _ \ ____| |  _| |_) || |
   | |_| | |_) |____| |_| |  __/ | |
   |____/|____/      \____|_|    |_|

   🚀 InsightAgent Quick Start

   +- - - - - - - - - - - - - - - - - - - - - - - -+
   :  Profile:   openai                              :
   :  Config:    /Users/you/.dbgpt/configs/openai.toml:
   :  Workspace: /Users/you/.dbgpt/workspace          :
   +- - - - - - - - - - - - - - - - - - - - - - - -+
```

## 3. 打开 Web UI

然后打开 [http://localhost:5670](http://localhost:5670)。

---

## 4. 命令参考

### 总览

```
dbgpt [OPTIONS] COMMAND [ARGS]...

Options:
  --log-level TEXT   Log level (default: warn)
  --version          Show version and exit
  --help             Show help message

Commands:
  start     Start the InsightAgent server
  stop      Stop a running server
  setup     Configure LLM provider (interactive wizard or CI mode)
  profile   Manage configuration profiles
  knowledge Knowledge base operations
  model     Manage model serving
  db        Database management and migration
  ...
```

---

### `dbgpt start`

启动 InsightAgent web server。直接运行 `dbgpt start` 等价于 `dbgpt start web`。

#### 子命令

| 子命令 | 说明 |
|---|---|
| `web`（或 `webserver`） | 启动 web server（默认） |
| `none` | 仅 API 模式 —— *未来版本计划支持* |
| `controller` | 启动模型 controller |
| `worker` | 启动模型 worker |
| `apiserver` | 启动 API server |

#### `dbgpt start web` 参数

| 参数 | Short | 类型 | 默认值 | 说明 |
|---|---|---|---|---|
| `--config` | `-c` | PATH | *auto* | TOML 配置文件路径。若未提供，则使用当前 active profile，或自动启动配置向导。 |
| `--profile` | `-p` | TEXT | *active* | Provider profile 名称（`openai`、`kimi`、`qwen`、`minimax`、`glm`、`custom`）。会覆盖当前 active profile。 |
| `--yes` | `-y` | FLAG | false | 非交互模式：跳过向导，直接使用默认值 / 环境变量，适合 CI/CD。 |
| `--api-key` | | TEXT | *env* | 指定 provider 的 API key，也可通过对应环境变量提供。 |
| `--daemon` | `-d` | FLAG | false | 后台守护进程方式运行。可通过 `dbgpt stop webserver` 停止。 |

#### 示例

```bash
# 首次运行，使用交互式向导
dbgpt start

# 使用现有 profile
dbgpt start web --profile openai

# 非交互方式并显式传入 API key
dbgpt start web --profile kimi --api-key sk-xxx --yes

# 使用指定配置文件
dbgpt start web --config /path/to/my-config.toml

# 以 daemon 方式运行
dbgpt start web --daemon
```

#### 配置解析优先级

启动 web server 时，配置文件的解析顺序如下：

1. **`--config` 参数** —— 如果提供，直接使用这个文件
2. **`--profile` 参数** —— 查找 `~/.dbgpt/configs/<profile>.toml`
3. **Active profile** —— 从 `~/.dbgpt/config.toml` 中读取
4. **配置向导** —— 如果还没有配置，则自动启动交互式向导

---

### `dbgpt stop`

停止正在运行的 InsightAgent 服务进程。

```bash
# 停止 web server
dbgpt stop webserver

# 停止指定端口上的 web server
dbgpt stop webserver --port 5670

# 停止所有服务
dbgpt stop all
```

---

### `dbgpt setup`

交互式配置 LLM provider，或用于非交互 / CI 模式配置。这个命令会把 TOML 配置写入 `~/.dbgpt/configs/<profile>.toml`，并将它标记为 active profile。

#### 参数

| 参数 | Short | 类型 | 默认值 | 说明 |
|---|---|---|---|---|
| `--profile` | `-p` | TEXT | *interactive* | 要配置的 provider profile。若省略，则显示交互菜单。 |
| `--yes` | `-y` | FLAG | false | 非交互模式：跳过向导并使用默认值。 |
| `--api-key` | | TEXT | *env* | API key，也会读取 `DBGPT_API_KEY` 环境变量。 |
| `--show` | | FLAG | false | 显示当前 active profile 和配置路径后退出。 |

#### 示例

```bash
# 交互式向导
dbgpt setup

# 非交互：使用 OpenAI + 环境变量
export OPENAI_API_KEY=sk-xxx
dbgpt setup --profile openai --yes

# 非交互：显式传入 key
dbgpt setup --profile kimi --api-key sk-xxx

# 查看当前配置
dbgpt setup --show
```

---

### `dbgpt profile`

管理多个配置 profile。每个 profile 都是 `~/.dbgpt/configs/` 下的一个 TOML 文件。

#### 子命令

| 子命令 | 说明 |
|---|---|
| `list` | 列出所有 profile，active 的会用 `*` 标记 |
| `show <name>` | 显示某个 profile 的 TOML 内容 |
| `create <name>` | 使用配置向导创建（或重新配置）一个 profile |
| `switch <name>` | 将某个 profile 设为当前默认 |
| `delete <name>` | 删除某个 profile 配置文件 |

#### 示例

```bash
# 列出所有 profile
dbgpt profile list
#   openai     ← no asterisk
# * kimi       ← active

# 查看 profile 内容
dbgpt profile show openai

# 创建新 profile
dbgpt profile create qwen

# 切换 active profile
dbgpt profile switch openai

# 删除 profile
dbgpt profile delete minimax
dbgpt profile delete minimax --yes  # 跳过确认
```

---

## 5. 支持的 Providers

配置向导和 `--profile` 参数支持以下 provider：

| Profile 名称 | 显示名称 | LLM 模型 | Embedding 模型 | API Key 环境变量 |
|---|---|---|---|---|
| `openai` | OpenAI | gpt-4o | text-embedding-3-small | `OPENAI_API_KEY` |
| `kimi` | Kimi | kimi-k2 | text-embedding-v3 | `MOONSHOT_API_KEY`（embedding 同时需要 `DASHSCOPE_API_KEY`） |
| `qwen` | Qwen | qwen-plus | text-embedding-v3 | `DASHSCOPE_API_KEY` |
| `minimax` | MiniMax | abab6.5s-chat | embo-01 | `MINIMAX_API_KEY` |
| `glm` | Z.AI | glm-4-plus | embedding-3 | `ZHIPUAI_API_KEY` |
| `custom` | Custom | gpt-4o | text-embedding-3-small | `OPENAI_API_KEY` |

:::info
**Custom** profile 可以连接任意 OpenAI 兼容 API endpoint。在向导中你会被要求输入 API Base URL。
:::

---

## 6. 目录结构

首次运行后，InsightAgent 会在用户目录下创建如下结构：

```
~/.dbgpt/
├── config.toml              # 记录当前 active profile 名称
├── configs/
│   ├── openai.toml          # OpenAI profile
│   ├── kimi.toml            # Kimi profile
│   └── ...                  # 每个 profile 对应一个文件
└── workspace/
    └── pilot/               # 运行时工作区（数据库、数据文件等）
        ├── meta_data/
        │   └── dbgpt.db     # SQLite 元数据库
        └── data/            # 向量数据存储
```

### 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `DBGPT_HOME` | `~/.dbgpt` | 覆盖 InsightAgent home 目录 |
| `OPENAI_API_KEY` | — | OpenAI API key（也用于 `openai` 和 `custom` profile） |
| `MOONSHOT_API_KEY` | — | Kimi / Moonshot API key |
| `DASHSCOPE_API_KEY` | — | Qwen / DashScope API key（也用于 Kimi embedding） |
| `MINIMAX_API_KEY` | — | MiniMax API key |
| `ZHIPUAI_API_KEY` | — | Z.AI / Zhipu API key |
| `DBGPT_API_KEY` | — | 通用 API key（`--api-key` 的 fallback） |
| `DBGPT_LANG` | `en` | UI 语言（`en` 或 `zh`） |

---

## 7. 常见工作流

### 首次安装

```bash
pip install dbgpt-app
dbgpt start
# Follow the wizard → choose provider → enter API key → server starts
```

### 在不同 provider 间切换

```bash
# 创建一个 Kimi profile
dbgpt profile create kimi

# 切换到它
dbgpt profile switch kimi

# 使用新 profile 启动
dbgpt start
```

### CI/CD 部署

```bash
export OPENAI_API_KEY=sk-xxx
dbgpt setup --profile openai --yes
dbgpt start web --daemon
```

### 自定义 endpoint（例如 Azure OpenAI、local vLLM）

```bash
dbgpt setup --profile custom
# Wizard will ask for:
#   - API base URL (e.g. http://localhost:8000/v1)
#   - API key
#   - Model names
```

---

## 8. 可选模块

默认 `pip install dbgpt-app` 会包含核心框架。你也可以通过 extras 为 LLM provider、vector store、data source 等增加能力。

### LLM Providers

| Extra | Provider | 关键包 |
|-------|----------|-------------|
| `proxy_openai` | OpenAI、Kimi、Qwen、MiniMax、Z.AI 以及任意 OpenAI-compatible API | `openai`, `tiktoken` |
| `proxy_ollama` | Ollama（本地模型） | `ollama` |
| `proxy_zhipuai` | Zhipu AI（GLM） | `openai` |
| `proxy_tongyi` | Tongyi Qianwen | `openai`, `dashscope` |
| `proxy_qianfan` | 百度千帆 | `qianfan` |
| `proxy_anthropic` | Anthropic Claude | `anthropic` |

### Vector Stores

| Extra | 存储 | 关键包 |
|-------|---------|-------------|
| `storage_chromadb` | ChromaDB | `chromadb`, `onnxruntime` |
| `storage_milvus` | Milvus | `pymilvus` |
| `storage_weaviate` | Weaviate | `weaviate-client` |
| `storage_elasticsearch` | Elasticsearch | `elasticsearch` |
| `storage_obvector` | OBVector | `pyobvector` |

### Knowledge & RAG

| Extra | 增加能力 | 关键包 |
|-------|-------------|-------------|
| `rag` | 文档解析（PDF、DOCX、PPTX、Markdown、HTML） | `spacy`, `pypdf`, `python-docx`, `python-pptx` |
| `graph_rag` | 基于 TuGraph / Neo4j 的 Graph RAG | `networkx`, `neo4j` |

### Data Sources

| Extra | 数据库 | 关键包 |
|-------|----------|-------------|
| `datasource_mysql` | MySQL | `mysqlclient` |
| `datasource_postgres` | PostgreSQL | `psycopg2-binary` |
| `datasource_clickhouse` | ClickHouse | `clickhouse-connect` |
| `datasource_oracle` | Oracle | `oracledb` |
| `datasource_mssql` | SQL Server | `pymssql` |
| `datasource_spark` | Apache Spark | `pyspark` |
| `datasource_hive` | Hive | `pyhive` |
| `datasource_vertica` | Vertica | `vertica-python` |

### 组合多个 extras 的示例

```bash
# OpenAI + ChromaDB + RAG + MySQL
pip install "dbgpt-app[proxy_openai,storage_chromadb,rag,datasource_mysql]"
```

:::tip 最小安装
如果你只需要核心框架而不需要任何 LLM 或存储支持：
```bash
pip install dbgpt-app
```
这会提供 CLI、FastAPI server 和 agent framework，但要真正使用它，至少还需要安装一个 LLM provider extra。
:::

---

## 9. 故障排查

### 端口已被占用

```bash
# 停止已有 web server
dbgpt stop webserver --port 5670

# 或改配置文件换端口
# [service.web]
# port = 5671
```

### 提示 “No config file found”

这说明当前还没有配置任何 profile，请运行：

```bash
dbgpt setup
```

### 更换 API Key

重新对同一个 profile 运行 setup 向导即可覆盖原配置：

```bash
dbgpt setup --profile openai
# 或者直接编辑 ~/.dbgpt/configs/openai.toml
```

### 查看当前配置

```bash
dbgpt setup --show
dbgpt profile show openai
```

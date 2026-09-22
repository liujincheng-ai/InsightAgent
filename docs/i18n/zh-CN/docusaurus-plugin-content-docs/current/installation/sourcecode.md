# 源码部署

## 环境要求

| 启动模式 | CPU * 内存 | GPU | 说明 |
|:--------------------:|:------------:|:--------------:|:---------------:|
| 代理模型 | 4C * 8G | 无 | 代理模式不依赖 GPU |
| 本地模型 | 8C * 32G | 24G | 建议本地使用 24G 及以上显存的 GPU |


## 环境准备

### 下载源码

:::tip
下载 InsightAgent
:::

```bash
git clone https://github.com/liujincheng-ai/InsightAgent.git
```

:::info note
uv 有多种安装方式：
:::

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

<Tabs
  defaultValue="uv_sh"
  values={[
    {label: '命令（macOS / Linux）', value: 'uv_sh'},
    {label: 'PyPI', value: 'uv_pypi'},
    {label: '其他', value: 'uv_other'},
  ]}>
  <TabItem value="uv_sh" label="命令">
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```
  </TabItem>

  <TabItem value="uv_pypi" label="PyPI">
使用 pipx 安装 uv。

```bash
python -m pip install --upgrade pip
python -m pip install --upgrade pipx
python -m pipx ensurepath
pipx install uv --global
```
  </TabItem>

  <TabItem value="uv_other" label="其他">

更多安装方式请参考 [uv 官方安装文档](https://docs.astral.sh/uv/getting-started/installation/)
  </TabItem>

</Tabs>

安装完成后，可以通过 `uv --version` 检查是否安装成功。

```bash
uv --version
```

## 部署 InsightAgent

### 安装依赖

<Tabs
  defaultValue="openai"
  values={[
    {label: 'OpenAI（代理）', value: 'openai'},
    {label: 'DeepSeek（代理）', value: 'deepseek'},
    {label: 'GLM4（本地）', value: 'glm-4'},
  ]}>

  <TabItem value="openai" label="OpenAI（代理）">

```bash
# 使用 uv 安装 OpenAI 代理模式所需依赖
uv sync --all-packages \
--extra "base" \
--extra "proxy_openai" \
--extra "rag" \
--extra "storage_chromadb" \
--extra "dbgpts"
```

### 启动 Webserver

如果要通过 OpenAI 代理运行 InsightAgent，需要在 `configs/dbgpt-proxy-openai.toml` 配置文件中填入 OpenAI API Key，或者通过环境变量 `OPENAI_API_KEY` 提供。

```toml
# Model Configurations
[models]
[[models.llms]]
...
api_key = "your-openai-api-key"
[[models.embeddings]]
...
api_key = "your-openai-api-key"
```

然后执行以下命令启动 webserver：

```bash
uv run dbgpt start webserver --config configs/dbgpt-proxy-openai.toml
```
上面命令中的 `--config` 用于指定配置文件，`configs/dbgpt-proxy-openai.toml` 是 OpenAI 代理模型的配置文件。你也可以根据需要使用其他配置文件或自定义配置文件。

你也可以使用下面的命令启动 webserver：
```bash
uv run python packages/dbgpt-app/src/dbgpt_app/dbgpt_server.py --config configs/dbgpt-proxy-openai.toml
```

  </TabItem>
 <TabItem value="deepseek" label="DeepSeek（代理）">

```bash
# 使用 uv 安装 DeepSeek 代理模式所需依赖
uv sync --all-packages \
--extra "base" \
--extra "proxy_openai" \
--extra "rag" \
--extra "storage_chromadb" \
--extra "dbgpts"
```

### 启动 Webserver

如果要通过 DeepSeek 代理运行 InsightAgent，需要在 `configs/dbgpt-proxy-deepseek.toml` 中配置 DeepSeek API Key。

你也可以在 `configs/dbgpt-proxy-deepseek.toml` 中指定 embedding 模型。默认 embedding 模型是 `BAAI/bge-large-zh-v1.5`。如果想使用其他 embedding 模型，可以修改 `[[models.embeddings]]` 部分中的 `name` 和 `provider`，其中 provider 可以设为 `hf`。

```toml
# Model Configurations
[models]
[[models.llms]]
# name = "deepseek-chat"
name = "deepseek-reasoner"
provider = "proxy/deepseek"
api_key = "your-deepseek-api-key"
[[models.embeddings]]
name = "BAAI/bge-large-zh-v1.5"
provider = "hf"
# If not provided, the model will be downloaded from the Hugging Face model hub
# uncomment the following line to specify the model path in the local file system
# path = "the-model-path-in-the-local-file-system"
path = "/data/models/bge-large-zh-v1.5"
```

然后执行以下命令启动 webserver：

```bash
uv run dbgpt start webserver --config configs/dbgpt-proxy-deepseek.toml
```
上面命令中的 `--config` 用于指定配置文件，`configs/dbgpt-proxy-deepseek.toml` 是 DeepSeek 代理模型的配置文件。你也可以根据需要使用其他配置文件或自定义配置文件。

你也可以使用下面的命令启动 webserver：
```bash
uv run python packages/dbgpt-app/src/dbgpt_app/dbgpt_server.py --config configs/dbgpt-proxy-deepseek.toml
```

  </TabItem>
  <TabItem value="glm-4" label="GLM4（本地）">

```bash
# 使用 uv 安装 GLM4 所需依赖
# 安装核心依赖并按需选择扩展
uv sync --all-packages \
--extra "base" \
--extra "cuda121" \
--extra "hf" \
--extra "rag" \
--extra "storage_chromadb" \
--extra "quant_bnb" \
--extra "dbgpts"
```

### 启动 Webserver

如果要通过本地模型运行 InsightAgent，可以修改 `configs/dbgpt-local-glm.toml` 来指定模型路径和其他参数。

```toml
# Model Configurations
[models]
[[models.llms]]
name = "THUDM/glm-4-9b-chat-hf"
provider = "hf"
# If not provided, the model will be downloaded from the Hugging Face model hub
# uncomment the following line to specify the model path in the local file system
# path = "the-model-path-in-the-local-file-system"

[[models.embeddings]]
name = "BAAI/bge-large-zh-v1.5"
provider = "hf"
# If not provided, the model will be downloaded from the Hugging Face model hub
# uncomment the following line to specify the model path in the local file system
# path = "the-model-path-in-the-local-file-system"
```
在上述配置中，`[[models.llms]]` 表示 LLM 模型，`[[models.embeddings]]` 表示 embedding 模型。如果不提供 `path` 参数，系统会根据 `name` 从 Hugging Face 模型仓库下载模型。

然后执行以下命令启动 webserver：

```bash
uv run dbgpt start webserver --config configs/dbgpt-local-glm.toml
```

  </TabItem>
</Tabs>


## 访问网站

打开浏览器访问 [`http://localhost:5670`](http://localhost:5670)

### （可选）单独运行 Web 前端

你也可以单独运行 Web 前端：

```bash
cd web && npm install
cp .env.template .env
// Set API_BASE_URL to your InsightAgent server address, usually http://localhost:5670
npm run dev
```
Open your browser and visit [`http://localhost:3000`](http://localhost:3000)


## 安装 InsightAgent 应用数据库
<Tabs
  defaultValue="sqlite"
  values={[
    {label: 'SQLite', value: 'sqlite'},
    {label: 'MySQL', value: 'mysql'},
  ]}>
<TabItem value="sqlite" label="sqlite">

:::tip NOTE

在 SQLite 下，你不需要手动创建 InsightAgent 应用相关的数据表；
默认会自动创建。

:::

修改 toml 配置文件以使用 SQLite 作为数据库（这也是默认设置）。
```toml
[service.web.database]
type = "sqlite"
path = "pilot/meta_data/dbgpt.db"
```


 </TabItem>
<TabItem value="mysql" label="MySQL">

:::warning NOTE

从 0.4.7 版本之后，出于安全考虑，我们移除了 MySQL Schema 的自动创建功能。

:::

1. 首先执行 MySQL 脚本创建数据库和表。

```bash
$ mysql -h127.0.0.1 -uroot -p{your_password} < ./assets/schema/dbgpt.sql
```

2. 然后修改 toml 配置文件以使用 MySQL。

```toml
[service.web.database]
type = "mysql"
host = "127.0.0.1"
port = 3306
user = "root"
database = "dbgpt"
password = "aa123456"
```
请将 `host`、`port`、`user`、`database` 和 `password` 替换为你自己的 MySQL 配置。

  </TabItem>
</Tabs>


## 测试数据（可选）
InsightAgent 默认内置了一部分测试数据，你可以通过以下命令将其加载到本地数据库中进行测试。
- **Linux**

```bash
bash ./scripts/examples/load_examples.sh

```
- **Windows**

```bash
.\scripts\examples\load_examples.bat
```

:::

## 访问网站
打开浏览器访问 [`http://localhost:5670`](http://localhost:5670)

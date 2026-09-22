import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

# Docker 部署

## Docker 镜像准备

准备 Docker 镜像有两种方式：
1. 直接拉取官方镜像
2. 本地构建，参考 [构建 Docker 镜像](./build_image.md)

实际使用时二选一即可。


## 使用代理模型部署

这种部署方式不需要 GPU 环境。

1. 从官方镜像仓库拉取镜像：[Eosphoros AI Docker Hub](https://hub.docker.com/u/eosphorosai)

```bash
docker pull eosphorosai/dbgpt-openai:latest
```

2. 运行 Docker 容器

此示例要求你提供可用的 SiliconFlow API Key。你可以在 [SiliconFlow](https://siliconflow.cn/) 注册，并在 [API Key 页面](https://cloud.siliconflow.cn/account/ak) 创建。也可以通过设置 `AIMLAPI_API_KEY` 来使用 AI/ML API 服务。


```bash
docker run -it --rm -e SILICONFLOW_API_KEY=${SILICONFLOW_API_KEY} \
 -p 5670:5670 --name dbgpt eosphorosai/dbgpt-openai
```
或者使用 AI/ML API：
```bash
docker run -it --rm -e AIMLAPI_API_KEY=${AIMLAPI_API_KEY} \
 -p 5670:5670 --name dbgpt eosphorosai/dbgpt-openai
```

请将 `${SILICONFLOW_API_KEY}` 或 `${AIMLAPI_API_KEY}` 替换成你自己的 API Key。


之后就可以在浏览器访问 [http://localhost:5670](http://localhost:5670)。


## 使用 GPU（本地模型）部署

这种部署方式需要 GPU 环境。

在运行 Docker 容器之前，需要先安装 NVIDIA Container Toolkit。详情请参考官方文档：[NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)。

在这种部署方式中，你将使用本地模型，而不是在容器中临时从 Hugging Face 或 ModelScope 下载。如果你已经提前把模型下载到本地，或者想使用其他来源的模型，这种方式会更方便。

### 第 1 步：下载模型

在运行 Docker 容器之前，需要先将模型下载到本地机器。你可以选择 Hugging Face 或 ModelScope（中国用户推荐）进行下载。

<Tabs>
<TabItem value="modelscope" label="从 ModelScope 下载">

1. 如果还没有安装，请先安装 `git` 和 `git-lfs`：

   ```bash
   sudo apt-get install git git-lfs
   ```

2. 在当前工作目录创建 `models` 目录：

   ```bash
   mkdir -p ./models
   ```

3. 使用 `git` 将模型仓库克隆到 `models` 目录：

   ```bash
   cd ./models
   git lfs install
   git clone https://www.modelscope.cn/Qwen/Qwen2.5-Coder-0.5B-Instruct.git
   git clone https://www.modelscope.cn/BAAI/bge-large-zh-v1.5.git
   cd ..
   ```

   模型会被下载到 `./models/Qwen2.5-Coder-0.5B-Instruct` 和 `./models/bge-large-zh-v1.5` 目录下。

</TabItem>
<TabItem value="huggingface" label="从 Hugging Face 下载">

1. 如果还没有安装，请先安装 `git` 和 `git-lfs`：

   ```bash
   sudo apt-get install git git-lfs
   ```

2. 在当前工作目录创建 `models` 目录：

   ```bash
   mkdir -p ./models
   ```

3. 使用 `git` 将模型仓库克隆到 `models` 目录：

   ```bash
   cd ./models
   git lfs install
   git clone https://huggingface.co/Qwen/Qwen2.5-Coder-0.5B-Instruct
   git clone https://huggingface.co/BAAI/bge-large-zh-v1.5
   cd ..
   ```

   模型会被下载到 `./models/Qwen2.5-Coder-0.5B-Instruct` 和 `./models/bge-large-zh-v1.5` 目录下。

</TabItem>
</Tabs>

---

### 第 2 步：准备配置文件

创建一个名为 `dbgpt-local-gpu.toml` 的配置文件，并填入以下内容：

```toml
[models]
[[models.llms]]
name = "Qwen2.5-Coder-0.5B-Instruct"
provider = "hf"
# 指定模型在本地文件系统中的路径
path = "/app/models/Qwen2.5-Coder-0.5B-Instruct"

[[models.embeddings]]
name = "BAAI/bge-large-zh-v1.5"
provider = "hf"
# 指定模型在本地文件系统中的路径
path = "/app/models/bge-large-zh-v1.5"
```

该配置文件用于指定 Docker 容器内模型的本地挂载路径。

---

### 第 3 步：运行 Docker 容器

运行 Docker 容器，并挂载本地 `models` 目录：

```bash
docker run --ipc host --gpus all \
  -it --rm \
  -p 5670:5670 \
  -v ./dbgpt-local-gpu.toml:/app/configs/dbgpt-local-gpu.toml \
  -v ./models:/app/models \
  --name dbgpt \
  eosphorosai/dbgpt \
  dbgpt start webserver --config /app/configs/dbgpt-local-gpu.toml
```

#### 命令说明：
- `--ipc host`：启用 host IPC 模式以获得更好的性能。
- `--gpus all`：允许容器使用所有可用 GPU。
- `-v ./dbgpt-local-gpu.toml:/app/configs/dbgpt-local-gpu.toml`：将本地配置文件挂载到容器内。
- `-v ./models:/app/models`：将本地 `models` 目录挂载到容器内。
- `eosphorosai/dbgpt`：使用的 Docker 镜像。
- `dbgpt start webserver --config /app/configs/dbgpt-local-gpu.toml`：使用指定配置文件启动 webserver。

---

### 第 4 步：访问应用

容器启动后，可以在浏览器访问 [http://localhost:5670](http://localhost:5670)。

---

### 第 5 步：持久化数据（可选）

为了避免容器停止或删除后数据丢失，你可以把 `pilot/data` 和 `pilot/message` 目录映射到本地机器。这两个目录用于保存应用数据和消息。

1. 创建本地目录用于数据持久化：

   ```bash
   mkdir -p ./pilot/data
   mkdir -p ./pilot/message
   mkdir -p ./pilot/alembic_versions
   ```

2. 修改 `dbgpt-local-gpu.toml` 中的路径配置：

   ```toml
   [service.web.database]
   type = "sqlite"
   path = "/app/pilot/message/dbgpt.db"
   ```

3. 运行 Docker 容器并增加额外挂载：

   ```bash
   docker run --ipc host --gpus all \
     -it --rm \
     -p 5670:5670 \
     -v ./dbgpt-local-gpu.toml:/app/configs/dbgpt-local-gpu.toml \
     -v ./models:/app/models \
     -v ./pilot/data:/app/pilot/data \
     -v ./pilot/message:/app/pilot/message \
     -v ./pilot/alembic_versions:/app/pilot/meta_data/alembic/versions \
     --name dbgpt \
     eosphorosai/dbgpt \
     dbgpt start webserver --config /app/configs/dbgpt-local-gpu.toml
   ```

   这样可以保证 `pilot/data` 和 `pilot/message` 目录中的数据持久化到本地。

---

### 目录结构示例

完成后，目录结构大致如下：

```
.
├── dbgpt-local-gpu.toml
├── models
│   ├── Qwen2.5-Coder-0.5B-Instruct
│   └── bge-large-zh-v1.5
├── pilot
│   ├── data
│   └── message
```

这种方式可以确保模型和应用数据保存在本地，并挂载到 Docker 容器中，避免数据丢失。
```

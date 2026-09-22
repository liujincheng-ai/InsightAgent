---
sidebar_position: 1
title: 安装问题
---

# 安装问题

这里整理了 InsightAgent 安装过程中常见的问题及对应的解决方法。

## Python 版本错误

**现象：** 出现 `Python 3.10+ required` 或版本不匹配相关报错。

**解决方法：**

```bash
python --version
# 必须为 3.10 或更高版本
```

如果你的环境中存在多个 Python 版本，可以显式指定使用的版本：

```bash
uv python pin 3.11
uv sync --all-packages ...
```

## 找不到 uv

**现象：** `command not found: uv`

**解决方法：**

```bash
# 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 验证
uv --version
```

如果已经安装但仍然找不到命令，请确认它已加入 PATH：

```bash
export PATH="$HOME/.local/bin:$PATH"
```

## 依赖解析失败

**现象：** `uv sync` 因依赖冲突而失败。

**解决方法：**

1. 确认你使用的是最新版本的 uv：

```bash
uv self update
```

2. 清理缓存后重试：

```bash
uv cache clean
uv sync --all-packages --extra "base" ...
```

3. 如果你使用国内镜像，可以设置索引地址：

```bash
UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple uv sync --all-packages ...
```

## 原生扩展构建失败

**现象：** 在 `uv sync` 过程中出现编译错误，尤其常见于 `tokenizers`、`grpcio`、`psutil` 等包。

**解决方法：**

先安装构建工具：

```bash
# Ubuntu/Debian
sudo apt-get install build-essential python3-dev

# macOS
xcode-select --install

# CentOS/RHEL
sudo yum groupinstall "Development Tools"
```

对于依赖 Rust 的包（例如 `tokenizers`）：

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source $HOME/.cargo/env
```

## CUDA / GPU 问题

**现象：** `CUDA not available` 或无法检测到 GPU。

**解决方法：**

1. 验证 CUDA 是否安装正确：

```bash
nvidia-smi
# 应显示 GPU 信息以及 CUDA 版本
```

2. 安装匹配的 CUDA extra：

```bash
# 对应 CUDA 12.1
uv sync --all-packages --extra "cuda121" ...

# 对应 CUDA 12.4
uv sync --all-packages --extra "cuda124" ...
```

3. 验证 PyTorch 是否能识别 GPU：

```bash
uv run python -c "import torch; print(torch.cuda.is_available())"
```

## 端口冲突

**现象：** 5670 端口提示 `Address already in use`。

**解决方法：**

```bash
# 查找占用该端口的进程
lsof -i :5670

# 结束该进程
kill -9 <PID>
```

或者改用其他端口启动：

```bash
uv run dbgpt start webserver --config configs/your-config.toml --port 5671
```

## Docker 相关问题

### 权限不足

**现象：** 执行 Docker 命令时出现 `permission denied`。

**解决方法：**

```bash
# 将当前用户加入 docker 用户组
sudo usermod -aG docker $USER
# 退出并重新登录
```

### 找不到 NVIDIA runtime

**现象：** `docker: Error response from daemon: could not select device driver`

**解决方法：** 安装 NVIDIA Container Toolkit：

```bash
# Ubuntu
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/libnvidia-container/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

## 数据库问题

### MySQL 连接被拒绝

**现象：** 启动时出现 `Can't connect to MySQL server`。

**解决方法：**

1. 验证 MySQL 是否已启动：

```bash
mysql -h127.0.0.1 -uroot -p -e "SELECT 1"
```

2. 检查配置值是否与你的 MySQL 实例一致：

```toml
[service.web.database]
type = "mysql"
host = "127.0.0.1"    # 不要写成 'localhost'，请直接使用 IP
port = 3306
user = "root"
database = "dbgpt"
password = "your-password"
```

3. 如果数据库不存在，先创建：

```bash
mysql -h127.0.0.1 -uroot -p < ./assets/schema/dbgpt.sql
```

## 还是没解决？

- 查看更详细的 [FAQ](/docs/faq/install)
- 搜索 [GitHub Issues](https://github.com/liujincheng-ai/InsightAgent/issues)
- 在 [GitHub Discussions](https://github.com/liujincheng-ai/InsightAgent/discussions) 中提问

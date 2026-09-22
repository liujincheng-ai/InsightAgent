# MySQL

MySQL 是广泛使用的开源关系型数据库系统。InsightAgent 在
`dbgpt_ext.datasource.rdbms.conn_mysql` 中内置了原生 MySQL 数据源连接器。

### 安装依赖

首先安装 MySQL 数据源所需依赖。

```bash
uv sync --all-packages \
--extra "base" \
--extra "datasource_mysql" \
--extra "rag" \
--extra "storage_chromadb" \
--extra "dbgpts"
```

### 准备 MySQL

准备好 MySQL 服务与数据库后，启动 InsightAgent WebServer：

```bash
uv run dbgpt start webserver --config configs/dbgpt-proxy-openai.toml
```

也可以使用：

```bash
uv run python packages/dbgpt-app/src/dbgpt_app/dbgpt_server.py --config configs/dbgpt-proxy-openai.toml
```

### MySQL 配置

在数据源 UI 或配置参数中填写：

- host
- port
- user
- password
- database
- driver (`mysql+pymysql`)

对应实现文件：

- `packages/dbgpt-ext/src/dbgpt_ext/datasource/rdbms/conn_mysql.py`

# StarRocks

StarRocks 是高性能分析型数据库。InsightAgent 通过
`dbgpt_ext.datasource.rdbms.conn_starrocks` 中的原生连接器提供支持。

### 安装依赖

请安装基础依赖，以及运行环境中所需的 StarRocks SQLAlchemy driver。

```bash
uv sync --all-packages \
--extra "base" \
--extra "rag" \
--extra "storage_chromadb" \
--extra "dbgpts"
```

### 准备 StarRocks

准备好 StarRocks 实例后，启动 InsightAgent WebServer：

```bash
uv run dbgpt start webserver --config configs/dbgpt-proxy-openai.toml
```

### StarRocks 配置

在数据源 UI 或配置参数中填写：

- host
- port
- user
- password
- database
- driver (`starrocks`)

对应实现文件：

- `packages/dbgpt-ext/src/dbgpt_ext/datasource/rdbms/conn_starrocks.py`

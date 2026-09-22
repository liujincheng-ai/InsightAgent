# GaussDB

GaussDB 是企业级关系型数据库。InsightAgent 通过
`dbgpt_ext.datasource.rdbms.conn_gaussdb` 中的原生连接器提供支持。

### 安装依赖

GaussDB 使用 PostgreSQL 兼容 driver 路径。

```bash
uv sync --all-packages \
--extra "base" \
--extra "datasource_postgres" \
--extra "rag" \
--extra "storage_chromadb" \
--extra "dbgpts"
```

### 准备 GaussDB

准备好 GaussDB 实例后，启动 InsightAgent WebServer：

```bash
uv run dbgpt start webserver --config configs/dbgpt-proxy-openai.toml
```

### GaussDB 配置

在数据源 UI 或配置参数中填写：

- host
- port
- user
- password
- database
- schema
- driver (`postgresql+psycopg2`)

对应实现文件：

- `packages/dbgpt-ext/src/dbgpt_ext/datasource/rdbms/conn_gaussdb.py`

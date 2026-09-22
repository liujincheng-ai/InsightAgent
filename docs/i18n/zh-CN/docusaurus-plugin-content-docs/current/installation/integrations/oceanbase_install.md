# OceanBase

OceanBase 是分布式 SQL 数据库，InsightAgent 通过
`dbgpt_ext.datasource.rdbms.conn_oceanbase` 中的原生连接器提供支持。

### 安装依赖

OceanBase 连接器基于与 MySQL 兼容的 OceanBase driver 路径。

```bash
uv sync --all-packages \
--extra "base" \
--extra "rag" \
--extra "storage_chromadb" \
--extra "dbgpts"
```

### 准备 OceanBase

准备好 OceanBase 实例后，启动 InsightAgent WebServer：

```bash
uv run dbgpt start webserver --config configs/dbgpt-proxy-openai.toml
```

### OceanBase 配置

在数据源 UI 或配置参数中填写：

- host
- port
- user
- password
- database
- driver (`mysql+ob`)

对应实现文件：

- `packages/dbgpt-ext/src/dbgpt_ext/datasource/rdbms/conn_oceanbase.py`

# Apache Doris

Apache Doris 是面向实时分析场景的数据仓库。InsightAgent 通过
`dbgpt_ext.datasource.rdbms.conn_doris` 中的原生连接器提供支持。

### 安装依赖

Doris 使用与 MySQL 兼容的 driver 路径。

```bash
uv sync --all-packages \
--extra "base" \
--extra "datasource_mysql" \
--extra "rag" \
--extra "storage_chromadb" \
--extra "dbgpts"
```

### 准备 Apache Doris

准备好 Doris 实例后，启动 InsightAgent WebServer：

```bash
uv run dbgpt start webserver --config configs/dbgpt-proxy-openai.toml
```

### Apache Doris 配置

在数据源 UI 或配置参数中填写：

- host
- port
- user
- password
- database
- driver (`mysql+pymysql`)

对应实现文件：

- `packages/dbgpt-ext/src/dbgpt_ext/datasource/rdbms/conn_doris.py`

# Vertica

Vertica 是分析型 SQL 数据仓库。InsightAgent 通过
`dbgpt_ext.datasource.rdbms.conn_vertica` 中的原生连接器提供支持。

### 安装依赖

安装 Vertica 数据源扩展：

```bash
uv sync --all-packages \
--extra "base" \
--extra "datasource_vertica" \
--extra "rag" \
--extra "storage_chromadb" \
--extra "dbgpts"
```

### 准备 Vertica

准备好 Vertica 实例后，启动 InsightAgent WebServer：

```bash
uv run dbgpt start webserver --config configs/dbgpt-proxy-openai.toml
```

### Vertica 配置

在数据源 UI 或配置参数中填写：

- host
- port
- user
- password
- database
- driver (`vertica+vertica_python`)

对应实现文件：

- `packages/dbgpt-ext/src/dbgpt_ext/datasource/rdbms/conn_vertica.py`

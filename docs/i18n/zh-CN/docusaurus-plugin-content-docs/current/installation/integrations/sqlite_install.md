# SQLite

SQLite 是轻量级嵌入式关系型数据库。InsightAgent 在
`dbgpt_ext.datasource.rdbms.conn_sqlite` 中内置了原生 SQLite 连接器。

### 安装依赖

SQLite 支持已包含在基础安装中，不需要额外的数据源扩展包。

```bash
uv sync --all-packages \
--extra "base" \
--extra "rag" \
--extra "storage_chromadb" \
--extra "dbgpts"
```

### 准备 SQLite

准备一个 SQLite 数据库文件路径，例如 `./data/demo.db`，然后启动服务：

```bash
uv run dbgpt start webserver --config configs/dbgpt-proxy-openai.toml
```

### SQLite 配置

在数据源 UI 或配置参数中填写：

- path
- check_same_thread
- driver (`sqlite`)

对应实现文件：

- `packages/dbgpt-ext/src/dbgpt_ext/datasource/rdbms/conn_sqlite.py`

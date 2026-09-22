# InsightAgent V0.8.0 — 范式跃迁：AI + Data 驱动的数据分析交互体验升级

一次从"对话问答"到"任务交付"的范式跃迁，从「被动问答」到「自主分析」，探索真正的 Agentic 生产力。

## 简介

InsightAgent V0.8.0 带来了自主驱动的 AI 数据助理，能够自主完成整个分析流水线：

🎯 业务目标 → 🧠 任务拆解 → 🧩 技能调用 → 💻 代码生成（SQL/Python） → 🛡️ 沙箱执行 → 📊 图表生成 → 📝 报告交付

你不再需要知道数据存在哪张表里，也不必为中间的数据清洗编写 Python 脚本。你只需要给出业务目标，**InsightAgent AI 数据助理**会为你打理好一切。

### 关键特性速览

- 🌟 **自主数据分析产品** — 全新升级的自主数据分析体验，通过 Skill 编排 AI 数据分析
- 🤖 **智能体技能支持** — 支持智能体（Agent）技能，赋能更强大、更灵活的智能体能力
- 📊 **自主 SQL 生成** — AI 智能体可自主编写 SQL 查询语句进行数据分析
- 💻 **自主代码编写** — AI 智能体可自动生成并执行 Python 代码，完成数据分析任务
- 🛡️ **沙箱环境支持** — 提供安全隔离的沙箱环境，用于执行不受信任的代码
- 💬 **对话分享与回放** — 不仅能看到最终精美的 HTML 报告，还能回放推理过程
- 🚀 **一键启动脚本** — 提供了新的极简一键安装脚本，更快速地帮助你启动 InsightAgent

## 核心特性

### ✨ Agentic 智能数据分析引擎

InsightAgent AI 数据助理现在能够围绕用户的分析目标，自主组织一整套执行流程，告别传统单轮对话的局限，带来全新的自主数据分析体验：

- **多源数据打通**：无缝连接关系型数据库、CSV / Excel 表格、数仓、知识库、文档等。
- **自主推理与探索**：面对复杂问题，AI 数据助理会自动分析数据库 Schema 或数据文件，并规划多步执行策略。
- **执行能力**：自主生成并执行 SQL / Python 代码。
- **开箱即用**：全新设计的 Welcome Page，并提供了丰富的分析示例，新用户学习成本几乎降为零。

#### CSV/Excel 自主数据分析

一键上传本地表格文件，AI 即可自动理解数据结构，自主完成数据清洗、多维计算与图表可视化，让日常报表处理变得前所未有的轻松。

<img src="/img/agentic_data/csv_data_analysis.jpg" width="720px" />

#### 智能数据库洞察与分析报告

基于全新 Agentic 架构，引擎可自主完成数据诊断、特征提取与多维分析，生成包含精美图表与深度洞察的专属分析报告，让数据价值一目了然。

<img src="/img/agentic_data/agentic_db_data_zh.jpg" width="720px" />

#### 深度财务报告智能剖析

专为财务场景量身打造，精准提取营收、利润等核心指标。自动进行同比/环比计算与趋势预测，一键生成专业的财务健康度诊断报告。

<img src="/img/skill/financial_report_analysis_skill.jpg" width="720px" />

#### SQL 自主生成与代码执行能力

底层依托强大的自然语言大模型能力，不仅能精准将对话转化为复杂 SQL，更支持在安全沙箱中自主执行 Python 代码，硬核应对各种高阶计算需求。

<img src="/img/agentic_data/agentic_sql_query.png" width="720px" />

<img src="/img/agentic_data/agentic_gen_code.png" width="720px" />

### 🤖 Agent Skill 生态

大模型决定了智力底线，但生态扩展性决定了业务上限。不同业务场景有着截然不同的分析套路。V0.8.0 正式引入 **Agent Skill** 系统，这是一种将团队专家经验沉淀为"资产"的全新方式：

- 📦 **自定义技能封装**：将你特有的数据清洗逻辑、业务分析模型等封装成独立 Skill，一次编写，全团队复用。
- 🔗 **GitHub 一键导入**：支持直接从社区或企业私有代码仓库导入优质 Skill，彻底打破信息孤岛。
- 📊 **内置 Skill 能力**：开箱即带 CSV/Excel 数据深度分析 Skill、财报分析 Skill、Agent Browser Skill 等，以及通过 Skill Creator 一键创建业务专属 Skill。

<img src="/img/skill/skill_list_zh.png" width="720px" />

### 🛡️ 沙箱安全执行环境（Sandbox）

给予 AI 执行代码的权力，往往伴随系统级的风险。为此，我们引入了隔离**沙箱（Sandbox）**：

- 🛡️ **隔离沙箱运行**：所有由 Agent 生成的未经人工审核的 Shell 代码，均在隔离容器中执行。支持严格的资源阈值限制与执行超时管控，不影响主系统，兼顾了智能体的执行力与企业级的数据安全。
- ⚙️ **资源配置**：会话级的沙箱资源配置限制与执行超时保障，分析产物更可复现、更易审计。

<img src="/img/agentic_data/sanbox_running.png" width="720px" />

### 💬 协作与产品体验升级

好工具需要顺畅地流转，让分析报告和过程从"个人使用"转向"团队复用"：

- 💬 **对话分享与执行回放**：一键生成分享链接。你的团队成员不仅能看到最终精美的 HTML 报告，还能回放查看 Agent 思考和推理的每一步，让复盘和知识分享变得更简单。
- 📝 **对话任务列表**：随时查找历史对话记录，便于复盘与记录。
- 🔗 **原生 APP、Agent 模式**：保留原生应用、Agent、AWEL 等能力，支持多样性产品提升和能力使用。

<img src="/img/agentic_data/agentic_playback.jpg" width="720px" />

### 🚀 新增一键启动脚本

我们提供了多种新的极简一键安装脚本，更快速地帮助你启动 InsightAgent。

**方式一：通过 PyPI 安装**

```bash
# 第一步：安装 dbgpt-app
pip install dbgpt-app

# 第二步：启动 InsightAgent
dbgpt start
```

**方式二：通过 Shell 脚本安装**

```bash
# 以 OpenAI 为例，快速初始化环境
curl -fsSL https://raw.githubusercontent.com/liujincheng-ai/InsightAgent/main/scripts/install/install.sh \
  | OPENAI_API_KEY=sk-xxx bash -s -- --profile openai

# 启动 InsightAgent
cd ~/.dbgpt/InsightAgent && uv run dbgpt start webserver --config ~/.dbgpt/configs/<profile>.toml
```

**方式三：源码安装（与之前版本一致）**

```bash
uv sync --all-packages \
  --extra "base" \
  --extra "proxy_openai" \
  --extra "rag" \
  --extra "storage_chromadb" \
  --extra "dbgpts"

uv run dbgpt start webserver --config configs/dbgpt-proxy-openai.toml
```

🚀 打开浏览器访问 [http://localhost:5670](http://localhost:5670)

详情查看 [安装文档](https://liujincheng-ai.github.io/InsightAgent/docs/next/installation/)。

### 📖 参考文档全面改版并支持多语言

对官方参考文档进行了全面升级，现已正式支持多语言版本！全新的 UI 设计、更清晰的目录结构、一键中英切换，带来更好的阅读与开发体验。

👉 [浏览新版文档](https://liujincheng-ai.github.io/InsightAgent/docs/next/overview/)

## 其他改进

- 新增 MiniMax Provider 支持（[#2989](https://github.com/liujincheng-ai/InsightAgent/pull/2989)）
- 修复 React 解析器对于 vis-thinking 块的处理（[#2996](https://github.com/liujincheng-ai/InsightAgent/pull/2996)）
- README 等文档更新（[#2991](https://github.com/liujincheng-ai/InsightAgent/pull/2991)）

## 升级指南

[升级到 v0.8.0](../upgrade/v0.8.0.md)

## 致谢

### 🎉 新贡献者

V0.8.0 版本新增 **2 位**新的贡献者：

- @octo-patch
- @LXW2019124

🔥🔥 感谢所有贡献者使这次发布成为可能！

@Aries-ckt、@Copilot、@LXW2019124、@chenliang15405、@copilot-swe-agent、@fangyinc 和 @octo-patch

## 参考链接

- [快速开始](https://liujincheng-ai.github.io/InsightAgent/docs/overview/)
- [Docker 快速部署](https://liujincheng-ai.github.io/InsightAgent/docs/next/installation/docker/)

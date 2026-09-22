# Day 3 源码主链路图

```mermaid
flowchart TD
    A[服务启动] --> B[component_configs._initialize_resource_manager]
    B --> C[ResourceManager.register_resource\nsales_diagnosis_tool]
    C --> D[Web 请求 agentic_data_api]
    D --> E{数据库 + 知识库?}
    E -->|是| F[构造综合 workflow prompt]
    F --> G[从 ResourceManager 获取业务 Tool]
    G --> H[显式加入原生 ToolPack]
    H --> I[SalesDiagnosisFirstToolPack 门禁]
    I --> J[ReActAgent / Action Space]
    J --> K{Action}
    K -->|sales_diagnosis_tool| L[固定参数化只读 SQL]
    L --> M[结构化 Observation\n销售/毛利/产品/渠道/全国对比]
    M --> J
    K -->|kb_grep / kb_cat| N[制度库检索]
    N --> O[引用 primarySection 元数据]
    O --> J
    K -->|html_interpreter| P[渲染 HTML 报告]
    P --> Q[报告卡片 / 引用 / 图表]
    Q --> R[terminate]
    K -->|模型提前结束| S[服务端 HTML 兜底]
    S --> P
    J --> T[DeepSeek DSML / ReAct Parser]
    T --> J
```

关键源码入口：

- Tool：`insight_agent/tools/sales_diagnosis.py`
- 门禁：`insight_agent/agent/sales_diagnosis_gate.py`
- 注册：`packages/dbgpt-app/src/dbgpt_app/component_configs.py`
- Web 主流程：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/agentic_data_api.py`
- DSML 解析：`packages/dbgpt-core/src/dbgpt/agent/util/react_parser.py`
- 引用链路：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/tools/knowledge_retrieve.py`

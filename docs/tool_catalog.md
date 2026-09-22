# InsightAgent Tool Catalog

## 目的

本目录定义三个业务 Tool 和通用 SQL 的职责边界。名称保持稳定，description 与参数 Schema 作为可版本化 API 契约维护。

## Tool 决策表

| Tool | 应调用 | 不应调用 | 必填参数 |
|---|---|---|---|
| `sales_diagnosis_tool` | 区域和品类的销售变化归因、环比同比、毛利率、产品或渠道贡献 | 客户流失名单、经销商健康评分、普通销售额查询 | `region`、`category`、`current_quarter` |
| `customer_loss_analysis_tool` | 停止采购、客户大幅下滑、客户下降贡献、A 级客户风险 | 整体销售归因、经销商健康评分、确认客户已经流失 | `region`、`category`、`current_quarter` |
| `dealer_health_analysis_tool` | 经销商健康分、风险排序、扣分原因、干预优先级 | 具体品类销售归因、普通客户流失名单 | `region`、`current_quarter` |
| `sql_query` | 普通销售额、销量、计数、简单排名和无需领域规则的聚合 | 客户流失规则、健康评分或固定业务归因 | `sql` |

## 参数契约

### 公共字段

- `region`：`华东`、`华南`、`华北`。
- `current_quarter`：严格使用 `YYYYQn`，例如 `2026Q2`。
- `top_n`：1 到 20 的整数。

### 销售诊断

- `category`：六个标准汽车配件品类之一。
- 默认 `top_n=5`。

### 客户流失预警

- `category`：六个标准汽车配件品类之一。
- `decline_threshold`：大于 0 且不超过 1 的小数；`0.5` 表示 50%。
- 默认 `decline_threshold=0.5`、`top_n=10`。
- 输出是风险预警，不是已确认流失事实。

### 经销商健康度

- 默认 `top_n=10`。
- 分数由销售变化、采购活跃天数、订单行平均折扣和加权毛利率确定性计算。

## 错误合同

Schema 校验在 Tool 函数和数据库执行之前发生。失败返回：

```json
{
  "status": "error",
  "error": {
    "code": "invalid_arguments",
    "message": "Tool 参数未通过 Schema 校验；请根据 details 修正后重试一次。",
    "retryable": true,
    "details": [
      {
        "field": "current_quarter",
        "type": "string_pattern_mismatch",
        "message": "String should match pattern ...",
        "expected": {"pattern": "^20\\d{2}Q[1-4]$"}
      }
    ]
  },
  "data": null,
  "evidence": []
}
```

可修复格式错误最多反馈一次；权限错误、数据库错误和重复失败不自动重试。

## 组合规则

- 销售变化原因加风险客户名单：销售诊断 + 客户流失。
- 销售归因加经销商评分：销售诊断 + 经销商健康。
- 客户名单加经销商整体评分：客户流失 + 经销商健康。
- 同一 Tool 与相同参数不得重复调用。
- 只调用覆盖用户明确意图所需的最小 Tool 集合。

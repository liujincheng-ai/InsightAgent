# InsightAgent Day 4

Day 4 adds two deterministic domain Tools beside `sales_diagnosis_tool`:

- `customer_loss_analysis_tool` compares a requested quarter with its immediately
  preceding quarter and ranks suspected purchase-stop or significant-decline warnings;
- `dealer_health_analysis_tool` scores a region's dealers using sales change,
  purchasing activity, line-average discount and weighted gross margin.

Both Tools use fixed parameterized SQL through the shared short-lived read-only
PostgreSQL executor. Successful, no-data and error results consistently expose
`status`, `data`, `evidence` and `error`.

## Business boundaries

- Customer warnings are not confirmed churn. They require the manual checks described
  in `重点客户流失预警办法.md`.
- Dealer scoring is an explainable InsightAgent V1 demo rule, not a company policy or
  an industry standard.
- The dataset has no payment, complaint, customer-contact, inventory or approval
  records. The Tools never infer those facts.
- Detailed thresholds and policy mappings are frozen in `DAY4_RULES.md`.

## Tool contracts

```text
customer_loss_analysis_tool(
    region: str,
    category: str,
    current_quarter: str,
    decline_threshold: float = 0.5,
    top_n: int = 10,
)

dealer_health_analysis_tool(
    region: str,
    current_quarter: str,
    top_n: int = 10,
)
```

`top_n` must be an integer from 1 to 20. Quarter values use `YYYYQn`; the customer
threshold must be greater than 0 and no greater than 1. Rates are decimals, money is
CNY, and gross-margin changes are percentage points.

## Native InsightAgent integration

The three domain Tools are registered in the same `ResourceManager`. In combined
database-and-knowledge mode, the request question selects exactly one required first
domain Tool:

```text
sales change / channel contribution -> sales_diagnosis_tool
customer loss / stopped purchasing  -> customer_loss_analysis_tool
dealer health / deduction reasons   -> dealer_health_analysis_tool
```

A focused single-Tool question may terminate after receiving its Observation. A full
report or policy question must continue through the relevant policy evidence and HTML
report stages. Policy documents and sections are chosen from the question intent;
dealer policy section 4.2 is not forced onto unrelated questions.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest tests\insight_agent -q
.\.venv\Scripts\ruff.exe check insight_agent\tools insight_agent\agent tests\insight_agent
```

The frozen database baseline is `data/gold/day4_gold_truth.json`; final evidence is
stored under `evidence/day4/`. No Git commit is part of Day 4 acceptance.

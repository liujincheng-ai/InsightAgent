"""Domain policy and SQL preflight checks for the InsightAgent database.

The evaluation questions intentionally stay unchanged.  This module supplies the
business semantic layer that a production agent would normally obtain from a
metric catalog or dashboard filter context.  It contains scopes and formulas,
never Gold answers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import sqlparse
from sqlparse.tokens import DDL, DML

from insight_agent.semantic import build_semantic_context

INSIGHT_DATABASE_NAMES = {"insight_agent"}

SQL_FINAL_ANSWER_TEMPLATE = """
## 数据范围
- 查询条件：区域/品类/渠道（如适用）
- 当前周期：...
- 对比周期：...

## 关键指标
| 指标 | 当前值 | 对比值 | 变化 |
|---|---:|---:|---:|
| 销售额（CNY） | ... | ... | ... |

## 结论
- 只陈述已由 SQL 返回的事实；比例写明 %，毛利率变化写明百分点。
""".strip()

_SQL_KEYWORDS = {
    "cross",
    "full",
    "group",
    "having",
    "inner",
    "join",
    "left",
    "limit",
    "on",
    "order",
    "outer",
    "right",
    "union",
    "where",
}

_SQL_SOURCE_BOUNDARIES = _SQL_KEYWORDS | {
    "as",
    "by",
    "connect",
    "except",
    "fetch",
    "from",
    "intersect",
    "into",
    "offset",
    "select",
    "using",
    "window",
}


@dataclass(frozen=True)
class SqlValidationResult:
    """Result of one SQL preflight validation."""

    valid: bool
    errors: tuple[str, ...] = ()


def is_insight_database(database_name: str | None) -> bool:
    """Return whether a selected connector targets the InsightAgent database."""

    if not database_name:
        return False
    normalized = database_name.strip().lower()
    return normalized in INSIGHT_DATABASE_NAMES or normalized.endswith("/insight_agent")


def build_database_agent_prompt(
    database_context: str, question: str, semantic_profile: str | None = None
) -> str:
    """Build the focused SQL-agent prompt used for database-only questions."""

    semantic = build_semantic_context(question, semantic_profile)
    clarification_rule = (
        "当前问题存在高风险歧义。不得执行 sql_query；直接 terminate 提出澄清问题。"
        if semantic.requires_clarification
        else "当前问题口径足以查询；按已选择定义生成 SQL。"
    )
    return f"""
你是 InsightAgent 的只读数据分析代理。只解决当前数据库问题，不生成网页、
HTML、图表、任务清单，也不委派子任务。

## 当前数据库
{database_context}

## 业务语义约束
- 数据覆盖 2025-01-01 至 2026-06-30；未写年份的 Q2 默认指最新完整 Q2，
  即 2026 Q2，并与 2026 Q1 比较。
- 环比是相邻周期比较；同比是上年同期比较。
- 销售变化默认使用 SUM(sales_amount)。
- 毛利率使用 SUM(gross_profit)/SUM(sales_amount)。
- 区域名称来自 dim_region，品类和产品名称来自 dim_product，客户属性来自
  dim_customer；使用这些字段时必须连接相应维表。
- 必须在 SQL 中保留问题要求的全部区域、品类、渠道和年份约束。
- 优先用 CASE WHEN 条件聚合在一条 SQL 中完成比较。首次失败后最多修正一次，
  两次失败必须终止，不得继续变换同一查询。

## 按需业务语义层（profile={semantic.profile}）
{semantic.context}

## 歧义决策
{clarification_rule}

## 可用动作
1. sql_query，参数必须是严格 JSON：{{"sql": "单条只读 SELECT 或 WITH...SELECT"}}
2. terminate，参数必须是严格 JSON：{{"result": "最终中文答案"}}

## 执行规则
1. 先检查表关系、范围和计算公式，再生成 SQL。
2. Action Input 必须是完整 JSON 对象，不得使用 Markdown 代码块或省略括号。
3. SQL 校验或执行失败时，根据结构化错误修正，不要重复原 SQL；最多修正一次。
   `PERMISSION_DENIED` 或 `retryable=false` 时不得重试，必须说明失败并终止。
4. 查询结果足以回答时立即 terminate。最终答案必须严格使用以下字段模板，
   不省略查询条件、时间范围、指标单位或比较基准；没有返回的字段写“未查询”，
   不得编造：
{SQL_FINAL_ANSWER_TEMPLATE}
5. 每轮只输出一个动作，格式严格为：
Thought: 简短分析
Action Intention: 简短意图
Action Reason: 简短原因
Action: sql_query 或 terminate
Action Input: 严格 JSON 对象
""".strip()


def build_integrated_business_prompt(question: str) -> str:
    """Return the hard workflow contract for InsightAgent's combined Web mode."""

    from .sales_diagnosis_gate import (
        requires_full_business_report,
        select_domain_tool,
    )

    required_tool = select_domain_tool(question)
    requested_domain_tools = []
    normalized_for_tools = str(question or "").replace(" ", "")
    for tool_name, markers in (
        ("sales_diagnosis_tool", ("销售诊断", "销售归因", "渠道贡献")),
        (
            "customer_loss_analysis_tool",
            ("客户流失", "风险客户", "停止采购", "客户下降贡献"),
        ),
        (
            "dealer_health_analysis_tool",
            ("经销商健康", "经销商风险", "健康度", "扣分"),
        ),
    ):
        if any(marker in normalized_for_tools for marker in markers):
            requested_domain_tools.append(tool_name)
    if required_tool not in requested_domain_tools:
        requested_domain_tools.insert(0, required_tool)
    requested_tool_text = "、".join(f"`{name}`" for name in requested_domain_tools)
    tool_instructions = {
        "sales_diagnosis_tool": "用于区域、品类、销售变化、毛利或渠道贡献问题。",
        "customer_loss_analysis_tool": (
            "用于客户流失风险、停止采购或客户下降贡献问题；"
            "不得把预警表述为已经确认流失。"
        ),
        "dealer_health_analysis_tool": (
            "用于经销商健康度、风险排序或扣分项问题；评分不替代客户核验或等级审批。"
        ),
    }
    tool_call_contracts = {
        "sales_diagnosis_tool": (
            'Action Input: {"region":"<区域>","category":"<品类>",'
            '"current_quarter":"<YYYYQn>","top_n":5}'
        ),
        "customer_loss_analysis_tool": (
            'Action Input: {"region":"<区域>","category":"<品类>",'
            '"current_quarter":"<YYYYQn>","decline_threshold":0.5,"top_n":10}'
        ),
        "dealer_health_analysis_tool": (
            'Action Input: {"region":"<区域>","current_quarter":"<YYYYQn>","top_n":10}'
        ),
    }
    requested_contract_text = "\n".join(
        f"   Action: {name}\n   {tool_call_contracts[name]}"
        for name in requested_domain_tools
    )
    normalized_question = str(question or "").replace(" ", "")
    explicit_document = re.search(r"《([^》]+)》", str(question or ""))
    explicit_section = re.search(r"(?:第\s*)?(\d+(?:\.\d+)+)\s*节", str(question or ""))
    if explicit_document:
        document_name = explicit_document.group(1)
        requested_sections = list(
            dict.fromkeys(re.findall(r"\d+(?:\.\d+)+", str(question or "")))
        )
        section_text = (
            " " + "、".join(requested_sections) + " 节"
            if requested_sections
            else (
                f" {explicit_section.group(1)} 节" if explicit_section else "中相关章节"
            )
        )
        policy_requirement = (
            f"按用户要求检索并引用《{document_name}》{section_text}；"
            "不得用其他制度替换用户指定依据。"
        )
    elif required_tool == "customer_loss_analysis_tool":
        policy_requirement = (
            "客户风险处置引用《重点客户流失预警办法》中与预警条件、风险分级和核验"
            "责任相符的章节。"
        )
    elif required_tool == "dealer_health_analysis_tool":
        policy_requirement = (
            "经销商评分引用《经销商分级与考核管理制度》3.1、3.2；"
            "涉及 A 级经销商下降处置时再引用 4.2。"
        )
    elif "经销商" in normalized_question:
        policy_requirement = (
            "经销商下降整改建议至少引用《经销商分级与考核管理制度》的 4.2 节。"
        )
    else:
        policy_requirement = "按问题主题检索对应制度，不得固定引用无关文件或章节。"
    completion_rule = (
        "调用知识库工具取得制度依据，再调用 html_interpreter 生成带引用的报告；"
        f"{policy_requirement}"
        "完成领域 Tool、制度检索与 HTML 报告渲染前，不得 terminate。"
        if requires_full_business_report(question)
        else (
            "取得领域 Tool Observation 后即可回答并 terminate，"
            "不强制检索制度或生成 HTML。"
        )
    )
    return f"""
## InsightAgent 汽车配件经营分析硬性工作流
你是汽车配件销售公司经营分析师。当前任务同时选择了 InsightAgent 销售数据库与
企业制度库，属于综合经营分析，不得把制度检索当作数据分析的替代。

数据覆盖 2025-01-01 至 2026-06-30。题目未写季度时，`current_quarter` 必须使用
最新完整季度 `2026Q2`，比较基准是上一季度 `2026Q1`，不得自行改成更早周期。

1. 第一项数据动作必须直接调用 `{required_tool}`，不得先调用另外两个领域 Tool，
   不得通过 `execute_tool` 间接调用，也不得使用其他通用工具绕过领域 Tool。
   {tool_instructions[required_tool]}
2. 参数名称必须严格使用以下契约，不得把 `current_quarter` 改成 `period`：
{requested_contract_text}
   本题明确要求的领域 Tool 是：{requested_tool_text}。第一项数据动作完成后，
   必须逐一直接调用其余明确要求的领域 Tool，各调用一次；全部完成前不得检索制度。
3. 领域 Tool 成功后直接使用其结构化 Observation，不再调用 `sql_query` 重复取数；
   只有领域 Tool 明确返回 no_data/error 时才允许补充查询。所有事实只能来自数据库
   Tool 的 Observation，不能从制度文本推断销售数字。
4. {completion_rule} 如果直接回答，必须在 `terminate` 的 `result` 中写出
   Observation 的具体数值、比较基准和结论，不能只说“已获得结果”或“正在整理”。
5. 需要制度或报告时，区分“数据事实”“预警/评分”“管理建议”，标记当前与比较
   时间范围、单位和制度来源；证据不足时必须明确说明。
6. 综合报告优先一次 `semantic_search` 取得目标制度，不要先枚举或全文读取知识库；
   同一 Tool 与相同参数最多调用一次。没有数据时说明无数据，不得编造。
""".strip()


def format_focused_domain_answer(
    tool_name: str, result: Any, question: str = ""
) -> str | None:
    """Build a deterministic user-facing answer from one focused domain result.

    This is the presentation safety net for focused Web questions.  The LLM still
    selects and calls the native domain Tool, while this formatter prevents a
    malformed final ReAct turn from hiding the verified Observation or replacing
    it with invented values.
    """

    if not isinstance(result, dict):
        return None
    status = result.get("status")
    if status == "no_data":
        return "未查询到符合条件的数据，请核对区域、品类和季度。"
    if status != "success" or not isinstance(result.get("data"), dict):
        error = result.get("error")
        if isinstance(error, dict) and error.get("message"):
            return f"领域分析失败：{error['message']}"
        return None

    data = result["data"]
    current_quarter = result.get("current_quarter", "当前季度")
    baseline_quarter = result.get("baseline_quarter", "上一季度")

    if tool_name == "sales_diagnosis_tool":
        sales = data.get("sales", result.get("sales", {}))
        gross_margin = data.get("gross_margin", result.get("gross_margin", {}))
        channels = data.get(
            "channel_contributions", result.get("channel_contributions", [])
        )
        if not isinstance(sales, dict):
            return None
        top_channel = channels[0] if isinstance(channels, list) and channels else {}
        margin_text = ""
        if isinstance(gross_margin, dict):
            margin_text = (
                f"加权毛利率由 {_percent_text(gross_margin.get('previous_quarter'))} "
                f"变为 {_percent_text(gross_margin.get('current'))}，变化 "
                f"{gross_margin.get('change_percentage_points', '未查询')} 个百分点。"
            )
        return (
            f"{result.get('region', '')}{result.get('category', '')} "
            f"{current_quarter}："
            f"销售额 {_money_text(sales.get('current'))} 元，较 {baseline_quarter} "
            f"环比 {_percent_text(sales.get('qoq_change_rate'))}，较上年同期同比 "
            f"{_percent_text(sales.get('yoy_change_rate'))}。主要下降渠道是"
            f"{top_channel.get('name', '未查询')}，环比减少 "
            f"{_money_text(abs(top_channel.get('qoq_change_amount', 0)))} 元，"
            f"占总下降 {_percent_text(top_channel.get('decline_contribution_rate'))}。"
            f"{margin_text}"
        )

    if tool_name == "customer_loss_analysis_tool":
        summary = data.get("summary", {})
        customers = data.get("risk_customers", [])
        if "A级" in str(question or "").replace(" ", ""):
            customers = [
                item
                for item in customers
                if isinstance(item, dict) and item.get("is_core_a_customer")
            ]
        rows = []
        for index, item in enumerate(customers[:3], start=1):
            rows.append(
                f"{index}. {item.get('customer_name', '未知客户')}：下降 "
                f"{_money_text(item.get('decline_amount'))} 元，降幅 "
                f"{_percent_text(item.get('decline_rate'))}，下降贡献 "
                f"{_percent_text(item.get('decline_contribution_rate'))}。"
            )
        return (
            f"{current_quarter} 相比 {baseline_quarter}，"
            f"{result.get('region', '')}{result.get('category', '')}销售净下降 "
            f"{_money_text(summary.get('net_decline_amount'))} 元；识别到 "
            f"{summary.get('risk_customer_count', 0)} 个风险客户。\n"
            + "\n".join(rows)
            + "\n注意：这是停止采购或大幅下滑预警，不代表客户已确认流失，"
            "仍需核对沟通、库存、价格和售后事实。"
        )

    if tool_name == "dealer_health_analysis_tool":
        dealers = data.get("dealers", [])
        if not isinstance(dealers, list) or not dealers:
            return "未查询到可评分的经销商数据。"
        dealer = dealers[0]
        scores = dealer.get("component_scores", {})
        deductions = dealer.get("deductions", [])
        deduction_text = "；".join(
            f"{item.get('component')} 扣 {item.get('deducted_points')} 分"
            for item in deductions
            if isinstance(item, dict)
        )
        return (
            f"{result.get('region', '')} {current_quarter} 风险最高的是"
            f"{dealer.get('dealer_name', '未知经销商')}，健康度 "
            f"{dealer.get('health_score', '未查询')}/100，风险等级 "
            f"{dealer.get('risk_level', '未查询')}。四项得分：销售变化 "
            f"{scores.get('sales_change', '未查询')}/40、采购活跃度 "
            f"{scores.get('purchase_activity', '未查询')}/20、折扣 "
            f"{scores.get('discount', '未查询')}/20、毛利 "
            f"{scores.get('gross_margin', '未查询')}/20。扣分项："
            f"{deduction_text or '无'}。该评分是 InsightAgent V1 演示规则，"
            "用于调查优先级，不替代客户核验或等级调整审批。"
        )
    return None


def format_integrated_business_answer(
    tool_name: str,
    result: Any,
    knowledge_result: Any,
    question: str = "",
    domain_results: dict[str, Any] | None = None,
) -> str | None:
    """Build an evidence-bound summary for a completed integrated report."""

    all_domain_results = dict(domain_results or {})
    all_domain_results.setdefault(tool_name, result)
    summaries = [
        summary
        for name, tool_result in all_domain_results.items()
        if (summary := format_focused_domain_answer(name, tool_result, str(question)))
    ]
    domain_summary = "\n".join(summaries)
    if not domain_summary or not isinstance(result, dict):
        return None
    knowledge_text = str(knowledge_result or "")
    current = str(result.get("current_quarter") or "2026Q2")
    baseline = str(result.get("baseline_quarter") or "2026Q1")
    match = re.fullmatch(r"(\d{4})Q([1-4])", current)
    prior = f"{int(match.group(1)) - 1}Q{match.group(2)}" if match else "上年同期"
    requested_document = re.search(r"《([^》]+)》", str(question or ""))
    requested_sections = list(
        dict.fromkeys(re.findall(r"\d+(?:\.\d+)+", str(question or "")))
    )
    if requested_document and requested_document.group(1) in knowledge_text:
        policy = f"《{requested_document.group(1)}》"
    elif "经销商分级与考核管理制度" in knowledge_text:
        policy = "《经销商分级与考核管理制度》"
    else:
        policy = "已检索制度证据"
    section_candidates = requested_sections or ["3.2", "4.2"]
    sections = "、".join(
        section for section in section_candidates if section in knowledge_text
    )
    section_text = f"第 {sections} 节" if sections else "对应章节"
    return (
        "## 数据事实\n"
        f"时间范围：{current} 对比 {baseline}；同比基准：{prior}；单位：元。\n"
        f"{domain_summary}\n\n"
        "## 风险判断\n"
        "领域 Tool 已识别主要下降渠道。经销商及其客户应进入风险核验，"
        "但销售下降只是预警信号，不等同于已确认客户流失。\n\n"
        "## 制度依据\n"
        f"知识库已实际检索到 {policy}{section_text}；制度内容与数据库数值"
        "分别取证，不用制度文本推断销售事实。\n\n"
        "## 管理建议\n"
        "按检索到的制度时限核对订单、库存、价格、竞品与客户反馈，形成整改"
        "计划并持续复核；涉及经销商等级或资源调整时，保留沟通与审批证据。"
    )


def format_verified_sql_answer(question: str, result: Any) -> str | None:
    """Present the last successful SQL result without LLM numeric transcription.

    The SQL itself remains model-generated and passes the existing semantic
    preflight.  Only the final rendering is deterministic so a verified value
    cannot be changed between the Observation and the user-facing answer.
    """

    if not isinstance(result, dict):
        return None
    columns = result.get("columns")
    rows = result.get("rows")
    if not isinstance(columns, list) or not isinstance(rows, list) or not rows:
        return None
    normalized_rows = [row for row in rows if isinstance(row, list)]
    if not normalized_rows:
        return None

    def _display(value: Any) -> str:
        if isinstance(value, float):
            return f"{value:,.4f}".rstrip("0").rstrip(".")
        return str(value)

    header = "| " + " | ".join(str(item) for item in columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    table_rows = [
        "| " + " | ".join(_display(value) for value in row) + " |"
        for row in normalized_rows
    ]
    parts = [
        "## 数据库已验证结果",
        "以下数值直接来自成功的 `sql_query` Observation，未由模型重新抄写：",
        "\n".join([header, separator, *table_rows]),
    ]
    lowered_columns = [str(item).lower() for item in columns]
    row_maps = [dict(zip(lowered_columns, row)) for row in normalized_rows]

    discount_column = next(
        (
            name
            for name in ("avg_discount_rate", "avg_line_discount_rate")
            if name in lowered_columns
        ),
        None,
    )
    if (
        "period" in lowered_columns
        and discount_column
        and "weighted_gross_margin" in lowered_columns
    ):
        period_rows = {
            re.sub(r"[^0-9q]", "", str(row["period"]).lower()): row for row in row_maps
        }
        current_row = period_rows.get("2026q2") or period_rows.get("q22026")
        previous_row = period_rows.get("2026q1") or period_rows.get("q12026")
        if current_row and previous_row:
            discount_change = (
                current_row[discount_column] - previous_row[discount_column]
            ) * 100
            margin_change = (
                current_row["weighted_gross_margin"]
                - previous_row["weighted_gross_margin"]
            ) * 100
            parts.extend(
                [
                    "## 指标变化与聚合口径",
                    f"- 订单行平均折扣率变化：{discount_change:+.4f} 个百分点；"
                    "口径为订单行 discount_rate 的算术平均。",
                    f"- 加权毛利率变化：{margin_change:+.4f} 个百分点；"
                    "口径为总毛利除以总销售额。",
                ]
            )
    count_column = next(
        (
            name
            for name in ("row_count", "record_count", "cnt", "count")
            if name in lowered_columns
        ),
        None,
    )
    if count_column and all(
        isinstance(item.get(count_column), (int, float, Decimal))
        and item[count_column] == 0
        for item in row_maps
    ):
        parts.extend(
            [
                "## 无数据说明",
                "- 查询范围内记录数为 0，明确判定为无数据；数值 0 不代表存在交易。",
            ]
        )
    max_date_column = next(
        (
            name
            for name in ("max_sale_date", "data_max_date")
            if name in lowered_columns
        ),
        None,
    )
    amount_columns = [
        name
        for name in lowered_columns
        if "sales" in name and ("amount" in name or name.endswith("sales"))
    ]
    if (
        max_date_column
        and amount_columns
        and all(row_maps[0].get(name) == 0 for name in amount_columns)
    ):
        parts.extend(
            [
                "## 无数据说明",
                f"- 查询周期超出当前数据截止日 {row_maps[0][max_date_column]}，"
                "明确判定为无数据。",
            ]
        )
    current_sales_column = next(
        (name for name in ("q2_2026_sales", "q2_2026") if name in lowered_columns),
        None,
    )
    previous_sales_column = next(
        (name for name in ("q1_2026_sales", "q1_2026") if name in lowered_columns),
        None,
    )
    prior_year_sales_column = next(
        (name for name in ("q2_2025_sales", "q2_2025") if name in lowered_columns),
        None,
    )
    if (
        current_sales_column
        and previous_sales_column
        and prior_year_sales_column
        and len(normalized_rows) == 1
    ):
        row_map = row_maps[0]
        current = row_map[current_sales_column]
        previous = row_map[previous_sales_column]
        last_year = row_map[prior_year_sales_column]
        if all(
            isinstance(value, (int, float, Decimal))
            for value in (current, previous, last_year)
        ):
            qoq = (current - previous) / previous if previous else None
            yoy = (current - last_year) / last_year if last_year else None
            parts.extend(
                [
                    "## 计算结论",
                    f"- 2026 Q2 销售额：{current:,.2f} 元。",
                    f"- 相比 2026 Q1：{qoq:.2%}。"
                    if qoq is not None
                    else "- 环比：基准为 0，无法计算。",
                    f"- 相比 2025 Q2：{yoy:.2%}。"
                    if yoy is not None
                    else "- 同比：基准为 0，无法计算。",
                ]
            )

    numeric_types = (int, float, Decimal)
    if {"region_name", "q2_sales", "q1_sales"}.issubset(lowered_columns):
        comparisons = []
        for row_map in row_maps:
            current = row_map["q2_sales"]
            previous = row_map["q1_sales"]
            if isinstance(current, numeric_types) and isinstance(
                previous, numeric_types
            ):
                rate = (current - previous) / previous if previous else None
                rate_text = f"{rate:.2%}" if rate is not None else "无法计算"
                comparisons.append(f"- {row_map['region_name']}：环比 {rate_text}。")
        if comparisons:
            parts.extend(["## 区域环比", *comparisons])

    if {"category", "q2_sales", "q1_sales"}.issubset(lowered_columns):
        row_map = row_maps[0]
        current = row_map["q2_sales"]
        previous = row_map["q1_sales"]
        if isinstance(current, numeric_types) and isinstance(previous, numeric_types):
            rate = (current - previous) / previous if previous else None
            parts.extend(
                [
                    "## 品类下降结论",
                    f"- 环比下降最多的品类：{row_map['category']}。",
                    f"- 环比变化率：{rate:.2%}；降幅：{abs(rate):.2%}。"
                    if rate is not None
                    else "- 环比变化率：基准为 0，无法计算。",
                ]
            )

    q1_margin_column = next(
        (
            name
            for name in lowered_columns
            if name.startswith("q1") and "margin" in name
        ),
        None,
    )
    q2_margin_column = next(
        (
            name
            for name in lowered_columns
            if name.startswith("q2") and "margin" in name
        ),
        None,
    )
    if q1_margin_column and q2_margin_column:
        row_map = row_maps[0]
        q1_margin = row_map[q1_margin_column]
        q2_margin = row_map[q2_margin_column]
        if isinstance(q1_margin, numeric_types) and isinstance(
            q2_margin, numeric_types
        ):
            q1_margin = q1_margin * 100 if abs(q1_margin) <= 1 else q1_margin
            q2_margin = q2_margin * 100 if abs(q2_margin) <= 1 else q2_margin
            parts.extend(
                [
                    "## 毛利率变化",
                    f"- 2026 Q1 加权毛利率：{q1_margin:.2f}%。",
                    f"- 2026 Q2 加权毛利率：{q2_margin:.2f}%。",
                    f"- 变化：{q2_margin - q1_margin:.2f} 个百分点。",
                ]
            )

    q1_profit_column = next(
        (
            name
            for name in lowered_columns
            if name.startswith("q1") and ("profit" in name or name.endswith("gp"))
        ),
        None,
    )
    q2_profit_column = next(
        (
            name
            for name in lowered_columns
            if name.startswith("q2") and ("profit" in name or name.endswith("gp"))
        ),
        None,
    )
    if (
        q1_profit_column
        and q2_profit_column
        and {
            "q1_sales",
            "q2_sales",
        }.issubset(lowered_columns)
    ):
        row_map = row_maps[0]
        values = [
            row_map[q1_profit_column],
            row_map["q1_sales"],
            row_map[q2_profit_column],
            row_map["q2_sales"],
        ]
        if all(isinstance(value, numeric_types) for value in values):
            q1_margin = (
                row_map[q1_profit_column] / row_map["q1_sales"] * 100
                if row_map["q1_sales"]
                else None
            )
            q2_margin = (
                row_map[q2_profit_column] / row_map["q2_sales"] * 100
                if row_map["q2_sales"]
                else None
            )
            if q1_margin is not None and q2_margin is not None:
                parts.extend(
                    [
                        "## 毛利率变化",
                        f"- 2026 Q1 加权毛利率：{q1_margin:.2f}%。",
                        f"- 2026 Q2 加权毛利率：{q2_margin:.2f}%。",
                        f"- 变化：{q2_margin - q1_margin:.2f} 个百分点。",
                    ]
                )

    if {"period", "gross_margin"}.issubset(lowered_columns):
        margins = {
            str(item["period"]).replace(" ", "").upper(): item["gross_margin"]
            for item in row_maps
            if isinstance(item.get("gross_margin"), numeric_types)
        }
        if "2026Q1" in margins and "2026Q2" in margins:
            q1_margin = margins["2026Q1"] * 100
            q2_margin = margins["2026Q2"] * 100
            parts.extend(
                [
                    "## 毛利率变化",
                    f"- 2026 Q1 加权毛利率：{q1_margin:.2f}%。",
                    f"- 2026 Q2 加权毛利率：{q2_margin:.2f}%。",
                    f"- 变化：{q2_margin - q1_margin:.2f} 个百分点。",
                ]
            )

    if {"qtr", "gross_margin"}.issubset(lowered_columns):
        margins = {
            int(item["qtr"]): item["gross_margin"]
            for item in row_maps
            if isinstance(item.get("qtr"), numeric_types)
            and isinstance(item.get("gross_margin"), numeric_types)
        }
        if 1 in margins and 2 in margins:
            q1_margin = margins[1] * 100 if abs(margins[1]) <= 1 else margins[1]
            q2_margin = margins[2] * 100 if abs(margins[2]) <= 1 else margins[2]
            parts.extend(
                [
                    "## 毛利率变化",
                    f"- 2026 Q1 加权毛利率：{q1_margin:.2f}%。",
                    f"- 2026 Q2 加权毛利率：{q2_margin:.2f}%。",
                    f"- 变化：{q2_margin - q1_margin:.2f} 个百分点。",
                ]
            )

    change_column = next(
        (
            name
            for name in ("diff", "change_amt", "change_amount", "qoq_change_amount")
            if name in lowered_columns
        ),
        None,
    )
    if "channel" in lowered_columns and (
        change_column or {"q2_sales", "q1_sales"}.issubset(lowered_columns)
    ):
        channel_changes = []
        for row_map in row_maps:
            if change_column and isinstance(row_map.get(change_column), numeric_types):
                channel_changes.append((row_map, row_map[change_column]))
            elif isinstance(row_map.get("q2_sales"), numeric_types) and isinstance(
                row_map.get("q1_sales"), numeric_types
            ):
                channel_changes.append(
                    (row_map, row_map["q2_sales"] - row_map["q1_sales"])
                )
        declining = [item for item in channel_changes if item[1] < 0]
        if declining:
            leading, leading_change = min(declining, key=lambda item: item[1])
            net_change = sum(item[1] for item in channel_changes)
            contribution_column = next(
                (
                    name
                    for name in lowered_columns
                    if "contribution" in name
                    or ("贡献" in name and ("rate" in name or "pct" in name))
                ),
                None,
            )
            contribution = None
            if len(channel_changes) > 1 and net_change:
                contribution = abs(leading_change) / abs(net_change)
            elif contribution_column and isinstance(
                leading.get(contribution_column), numeric_types
            ):
                contribution = leading[contribution_column]
                if abs(contribution) > 1:
                    contribution /= 100
            parts.extend(
                [
                    "## 渠道下降贡献",
                    (
                        f"- 主要下降渠道：{leading['channel']}；下降金额 "
                        f"{abs(leading_change):,.2f} 元；"
                        "对净下降的贡献率 "
                        + (
                            f"{contribution:.2%}。"
                            if contribution is not None
                            else "无法计算。"
                        )
                    ),
                ]
            )

    customer_change_column = next(
        (
            name
            for name in ("decline_amount", "change_amount", "change_amt", "diff")
            if name in lowered_columns
        ),
        None,
    )
    if (
        "下降" in question
        and "customer_name" in lowered_columns
        and customer_change_column
    ):
        row_map = row_maps[0]
        decline = row_map[customer_change_column]
        if isinstance(decline, numeric_types):
            parts.extend(
                [
                    "## 客户下降结论",
                    f"- {row_map['customer_name']}下降 {abs(decline):,.2f} 元。",
                ]
            )

    parts.append(f"查询问题：{question.strip()}")
    return "\n\n".join(parts)


def _money_text(value: Any) -> str:
    return f"{value:,.2f}" if isinstance(value, (int, float)) else "未查询"


def _percent_text(value: Any) -> str:
    return f"{value:.2%}" if isinstance(value, (int, float)) else "未查询"


def _validate_single_read_only_statement(sql: str) -> list[str]:
    errors: list[str] = []
    statements = [
        statement for statement in sqlparse.parse(sql) if str(statement).strip()
    ]
    if len(statements) != 1:
        return ["只允许一条 SQL 语句"]

    statement = statements[0]
    if statement.get_type().upper() != "SELECT":
        errors.append("只允许 SELECT 或以 SELECT 结束的 WITH 查询")

    for token in statement.flatten():
        if token.ttype in DDL:
            errors.append(f"检测到禁止的 DDL 关键字 {token.value.upper()}")
        elif token.ttype in DML and token.value.upper() != "SELECT":
            errors.append(f"检测到禁止的 DML 关键字 {token.value.upper()}")
    return errors


def validate_read_only_sql(sql: str) -> SqlValidationResult:
    """Validate that input is one read-only SELECT statement."""

    if not isinstance(sql, str) or not sql.strip():
        return SqlValidationResult(False, ("sql 必须是非空字符串",))
    errors = _validate_single_read_only_statement(sql)
    return SqlValidationResult(not errors, tuple(dict.fromkeys(errors)))


def _undefined_aliases(sql: str) -> set[str]:
    defined = {"public"}
    boundary_words = "|".join(sorted(_SQL_SOURCE_BOUNDARIES))
    source_pattern = re.compile(
        r"\b(?:FROM|JOIN)\s+([A-Za-z_][\w.]*)"
        rf"(?:\s+(?:AS\s+)?(?!(?:{boundary_words})\b)([A-Za-z_]\w*))?",
        flags=re.IGNORECASE,
    )
    for match in source_pattern.finditer(sql):
        table_name = match.group(1).split(".")[-1].lower()
        defined.add(table_name)
        alias = (match.group(2) or "").lower()
        if alias and alias not in _SQL_SOURCE_BOUNDARIES:
            defined.add(alias)

    # A derived table is introduced after a closing parenthesis rather than
    # directly after FROM/JOIN, so record its alias separately.
    for match in re.finditer(
        rf"\)\s+(?:AS\s+)?(?!(?:{boundary_words})\b)([A-Za-z_]\w*)",
        sql,
        flags=re.IGNORECASE,
    ):
        defined.add(match.group(1).lower())

    for match in re.finditer(
        r"\bWITH\s+([A-Za-z_]\w*)\s+AS\s*\(", sql, flags=re.IGNORECASE
    ):
        defined.add(match.group(1).lower())

    referenced = {
        match.group(1).lower() for match in re.finditer(r"\b([A-Za-z_]\w*)\s*\.", sql)
    }
    return referenced - defined


def validate_insight_sql(sql: str, question: str) -> SqlValidationResult:
    """Validate read-only safety and InsightAgent question constraints."""

    if not isinstance(sql, str) or not sql.strip():
        return SqlValidationResult(False, ("sql 必须是非空字符串",))

    errors = list(validate_read_only_sql(sql).errors)
    undefined = sorted(_undefined_aliases(sql))
    if undefined:
        errors.append("引用了未在 FROM/JOIN 中定义的别名: " + ", ".join(undefined))

    sql_lower = sql.lower()
    normalized_question = re.sub(r"\s+", "", question or "")
    required_literals = [
        literal
        for literal in (
            "华东",
            "华南",
            "华北",
            "华中",
            "西南",
            "刹车系统",
            "经销商",
            "不存在品类",
        )
        if literal in normalized_question
    ]
    for literal in dict.fromkeys(required_literals):
        if literal not in sql:
            errors.append(f"缺少业务范围约束: {literal}")

    needs_region = any(
        name in normalized_question
        for name in ("华东", "华南", "华北", "华中", "西南", "区域")
    )
    if needs_region and "dim_region" not in sql_lower:
        errors.append("区域分析必须连接 dim_region")

    needs_product = any(
        name in normalized_question for name in ("品类", "产品", "刹车系统")
    )
    if needs_product and "dim_product" not in sql_lower:
        errors.append("产品或品类分析必须连接 dim_product")

    if "Q2" in (question or "").upper() and "2026" not in sql:
        errors.append("当前 Q2 口径为 2026 Q2，SQL 必须显式限定 2026")
    requires_full_trace = (
        "完整查询结果必须可追溯" in normalized_question
        or "完整结果需要可追溯" in normalized_question
    )
    topn_filter = re.search(
        r"\b(?:limit\s+\d+|(?:rn|rank|row_num|row_number)\s*<=?\s*\d+)",
        sql_lower,
    )
    if requires_full_trace and topn_filter:
        errors.append(
            "用户要求完整结果可追溯，SQL 不得 LIMIT 或过滤 Top-N；"
            "展示 Top-N 应在结果落盘后完成"
        )
    if "同比" in normalized_question and not all(
        year in sql for year in ("2025", "2026")
    ):
        errors.append("同比/环比查询必须同时覆盖 2025 和 2026 的比较周期")
    if "贡献" in normalized_question and not re.search(
        r"(?:contribution|rate|pct)", sql_lower
    ):
        errors.append("贡献率必须在 SQL 中显式计算并返回，不能只查询下降金额")
    if "销量" in normalized_question and "quantity" not in sql_lower:
        errors.append("销量必须使用 SUM(quantity)，不能用销售额或明细行数代替")
    if "毛利率" in normalized_question:
        has_weighted_margin = bool(
            re.search(r"sum\s*\([^)]*gross_profit", sql_lower)
            and re.search(r"sum\s*\([^)]*sales_amount", sql_lower)
            and "/" in sql_lower
        )
        if not has_weighted_margin or re.search(
            r"avg\s*\([^)]*(?:gross_profit|margin)", sql_lower
        ):
            errors.append(
                "毛利率必须使用 SUM(gross_profit)/SUM(sales_amount)，不能平均行毛利率"
            )
    if "加权平均折扣率" in normalized_question and not re.search(
        r"sales_amount\s*\*\s*\w*\.?discount_rate", sql_lower
    ):
        errors.append(
            "销售额加权折扣率必须使用 SUM(sales_amount*discount_rate)/SUM(sales_amount)"
        )
    if any(term in normalized_question for term in ("不同客户数", "活跃经销商")):
        if not re.search(r"count\s*\(\s*distinct\s+", sql_lower):
            errors.append("不同客户数或活跃经销商必须使用 COUNT(DISTINCT customer_id)")
    if "交易发生区域" in normalized_question and re.search(
        r"dim_region\s+\w+\s+on\s+\w+\.region_id\s*=\s*\w+\.region_id",
        sql_lower,
    ):
        customer_region_join = bool(
            re.search(
                r"dim_region\s+(\w+)\s+on\s+(?:c|\w*customer\w*)\.region_id",
                sql_lower,
            )
        )
        if customer_region_join:
            errors.append("交易发生区域必须用 fact_sales.region_id 连接 dim_region")

    return SqlValidationResult(not errors, tuple(dict.fromkeys(errors)))

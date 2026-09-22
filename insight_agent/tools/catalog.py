"""Versioned Tool descriptions used by the Week 2 ablation."""

from __future__ import annotations

from typing import Callable

from dbgpt.agent.resource.tool.base import BaseTool, FunctionTool

from .customer_loss_analysis import customer_loss_analysis_tool
from .dealer_health_analysis import dealer_health_analysis_tool
from .sales_diagnosis import sales_diagnosis_tool

TOOL_CALLING_PROFILES = ("baseline", "positive", "boundary")

_BASELINE_DESCRIPTIONS = {
    "sales_diagnosis_tool": (
        "确定性诊断指定区域、汽车配件品类在某季度的销售下滑；返回环比、同比、"
        "加权毛利率变化、产品和渠道下降贡献及全国趋势。仅用于有明确区域、品类和"
        "季度的销售变化归因。"
    ),
    "customer_loss_analysis_tool": (
        "比较指定区域和汽车配件品类的当前季度与上一季度客户采购，识别疑似停止"
        "采购和大幅下滑客户，计算下降贡献并标记 A 级核心客户。用于客户流失风险"
        "或客户下降影响问题；结果是预警而非已确认流失事实。"
    ),
    "dealer_health_analysis_tool": (
        "按销售变化、采购活跃天数、订单行平均折扣和加权毛利率四项规则，确定性"
        "计算指定区域经销商在某季度的 0 到 100 健康度、风险等级和扣分原因。用于"
        "经销商健康、风险排序或优先干预问题，不用于具体品类的销售归因。"
    ),
}

_POSITIVE_DESCRIPTIONS = {
    "sales_diagnosis_tool": (
        "分析明确区域、汽车配件品类和季度的销售变化原因，返回环比、同比、加权"
        "毛利率、产品下降贡献、渠道贡献和全国趋势。用于销售下滑或增长归因。"
    ),
    "customer_loss_analysis_tool": (
        "比较明确区域和品类的季度客户采购，列出停止采购或超过阈值下滑的客户，"
        "计算客户下降贡献并标记 A 级客户。用于客户流失风险和客户下降影响。"
    ),
    "dealer_health_analysis_tool": (
        "按照销售变化、活跃天数、折扣和毛利率计算区域经销商季度健康分、风险等级"
        "和扣分原因。用于经销商健康度、风险排序和干预优先级。"
    ),
}


def build_business_tools(profile: str) -> list[BaseTool]:
    """Build one immutable Tool surface for a controlled ablation profile."""

    normalized = str(profile or "").strip().lower()
    if normalized not in TOOL_CALLING_PROFILES:
        raise ValueError(
            f"tool_calling_profile 必须是 {', '.join(TOOL_CALLING_PROFILES)}"
        )
    decorated_tools = (
        sales_diagnosis_tool,
        customer_loss_analysis_tool,
        dealer_health_analysis_tool,
    )
    if normalized == "boundary":
        return [tool._tool for tool in decorated_tools]
    descriptions = (
        _BASELINE_DESCRIPTIONS if normalized == "baseline" else _POSITIVE_DESCRIPTIONS
    )
    return [
        _legacy_function_tool(tool, descriptions[tool._tool.name])
        for tool in decorated_tools
    ]


def _legacy_function_tool(tool: Callable, description: str) -> FunctionTool:
    """Clone a tool with signature-only arguments and no Schema validation."""

    implementation = getattr(tool, "__wrapped__", tool)
    return FunctionTool(
        name=tool._tool.name,
        func=implementation,
        description=description,
    )

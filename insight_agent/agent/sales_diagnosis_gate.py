"""Native ToolPack guard for the InsightAgent integrated Web workflow."""

from __future__ import annotations

import re
from typing import Any, Optional

from insight_agent.reliability.tool_pack import InsightReliabilityToolPack


class SalesDiagnosisFirstToolPack(InsightReliabilityToolPack):
    """Keep InsightAgent workflows evidence-led and route one domain tool first.

    This is deliberately a ``ToolPack`` subclass rather than a separate agent or
    a proxy HTTP service.  The registered ``sales_diagnosis_tool`` remains the
    exact native InsightAgent tool the ReAct agent discovers and executes.
    """

    _PLANNING_TOOLS = {"todowrite"}
    _KNOWLEDGE_TOOLS = {"semantic_search", "kb_grep", "kb_cat", "kb_ls", "kb_glob"}
    _REPORT_BYPASS_TOOLS = {
        "code_interpreter",
        "shell_interpreter",
        "execute_tool",
        "execute_skill_script",
        "execute_skill_script_file",
    }

    def __init__(
        self,
        resources: Any,
        required_domain_tool: str = "sales_diagnosis_tool",
        required_domain_tools: Optional[list[str]] = None,
        require_knowledge_and_report: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(resources, **kwargs)
        self.required_domain_tool = required_domain_tool
        ordered_tools = required_domain_tools or [required_domain_tool]
        self.required_domain_tools = tuple(
            dict.fromkeys([required_domain_tool, *ordered_tools])
        )
        self.require_knowledge_and_report = require_knowledge_and_report
        self._domain_tool_completed = False
        self._completed_domain_tools: set[str] = set()
        self._knowledge_evidence_completed = False
        self._html_report_completed = False
        self.last_domain_result: Any = None
        self.last_sales_result: Any = None
        self.domain_results: dict[str, Any] = {}
        self.last_knowledge_result: Any = None

    def _missing_steps(self) -> list[str]:
        missing: list[str] = []
        missing_domain_tools = [
            name
            for name in self.required_domain_tools
            if name not in self._completed_domain_tools
        ]
        if missing_domain_tools:
            missing.append("调用 " + "、".join(missing_domain_tools) + " 完成领域分析")
        if self.require_knowledge_and_report and not self._knowledge_evidence_completed:
            missing.append("再调用知识库工具取得制度依据")
        if self.require_knowledge_and_report and not self._html_report_completed:
            missing.append("最后调用 html_interpreter 渲染报告")
        return missing

    def _blocked_result(self, resource_name: Optional[str]) -> dict[str, Any]:
        missing = self._missing_steps()
        return {
            "status": "blocked",
            "error_code": "INSIGHT_WORKFLOW_EVIDENCE_REQUIRED",
            "attempted_tool": resource_name,
            "message": "；".join(missing) + "。不得用制度检索替代数据库事实。",
        }

    def _should_block(self, resource_name: Optional[str]) -> bool:
        if not self._domain_tool_completed:
            return resource_name not in self._PLANNING_TOOLS | {
                self.required_domain_tool
            }
        if len(self._completed_domain_tools) < len(self.required_domain_tools):
            return resource_name not in self._PLANNING_TOOLS | set(
                self.required_domain_tools
            )
        if not self.require_knowledge_and_report:
            return False
        if not self._knowledge_evidence_completed:
            allowed = self._PLANNING_TOOLS | self._KNOWLEDGE_TOOLS
            return resource_name not in allowed
        if not self._html_report_completed:
            allowed = (
                self._PLANNING_TOOLS | self._KNOWLEDGE_TOOLS | {"html_interpreter"}
            )
            return resource_name not in allowed
        return False

    def _record_completion(self, resource_name: Optional[str]) -> None:
        if self.policy_enabled and not self.last_observation.succeeded:
            return
        if resource_name in self.required_domain_tools:
            self._completed_domain_tools.add(resource_name)
            self._domain_tool_completed = (
                self.required_domain_tool in self._completed_domain_tools
            )
        elif resource_name in self._KNOWLEDGE_TOOLS:
            self._knowledge_evidence_completed = True
        elif resource_name == "html_interpreter":
            self._html_report_completed = True

    def execute(
        self, *args: Any, resource_name: Optional[str] = None, **kwargs: Any
    ) -> Any:
        if self._should_block(resource_name):
            result = self._blocked_result(resource_name)
            if not self.policy_enabled:
                return result
            return self._process_result(resource_name, kwargs, result)
        result = super().execute(*args, resource_name=resource_name, **kwargs)
        if resource_name in self.required_domain_tools:
            self.domain_results[resource_name] = result
        if resource_name == self.required_domain_tool:
            self.last_domain_result = result
        if resource_name == "sales_diagnosis_tool":
            self.last_sales_result = result
        elif resource_name in self._KNOWLEDGE_TOOLS:
            self.last_knowledge_result = result
        self._record_completion(resource_name)
        return result

    async def async_execute(
        self, *args: Any, resource_name: Optional[str] = None, **kwargs: Any
    ) -> Any:
        if self._should_block(resource_name):
            result = self._blocked_result(resource_name)
            if not self.policy_enabled:
                return result
            return self._process_result(resource_name, kwargs, result)
        result = await super().async_execute(
            *args, resource_name=resource_name, **kwargs
        )
        if resource_name in self.required_domain_tools:
            self.domain_results[resource_name] = result
        if resource_name == self.required_domain_tool:
            self.last_domain_result = result
        if resource_name == "sales_diagnosis_tool":
            self.last_sales_result = result
        elif resource_name in self._KNOWLEDGE_TOOLS:
            self.last_knowledge_result = result
        self._record_completion(resource_name)
        return result

    def is_terminal(self, resource_name: Optional[str] = None) -> bool:
        if self.policy_enabled and self.force_terminal:
            return True
        if resource_name == "terminate" and self._missing_steps():
            return False
        return super().is_terminal(resource_name)


def select_domain_tool(question: str) -> str:
    """Choose the narrowest Day 4 domain tool from explicit business intent."""

    normalized = _business_question_text(question).replace(" ", "")
    dealer_health_terms = ("经销商健康", "健康度", "风险最高", "扣分项")
    customer_loss_terms = ("客户流失", "流失风险", "停止采购", "哪些A级客户")
    if any(term in normalized for term in dealer_health_terms):
        return "dealer_health_analysis_tool"
    if any(term in normalized for term in customer_loss_terms):
        return "customer_loss_analysis_tool"
    return "sales_diagnosis_tool"


def requires_full_business_report(question: str) -> bool:
    """Return whether policy retrieval and HTML presentation are required."""

    normalized = _business_question_text(question).replace(" ", "")
    return any(
        term in normalized
        for term in (
            "制度",
            "建议",
            "改进",
            "整改",
            "报告",
            "图表",
            "引用",
        )
    )


def focused_domain_tool_args(question: str, tool_name: str) -> dict[str, Any] | None:
    """Extract deterministic arguments for a focused Day 4 domain Tool.

    Return ``None`` instead of guessing when a required region or category is
    absent.  The latest complete quarter is the documented project default.
    """

    normalized = _business_question_text(question).replace(" ", "")
    region = next(
        (name for name in ("华东", "华南", "华北") if name in normalized),
        None,
    )
    quarter_match = re.search(r"20\d{2}Q[1-4]", normalized, flags=re.IGNORECASE)
    quarter = quarter_match.group(0).upper() if quarter_match else "2026Q2"
    if not region:
        return None
    if tool_name == "dealer_health_analysis_tool":
        return {"region": region, "current_quarter": quarter, "top_n": 10}

    categories = (
        "刹车系统",
        "滤清系统",
        "点火系统",
        "悬挂系统",
        "照明系统",
        "雨刮及易损件",
    )
    category = next((name for name in categories if name in normalized), None)
    if not category:
        return None
    common = {
        "region": region,
        "category": category,
        "current_quarter": quarter,
    }
    if tool_name == "sales_diagnosis_tool":
        return {**common, "top_n": 5}
    if tool_name == "customer_loss_analysis_tool":
        return {**common, "decline_threshold": 0.5, "top_n": 10}
    return None


def _business_question_text(question: str) -> str:
    """Remove UI resource labels before classifying the user's actual request."""

    return re.sub(
        r"^(?:\[(?:Database|Knowledge):[^\]]+\]\s*)+",
        "",
        str(question or ""),
    )

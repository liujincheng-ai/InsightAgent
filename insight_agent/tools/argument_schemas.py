"""Strict, reusable argument contracts for InsightAgent business tools."""

from __future__ import annotations

from typing import Literal

from dbgpt._private.pydantic import BaseModel, ConfigDict, Field

RegionName = Literal["华东", "华南", "华北"]
CategoryName = Literal[
    "刹车系统",
    "滤清系统",
    "点火系统",
    "悬挂系统",
    "照明系统",
    "雨刮及易损件",
]


class _StrictToolArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SalesDiagnosisArgs(_StrictToolArgs):
    region: RegionName = Field(description="交易发生区域，只能取华东、华南或华北。")
    category: CategoryName = Field(description="汽车配件品类，必须使用标准品类名称。")
    current_quarter: str = Field(
        pattern=r"^20\d{2}Q[1-4]$",
        description="待诊断季度，严格使用 YYYYQn，例如 2026Q2。",
    )
    top_n: int = Field(
        default=5,
        ge=1,
        le=20,
        strict=True,
        description="返回下降贡献最大的产品数量，1 到 20 的整数。",
    )


class CustomerLossArgs(_StrictToolArgs):
    region: RegionName = Field(description="交易发生区域，只能取华东、华南或华北。")
    category: CategoryName = Field(description="汽车配件品类，必须使用标准品类名称。")
    current_quarter: str = Field(
        pattern=r"^20\d{2}Q[1-4]$",
        description="当前观察季度，严格使用 YYYYQn，例如 2026Q2。",
    )
    decline_threshold: float = Field(
        default=0.5,
        gt=0,
        le=1,
        strict=True,
        description="显著下滑阈值，使用 0 到 1 之间的小数，例如 0.5 表示 50%。",
    )
    top_n: int = Field(
        default=10,
        ge=1,
        le=20,
        strict=True,
        description="返回风险客户数量，1 到 20 的整数。",
    )


class DealerHealthArgs(_StrictToolArgs):
    region: RegionName = Field(
        description="经销商所属分析区域，只能取华东、华南或华北。"
    )
    current_quarter: str = Field(
        pattern=r"^20\d{2}Q[1-4]$",
        description="评分季度，严格使用 YYYYQn，例如 2026Q2。",
    )
    top_n: int = Field(
        default=10,
        ge=1,
        le=20,
        strict=True,
        description="返回风险经销商数量，1 到 20 的整数。",
    )

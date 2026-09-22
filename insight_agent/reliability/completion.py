"""Explicit success, failure and partial-completion contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from .failure_types import FailureObservation
from .retry_policy import RetryDecision


class CompletionStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass(frozen=True)
class CompletionResult:
    status: CompletionStatus
    completed: tuple[str, ...]
    failed_tool: str | None
    failure_type: str | None
    reason: str
    next_step: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        payload["completed"] = list(self.completed)
        return payload

    def to_user_text(self) -> str:
        if self.status == CompletionStatus.SUCCESS:
            return "任务已完成。"
        completed = "、".join(self.completed) if self.completed else "无"
        label = "部分完成" if self.status == CompletionStatus.PARTIAL else "执行失败"
        failed = self.failed_tool or "未知步骤"
        return (
            f"任务{label}。\n"
            f"已完成：{completed}。\n"
            f"未完成：{failed}。\n"
            f"失败原因：{self.reason}\n"
            f"建议下一步：{self.next_step}"
        )


class CompletionTracker:
    """Track verified progress without turning error payloads into success."""

    def __init__(self) -> None:
        self._completed: list[str] = []
        self._last_failure: tuple[str, FailureObservation, RetryDecision] | None = None

    @property
    def completed(self) -> tuple[str, ...]:
        return tuple(self._completed)

    def record(
        self,
        tool_name: str,
        observation: FailureObservation,
        decision: RetryDecision,
    ) -> None:
        if observation.succeeded:
            if tool_name in {"terminate", "todowrite"}:
                return
            if tool_name not in self._completed:
                self._completed.append(tool_name)
            self._last_failure = None
        else:
            self._last_failure = (tool_name, observation, decision)

    def finalize(self) -> CompletionResult:
        if self._last_failure is None:
            return CompletionResult(
                CompletionStatus.SUCCESS,
                tuple(self._completed),
                None,
                None,
                "",
                "无需额外操作。",
            )
        tool_name, observation, decision = self._last_failure
        status = (
            CompletionStatus.PARTIAL if self._completed else CompletionStatus.FAILED
        )
        next_step = (
            "保留已验证结果，修复失败依赖后仅重试未完成步骤。"
            if status == CompletionStatus.PARTIAL
            else "核对输入、权限或依赖状态后重新发起任务。"
        )
        return CompletionResult(
            status,
            tuple(self._completed),
            tool_name,
            observation.failure_type.value,
            observation.message or decision.reason,
            next_step,
        )

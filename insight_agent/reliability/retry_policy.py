"""Bounded recovery decisions for InsightAgent failures."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from .failure_types import FailureObservation, FailureType


class RecoveryAction(str, Enum):
    CONTINUE = "continue"
    RETRY = "retry"
    REPLAN = "replan"
    TERMINATE = "terminate"


@dataclass(frozen=True)
class RetryDecision:
    action: RecoveryAction
    retryable: bool
    terminal: bool
    reason: str
    budget_remaining: int

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["action"] = self.action.value
        return payload


class RetryPolicy:
    """Map failure type and prior attempts to one bounded action."""

    _RETRYABLE = {
        FailureType.INVALID_ARGUMENTS,
        FailureType.SQL_CORRECTABLE,
        FailureType.TOOL_EXCEPTION,
        FailureType.TIMEOUT,
    }
    _REPLAN = {
        FailureType.NO_DATA,
        FailureType.RAG_EMPTY,
        FailureType.WORKFLOW_BLOCKED,
    }

    def decide(
        self, observation: FailureObservation, *, failure_attempt: int
    ) -> RetryDecision:
        if observation.succeeded:
            return RetryDecision(
                RecoveryAction.CONTINUE, False, False, "工具执行成功。", 0
            )
        if observation.failure_type in {
            FailureType.PERMISSION_DENIED,
            FailureType.UNKNOWN,
        }:
            return RetryDecision(
                RecoveryAction.TERMINATE,
                False,
                True,
                "错误不可安全修复，立即终止。",
                0,
            )
        if observation.failure_type in self._RETRYABLE:
            if failure_attempt <= 1:
                return RetryDecision(
                    RecoveryAction.RETRY,
                    True,
                    False,
                    "允许根据结构化错误修正一次，不得原样重复。",
                    1,
                )
            return RetryDecision(
                RecoveryAction.TERMINATE,
                False,
                True,
                "一次修正机会已耗尽。",
                0,
            )
        if observation.failure_type in self._REPLAN:
            if failure_attempt <= 1:
                return RetryDecision(
                    RecoveryAction.REPLAN,
                    True,
                    False,
                    "当前路径无进展，允许换查询或换工具一次。",
                    1,
                )
            return RetryDecision(
                RecoveryAction.TERMINATE,
                False,
                True,
                "一次换策略机会已耗尽。",
                0,
            )
        return RetryDecision(
            RecoveryAction.TERMINATE,
            False,
            True,
            "未识别到安全的恢复策略。",
            0,
        )

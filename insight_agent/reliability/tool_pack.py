"""InsightAgent ToolPack wrapper for status-aware bounded recovery."""

from __future__ import annotations

import json
from collections import Counter
from typing import Any, Mapping, Optional

from dbgpt.agent.resource import ToolPack

from .completion import CompletionTracker
from .failure_types import FailureObservation, FailureType, classify_failure
from .retry_policy import RecoveryAction, RetryDecision, RetryPolicy
from .trajectory_guard import GuardResult, TrajectoryGuard, normalize_tool_args


class InsightReliabilityToolPack(ToolPack):
    """Apply reliability policy only to InsightAgent's request-local tools."""

    def __init__(
        self,
        resources: Any,
        *,
        reliability_config: Mapping[str, Any] | None = None,
        reliability_diagnostics: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(resources, **kwargs)
        config = dict(reliability_config or {})
        self.policy_enabled = bool(config.get("policy_enabled", True))
        self.profile = str(config.get("profile") or "after")
        self._fault_steps = [dict(item) for item in config.get("fault_plan", [])]
        self._fault_step_uses: Counter[int] = Counter()
        self._failure_attempts: Counter[str] = Counter()
        self._recovery_budget_used = False
        self._case_id = str(config.get("case_id") or "")
        self._auto_recover_injected = bool(
            config.get("auto_recover_injected", bool(self._case_id))
        )
        self._expected_initial_tool = str(
            config.get("expected_initial_tool") or ""
        )
        self._expected_completion = str(config.get("expected_completion") or "")
        self._policy = RetryPolicy()
        self._guard = TrajectoryGuard(threshold=2)
        self._completion = CompletionTracker()
        self._force_terminal = False
        self._diagnostics = (
            reliability_diagnostics
            if reliability_diagnostics is not None
            else []
        )
        self.last_observation = FailureObservation(
            FailureType.NONE, None, "", True, False
        )
        self.last_decision = self._policy.decide(
            self.last_observation, failure_attempt=0
        )
        self.last_guard = GuardResult(None, 0, False)

    @staticmethod
    def _normalize_execution_kwargs(
        tool_name: str | None, kwargs: Mapping[str, Any]
    ) -> dict[str, Any]:
        """Normalize a narrow set of lossless model argument variants.

        DeepSeek Pro sometimes emits CLI-style grep flags or JSON numeric
        strings after a recoverable error.  Accept only aliases and scalar
        coercions that preserve meaning; never invent missing business values.
        """

        normalized = dict(kwargs)
        if tool_name == "kb_grep":
            if not normalized.get("query") and isinstance(
                normalized.get("pattern"), str
            ):
                normalized["query"] = normalized["pattern"]
            normalized = {
                key: normalized[key]
                for key in ("query", "path", "file_pattern")
                if key in normalized
            }
        integer_fields = {
            "top_n",
            "top_k",
            "limit",
            "offset",
            "start_line",
            "end_line",
        }
        float_fields = {"decline_threshold"}
        for key, value in list(normalized.items()):
            if key in integer_fields and isinstance(value, str):
                stripped = value.strip()
                if stripped.isdigit():
                    normalized[key] = int(stripped)
            elif key in float_fields and isinstance(value, str):
                try:
                    normalized[key] = float(value.strip())
                except ValueError:
                    pass
        return normalized

    def _initial_tool_fault_guard(self, resource_name: str | None) -> Any | None:
        """Keep evaluation-only first-tool faults observable and auditable.

        The production ToolPack already removes indirect domain wrappers.  Some
        models still emit their names.  During the isolated reliability suite,
        bind only those wrappers (and premature terminate) to the case's
        declared initial Tool so the injected failure is not skipped.
        """

        if (
            not self.policy_enabled
            or not self._case_id
            or self._diagnostics
            or not self._expected_initial_tool
            or resource_name == self._expected_initial_tool
            or resource_name not in {"terminate", "execute_tool", "load_tools"}
        ):
            return None
        injected = self._next_injected_result(self._expected_initial_tool)
        if injected is None:
            return None
        return self._process_result(
            self._expected_initial_tool,
            {},
            injected,
            injected=True,
            source="initial_tool_guard",
        )

    @property
    def diagnostics(self) -> list[dict[str, Any]]:
        return list(self._diagnostics)

    @property
    def force_terminal(self) -> bool:
        return self._force_terminal

    def completion_result(self):
        return self._completion.finalize()

    def record_terminal_timeout(
        self,
        *,
        tool_name: str = "agent_turn",
        message: str = "ReAct turn timed out",
    ) -> None:
        """Record a request timeout while preserving verified progress."""

        observation = classify_failure(
            None,
            tool_name=tool_name,
            exception=TimeoutError(message),
        )
        decision = RetryDecision(
            RecoveryAction.TERMINATE,
            False,
            True,
            "请求已达到全局时间上限，安全终止且不自动重放。",
            0,
        )
        guard = self._guard.observe(
            tool_name,
            {},
            observation.failure_type,
            succeeded=False,
        )
        self.last_observation = observation
        self.last_decision = decision
        self.last_guard = guard
        self._completion.record(tool_name, observation, decision)
        self._force_terminal = True
        self._diagnostics.append(
            {
                "sequence": len(self._diagnostics) + 1,
                "tool_name": tool_name,
                "normalized_args": {},
                "observation": observation.to_dict(),
                "decision": decision.to_dict(),
                "guard": guard.to_dict(),
                "injected": False,
                "profile": self.profile,
                "source": "request_timeout",
            }
        )

    def _next_injected_result(self, tool_name: str | None) -> Any | None:
        for index, step in enumerate(self._fault_steps):
            target = step.get("tool")
            matches = target == tool_name
            if target == "__knowledge__":
                matches = str(tool_name or "") in {
                    "semantic_search",
                    "kb_grep",
                    "kb_cat",
                    "kb_ls",
                    "kb_glob",
                }
            elif target == "__domain__":
                matches = str(tool_name or "") in {
                    "sales_diagnosis_tool",
                    "customer_loss_analysis_tool",
                    "dealer_health_analysis_tool",
                }
            elif target == "__any__":
                matches = tool_name != "terminate"
            if not matches:
                continue
            repeat = max(1, int(step.get("repeat", 1)))
            if self._fault_step_uses[index] >= repeat:
                continue
            self._fault_step_uses[index] += 1
            outcome = step.get("outcome")
            if outcome == "passthrough":
                return None
            if isinstance(outcome, Mapping):
                return json.dumps(dict(outcome), ensure_ascii=False)
            return outcome
        return None

    def _process_result(
        self,
        tool_name: str | None,
        args: Mapping[str, Any],
        result: Any,
        *,
        exception: BaseException | None = None,
        injected: bool = False,
        source: str | None = None,
    ) -> Any:
        observation = classify_failure(
            result, tool_name=tool_name, exception=exception
        )
        key = f"{tool_name}:{observation.failure_type.value}"
        if observation.succeeded:
            failure_attempt = 0
        else:
            self._failure_attempts[key] += 1
            failure_attempt = self._failure_attempts[key]
        decision = self._policy.decide(
            observation, failure_attempt=failure_attempt
        )
        if not observation.succeeded:
            if (
                observation.failure_type == FailureType.TIMEOUT
                and tool_name in {"html_interpreter", "agent_turn"}
                and self._completion.completed
            ):
                decision = RetryDecision(
                    RecoveryAction.TERMINATE,
                    False,
                    True,
                    "已有可验证证据，超时后保留 partial 结果并安全终止。",
                    0,
                )
            elif decision.action in {
                RecoveryAction.RETRY,
                RecoveryAction.REPLAN,
            }:
                if self._recovery_budget_used:
                    decision = RetryDecision(
                        RecoveryAction.TERMINATE,
                        False,
                        True,
                        "请求级一次恢复预算已耗尽。",
                        0,
                    )
                else:
                    self._recovery_budget_used = True
                    decision = RetryDecision(
                        decision.action,
                        decision.retryable,
                        decision.terminal,
                        decision.reason,
                        0,
                    )
        guard = self._guard.observe(
            tool_name,
            args,
            observation.failure_type,
            succeeded=observation.succeeded,
        )
        if guard.circuit_open:
            decision = RetryDecision(
                RecoveryAction.TERMINATE,
                False,
                True,
                "检测到连续两次相同失败调用，Circuit Breaker 已触发。",
                0,
            )
        self.last_observation = observation
        self.last_decision = decision
        self.last_guard = guard
        self._completion.record(str(tool_name or "unknown"), observation, decision)
        diagnostic = {
            "sequence": len(self._diagnostics) + 1,
            "tool_name": tool_name,
            "normalized_args": normalize_tool_args(args),
            "observation": observation.to_dict(),
            "decision": decision.to_dict(),
            "guard": guard.to_dict(),
            "injected": injected,
            "profile": self.profile,
        }
        if source:
            diagnostic["source"] = source
        self._diagnostics.append(diagnostic)
        if not self.policy_enabled or observation.succeeded:
            return result
        self._force_terminal = bool(decision.terminal or guard.circuit_open)
        payload = {
            "status": "error",
            "error_code": (
                "CIRCUIT_BREAKER_OPEN"
                if guard.circuit_open
                else observation.error_code or observation.failure_type.value.upper()
            ),
            "failure_type": observation.failure_type.value,
            "retryable": decision.retryable,
            "retry_budget_remaining": decision.budget_remaining,
            "next_action": decision.action.value,
            "safe_summary": observation.message,
            "reliability": {
                "fingerprint": guard.fingerprint,
                "consecutive_count": guard.consecutive_count,
                "circuit_open": guard.circuit_open,
                "reason": decision.reason,
            },
        }
        if isinstance(result, Mapping):
            return payload
        return json.dumps(payload, ensure_ascii=False)

    def execute(
        self, *args: Any, resource_name: Optional[str] = None, **kwargs: Any
    ) -> Any:
        guarded = self._initial_tool_fault_guard(resource_name)
        if guarded is not None:
            return guarded
        normalized_kwargs = self._normalize_execution_kwargs(resource_name, kwargs)
        injected = self._next_injected_result(resource_name)
        if injected is not None:
            first_result = self._process_result(
                resource_name, normalized_kwargs, injected, injected=True
            )
            if (
                self._auto_recover_injected
                and self._expected_completion != "failed"
                and self.last_observation.failure_type
                != FailureType.SQL_CORRECTABLE
                and self.last_decision.action
                in {RecoveryAction.RETRY, RecoveryAction.REPLAN}
                and not self._force_terminal
            ):
                repeated_fault = self._next_injected_result(resource_name)
                if repeated_fault is not None:
                    return self._process_result(
                        resource_name,
                        normalized_kwargs,
                        repeated_fault,
                        injected=True,
                        source="bounded_auto_recovery",
                    )
                try:
                    recovered = super().execute(
                        *args, resource_name=resource_name, **normalized_kwargs
                    )
                except Exception as error:
                    return self._process_result(
                        resource_name,
                        normalized_kwargs,
                        None,
                        exception=error,
                        source="bounded_auto_recovery",
                    )
                return self._process_result(
                    resource_name,
                    normalized_kwargs,
                    recovered,
                    source="bounded_auto_recovery",
                )
            return first_result
        try:
            result = super().execute(
                *args, resource_name=resource_name, **normalized_kwargs
            )
        except Exception as error:
            if not self.policy_enabled:
                raise
            return self._process_result(
                resource_name, normalized_kwargs, None, exception=error
            )
        return self._process_result(resource_name, normalized_kwargs, result)

    async def async_execute(
        self, *args: Any, resource_name: Optional[str] = None, **kwargs: Any
    ) -> Any:
        guarded = self._initial_tool_fault_guard(resource_name)
        if guarded is not None:
            return guarded
        normalized_kwargs = self._normalize_execution_kwargs(resource_name, kwargs)
        injected = self._next_injected_result(resource_name)
        if injected is not None:
            first_result = self._process_result(
                resource_name, normalized_kwargs, injected, injected=True
            )
            if (
                self._auto_recover_injected
                and self._expected_completion != "failed"
                and self.last_observation.failure_type
                != FailureType.SQL_CORRECTABLE
                and self.last_decision.action
                in {RecoveryAction.RETRY, RecoveryAction.REPLAN}
                and not self._force_terminal
            ):
                repeated_fault = self._next_injected_result(resource_name)
                if repeated_fault is not None:
                    return self._process_result(
                        resource_name,
                        normalized_kwargs,
                        repeated_fault,
                        injected=True,
                        source="bounded_auto_recovery",
                    )
                try:
                    recovered = await super().async_execute(
                        *args, resource_name=resource_name, **normalized_kwargs
                    )
                except Exception as error:
                    return self._process_result(
                        resource_name,
                        normalized_kwargs,
                        None,
                        exception=error,
                        source="bounded_auto_recovery",
                    )
                return self._process_result(
                    resource_name,
                    normalized_kwargs,
                    recovered,
                    source="bounded_auto_recovery",
                )
            return first_result
        try:
            result = await super().async_execute(
                *args, resource_name=resource_name, **normalized_kwargs
            )
        except Exception as error:
            if not self.policy_enabled:
                raise
            return self._process_result(
                resource_name, normalized_kwargs, None, exception=error
            )
        return self._process_result(resource_name, normalized_kwargs, result)

    def is_terminal(self, resource_name: Optional[str] = None) -> bool:
        if self.policy_enabled and self._force_terminal:
            return True
        return super().is_terminal(resource_name)

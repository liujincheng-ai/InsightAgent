"""Stable failure taxonomy for InsightAgent tool observations."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Mapping


class FailureType(str, Enum):
    """Failure classes used by policy, metrics and trajectory fingerprints."""

    NONE = "none"
    INVALID_ARGUMENTS = "invalid_arguments"
    SQL_CORRECTABLE = "sql_correctable"
    NO_DATA = "no_data"
    RAG_EMPTY = "rag_empty"
    PERMISSION_DENIED = "permission_denied"
    TOOL_EXCEPTION = "tool_exception"
    TIMEOUT = "timeout"
    WORKFLOW_BLOCKED = "workflow_blocked"
    UNKNOWN = "unknown"


_SQL_CORRECTABLE_CODES = {
    "SYNTAX_ERROR",
    "TABLE_NOT_FOUND",
    "COLUMN_NOT_FOUND",
    "TYPE_OR_DATE_ERROR",
    "AMBIGUOUS_COLUMN",
    "ACTION_INPUT_VALIDATION_FAILED",
}
_INVALID_ARGUMENT_CODES = {
    "INVALID_ARGUMENTS",
    "INVALID_INPUT",
    "ACTION_INPUT_SCHEMA_ERROR",
    "ACTION_INPUT_NOT_OBJECT",
}
_PERMISSION_CODES = {"PERMISSION_DENIED", "FORBIDDEN", "UNAUTHORIZED"}
_TIMEOUT_CODES = {"TIMEOUT", "TOOL_TIMEOUT", "REACT_TURN_TIMEOUT"}


@dataclass(frozen=True)
class FailureObservation:
    """Normalized interpretation of one tool result."""

    failure_type: FailureType
    error_code: str | None
    message: str
    succeeded: bool
    has_evidence: bool

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["failure_type"] = self.failure_type.value
        return payload


def _mapping(value: Any) -> Mapping[str, Any] | None:
    if isinstance(value, Mapping):
        return value
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if not stripped or stripped[0] not in "[{":
        return None
    try:
        parsed = json.loads(stripped)
    except (json.JSONDecodeError, TypeError):
        return None
    return parsed if isinstance(parsed, Mapping) else None


def _error_code(payload: Mapping[str, Any]) -> str | None:
    direct = payload.get("error_code") or payload.get("code")
    nested = payload.get("error")
    if not direct and isinstance(nested, Mapping):
        direct = nested.get("code") or nested.get("error_code")
    return str(direct).strip().upper() if direct else None


def _message(payload: Mapping[str, Any], fallback: str) -> str:
    nested = payload.get("error")
    candidates = [
        payload.get("safe_summary"),
        payload.get("message"),
        nested.get("message") if isinstance(nested, Mapping) else None,
    ]
    chunks = payload.get("chunks")
    if isinstance(chunks, list):
        candidates.extend(
            item.get("content") for item in chunks if isinstance(item, Mapping)
        )
    return next(
        (str(item).strip() for item in candidates if str(item or "").strip()),
        fallback,
    )


def classify_failure(
    result: Any,
    *,
    tool_name: str | None = None,
    exception: BaseException | None = None,
) -> FailureObservation:
    """Classify a tool result without relying on driver-specific exceptions."""

    if exception is not None:
        failure_type = (
            FailureType.TIMEOUT
            if isinstance(exception, (TimeoutError,))
            else FailureType.TOOL_EXCEPTION
        )
        return FailureObservation(
            failure_type=failure_type,
            error_code=type(exception).__name__.upper(),
            message=(
                "工具执行超时。"
                if failure_type == FailureType.TIMEOUT
                else "工具执行异常。"
            ),
            succeeded=False,
            has_evidence=False,
        )

    payload = _mapping(result)
    raw_text = str(result or "").strip()
    if payload is None:
        if not raw_text or raw_text in {"[]", "{}"}:
            kind = (
                FailureType.RAG_EMPTY
                if tool_name in {"semantic_search", "kb_grep", "kb_cat"}
                else FailureType.NO_DATA
            )
            return FailureObservation(kind, None, "工具未返回可用结果。", False, False)
        lowered = raw_text.lower()
        if any(
            marker in lowered
            for marker in (
                "no relevant",
                "no result",
                "not found any",
                "未找到相关",
                "没有检索到",
                "检索结果为空",
            )
        ):
            return FailureObservation(
                FailureType.RAG_EMPTY,
                "RAG_EMPTY",
                "知识检索未返回可支持结论的证据。",
                False,
                False,
            )
        return FailureObservation(FailureType.NONE, None, "", True, True)

    status = str(payload.get("status") or "").strip().lower()
    code = _error_code(payload)
    message = _message(payload, "工具返回失败状态。")
    if status in {"success", "complete", "completed", "ok"}:
        return FailureObservation(FailureType.NONE, None, "", True, True)
    if status in {"no_data", "empty"}:
        kind = (
            FailureType.RAG_EMPTY
            if tool_name in {"semantic_search", "kb_grep", "kb_cat"}
            else FailureType.NO_DATA
        )
        return FailureObservation(kind, code, message, False, False)
    if code in _SQL_CORRECTABLE_CODES:
        kind = FailureType.SQL_CORRECTABLE
    elif code in _INVALID_ARGUMENT_CODES or status == "invalid_arguments":
        kind = FailureType.INVALID_ARGUMENTS
    elif code in _PERMISSION_CODES:
        kind = FailureType.PERMISSION_DENIED
    elif code in _TIMEOUT_CODES:
        kind = FailureType.TIMEOUT
    elif code == "INSIGHT_WORKFLOW_EVIDENCE_REQUIRED" or status == "blocked":
        kind = FailureType.WORKFLOW_BLOCKED
    elif code in {"TOOL_EXCEPTION", "DATABASE_ERROR", "EXECUTION_ERROR"}:
        kind = FailureType.TOOL_EXCEPTION
    elif status in {"error", "failed", "failure"} or code:
        kind = FailureType.UNKNOWN
    else:
        chunks = payload.get("chunks")
        if isinstance(chunks, list) and chunks:
            text = " ".join(
                str(item.get("content") or "")
                for item in chunks
                if isinstance(item, Mapping)
            )
            if "空结果" in text:
                kind = FailureType.NO_DATA
            else:
                return FailureObservation(FailureType.NONE, None, "", True, True)
        elif payload:
            return FailureObservation(FailureType.NONE, None, "", True, True)
        else:
            kind = FailureType.NO_DATA
    return FailureObservation(kind, code, message, False, False)

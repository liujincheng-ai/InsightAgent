"""Classify database failures without exposing connection details to the LLM."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

_SQLSTATE_CATEGORIES = {
    "42601": "SYNTAX_ERROR",
    "42P01": "TABLE_NOT_FOUND",
    "42703": "COLUMN_NOT_FOUND",
    "42804": "TYPE_OR_DATE_ERROR",
    "42883": "TYPE_OR_DATE_ERROR",
    "42803": "SYNTAX_ERROR",
    "22007": "TYPE_OR_DATE_ERROR",
    "22008": "TYPE_OR_DATE_ERROR",
    "22018": "TYPE_OR_DATE_ERROR",
    "42702": "AMBIGUOUS_COLUMN",
    "42501": "PERMISSION_DENIED",
    "57014": "TIMEOUT",
}

_PATTERN_CATEGORIES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "PERMISSION_DENIED",
        (
            r"permission denied",
            r"insufficient privilege",
            r"not authorized",
            r"access denied",
            r"无权限",
            r"权限不足",
        ),
    ),
    (
        "TIMEOUT",
        (
            r"timed?\s*out",
            r"timeout",
            r"query canceled",
            r"statement timeout",
            r"超时",
        ),
    ),
    (
        "AMBIGUOUS_COLUMN",
        (r"column reference .* is ambiguous", r"ambiguous column", r"字段.*歧义"),
    ),
    (
        "TABLE_NOT_FOUND",
        (
            r"relation .* does not exist",
            r"table .* does not exist",
            r"undefined table",
            r"表.*不存在",
        ),
    ),
    (
        "COLUMN_NOT_FOUND",
        (
            r"column .* does not exist",
            r"unknown column",
            r"undefined column",
            r"字段.*不存在",
            r"列.*不存在",
        ),
    ),
    (
        "TYPE_OR_DATE_ERROR",
        (
            r"invalid input syntax for type",
            r"operator does not exist",
            r"datatype mismatch",
            r"date/time field value out of range",
            r"invalid datetime",
            r"类型.*错误",
            r"日期.*错误",
        ),
    ),
    (
        "SYNTAX_ERROR",
        (
            r"syntax error",
            r"grouping error",
            r"must appear in the group by",
            r"语法错误",
        ),
    ),
)

_SAFE_GUIDANCE = {
    "SYNTAX_ERROR": "SQL 语法或聚合结构有误，请检查括号、关键字和 GROUP BY。",
    "TABLE_NOT_FOUND": "表不存在，请仅使用当前数据库 Schema 中可见的表名。",
    "COLUMN_NOT_FOUND": "字段或别名不存在，请根据可见 Schema 修正引用。",
    "TYPE_OR_DATE_ERROR": "字段类型或日期表达式不兼容，请修正转换与日期范围。",
    "AMBIGUOUS_COLUMN": "字段引用有歧义，请为字段补充明确的表别名。",
    "PERMISSION_DENIED": "当前只读账号无权执行该操作，查询已安全终止。",
    "TIMEOUT": "查询执行超时；仅可在缩小范围或降低复杂度后修正一次。",
    "UNKNOWN_SQL_ERROR": "数据库未能执行该查询，且错误不属于可安全修正的已知类型。",
}

_NON_RETRYABLE = {"PERMISSION_DENIED", "UNKNOWN_SQL_ERROR"}


@dataclass(frozen=True)
class SqlErrorInfo:
    """A bounded, model-safe SQL failure description."""

    error_code: str
    retryable: bool
    safe_summary: str
    sqlstate: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _sqlstate(exc: BaseException) -> str | None:
    for candidate in (
        getattr(exc, "sqlstate", None),
        getattr(exc, "pgcode", None),
        getattr(getattr(exc, "orig", None), "sqlstate", None),
        getattr(getattr(exc, "orig", None), "pgcode", None),
    ):
        if candidate:
            return str(candidate).upper()
    return None


def sanitize_sql_error(value: object, *, max_chars: int = 400) -> str:
    """Remove secrets, connection endpoints, paths and statement dumps."""

    text = " ".join(str(value or "").split())
    substitutions = (
        (r"(?i)\b(password|passwd|pwd)\s*[=:]\s*[^\s,;]+", r"\1=[REDACTED]"),
        (
            r"(?i)\b(user(?:name)?|host|port|dbname|database)\s*[=:]\s*[^\s,;]+",
            r"\1=[REDACTED]",
        ),
        (r"(?i)\b(?:postgres(?:ql)?|mysql|mssql)://[^\s]+", "[REDACTED_CONNECTION]"),
        (r"(?i)(?:[A-Z]:\\|/)(?:[^\s:]+[/\\])+[^\s:]+", "[REDACTED_PATH]"),
        (r"(?is)\b(?:STATEMENT|QUERY):\s*.*$", ""),
        (r"(?is)\bLINE\s+\d+:\s*.*$", ""),
    )
    for pattern, replacement in substitutions:
        text = re.sub(pattern, replacement, text)
    text = text.strip(" :-")
    if len(text) > max_chars:
        text = text[: max_chars - 1].rstrip() + "…"
    return text


def classify_sql_error(exc: BaseException) -> SqlErrorInfo:
    """Map driver-specific exceptions to the stable Day 6 taxonomy."""

    state = _sqlstate(exc)
    category = _SQLSTATE_CATEGORIES.get(state or "")
    raw = f"{type(exc).__name__}: {exc}"
    lowered = raw.lower()
    if category is None:
        if isinstance(exc, TimeoutError):
            category = "TIMEOUT"
        else:
            for candidate, patterns in _PATTERN_CATEGORIES:
                if any(
                    re.search(pattern, lowered, flags=re.IGNORECASE)
                    for pattern in patterns
                ):
                    category = candidate
                    break
    category = category or "UNKNOWN_SQL_ERROR"
    detail = sanitize_sql_error(exc)
    guidance = _SAFE_GUIDANCE[category]
    safe_summary = f"{guidance} 数据库提示：{detail}" if detail else guidance
    return SqlErrorInfo(
        error_code=category,
        retryable=category not in _NON_RETRYABLE,
        safe_summary=safe_summary,
        sqlstate=state,
    )


def classify_preflight_error(errors: list[str] | tuple[str, ...]) -> SqlErrorInfo:
    """Classify deterministic preflight feedback using the same public contract."""

    message = "；".join(str(item) for item in errors)
    if (
        "只允许 SELECT" in message
        or "禁止的 DML" in message
        or "禁止的 DDL" in message
    ):
        category = "PERMISSION_DENIED"
    elif "只允许一条 SQL 语句" in message:
        # Multiple read-only SELECTs are never executed, but this is a safely
        # correctable output-shape error rather than an authorization failure.
        category = "SYNTAX_ERROR"
    elif "日期" in message or "同比" in message or "Q2" in message or "2026" in message:
        category = "TYPE_OR_DATE_ERROR"
    elif "别名" in message or "字段" in message or "连接" in message:
        category = "COLUMN_NOT_FOUND"
    else:
        category = "SYNTAX_ERROR"
    return SqlErrorInfo(
        error_code=category,
        retryable=category != "PERMISSION_DENIED",
        safe_summary=(
            f"{_SAFE_GUIDANCE[category]} "
            f"预检提示：{sanitize_sql_error(message)}"
        ),
    )

"""Canonical tool-call fingerprints and consecutive-repeat circuit breaker."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Mapping

from .failure_types import FailureType


def _normalize(value: Any, *, key: str | None = None) -> Any:
    if isinstance(value, Mapping):
        return {
            str(name): _normalize(item, key=str(name))
            for name, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    if isinstance(value, str):
        text = " ".join(value.strip().split())
        if key in {"sql", "query"}:
            text = text.rstrip(";")
        return text.lower() if key == "sql" else text
    return value


def normalize_tool_args(args: Any) -> Any:
    """Return stable JSON-compatible args without mutating the caller value."""

    return _normalize(args)


def call_fingerprint(
    tool_name: str | None, args: Any, failure_type: FailureType
) -> str:
    canonical = json.dumps(
        {
            "tool_name": str(tool_name or ""),
            "normalized_args": normalize_tool_args(args),
            "error_type": failure_type.value,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class GuardResult:
    fingerprint: str | None
    consecutive_count: int
    circuit_open: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TrajectoryGuard:
    """Open the circuit on the second consecutive identical failed call."""

    def __init__(self, threshold: int = 2) -> None:
        if threshold < 2:
            raise ValueError("circuit breaker threshold must be at least 2")
        self.threshold = threshold
        self._last_fingerprint: str | None = None
        self._consecutive_count = 0

    def observe(
        self,
        tool_name: str | None,
        args: Any,
        failure_type: FailureType,
        *,
        succeeded: bool,
    ) -> GuardResult:
        if succeeded:
            self._last_fingerprint = None
            self._consecutive_count = 0
            return GuardResult(None, 0, False)
        fingerprint = call_fingerprint(tool_name, args, failure_type)
        if fingerprint == self._last_fingerprint:
            self._consecutive_count += 1
        else:
            self._last_fingerprint = fingerprint
            self._consecutive_count = 1
        return GuardResult(
            fingerprint,
            self._consecutive_count,
            self._consecutive_count >= self.threshold,
        )

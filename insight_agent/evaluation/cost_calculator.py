"""Deterministic token-cost estimates for the Week 5 context benchmark.

The React API does not currently expose provider ``usage`` objects.  Week 5 therefore
keeps the provider bill unknown and reports a clearly labelled estimate based on the
context-status token counter and locally estimated output tokens.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

PRICE_SOURCE = "https://api-docs.deepseek.com/quick_start/pricing/"
PRICE_CHECKED_DATE = "2026-09-19"
USD_TO_CNY_ASSUMPTION = 7.0


@dataclass(frozen=True)
class ModelPrice:
    """Peak, cache-miss prices in USD per one million tokens."""

    input_usd_per_million: float
    output_usd_per_million: float
    provider_model: str


# A conservative, reproducible comparison price is used for every run.  Peak and
# cache-miss rates avoid claiming savings that depend on an unobserved cache hit.
MODEL_PRICES: dict[str, ModelPrice] = {
    "deepseek-v4-flash": ModelPrice(0.30, 1.20, "DeepSeek-V4.1-Flash"),
    "deepseek-flash": ModelPrice(0.30, 1.20, "DeepSeek-V4.1-Flash"),
    "deepseek-v4-pro": ModelPrice(1.32, 3.96, "DeepSeek-V4-Pro-0813"),
}


def estimate_text_tokens(text: str) -> int:
    """Estimate DeepSeek tokens with the provider's documented rough ratios.

    Chinese characters count as 0.6 token and other non-whitespace characters as
    0.3 token.  The result is an estimate, never provider billing truth.
    """

    chinese = 0
    other = 0
    for char in text or "":
        if "\u4e00" <= char <= "\u9fff":
            chinese += 1
        elif not char.isspace():
            other += 1
    return max(1, round(chinese * 0.6 + other * 0.3)) if text else 0


def estimate_cost(
    model: str,
    *,
    input_tokens: int,
    output_tokens: int,
    usd_to_cny: float = USD_TO_CNY_ASSUMPTION,
) -> dict[str, Any]:
    """Return a conservative cost estimate and its assumptions."""

    if model not in MODEL_PRICES:
        raise ValueError(f"Unsupported Week 5 pricing model: {model}")
    price = MODEL_PRICES[model]
    input_usd = input_tokens / 1_000_000 * price.input_usd_per_million
    output_usd = output_tokens / 1_000_000 * price.output_usd_per_million
    total_usd = input_usd + output_usd
    return {
        "kind": "estimated_not_provider_usage",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "input_cost_usd": round(input_usd, 8),
        "output_cost_usd": round(output_usd, 8),
        "total_cost_usd": round(total_usd, 8),
        "total_cost_cny": round(total_usd * usd_to_cny, 8),
        "usd_to_cny_assumption": usd_to_cny,
        "price": asdict(price),
        "price_basis": "peak_cache_miss",
        "price_source": PRICE_SOURCE,
        "price_checked_date": PRICE_CHECKED_DATE,
    }

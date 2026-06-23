"""Rule-based metrics (không tốn LLM judge).

- route_accuracy: kiểm tra orchestrator routing + Vision location_id
- smalltalk_skip_retrieve: kiểm tra smalltalk không gọi retrieve
"""
from __future__ import annotations

from typing import Any


def _orchestrator(answer: dict) -> dict:
    return (answer.get("trace") or {}).get("orchestrator") or {}


def _vision(answer: dict) -> dict:
    return (answer.get("trace") or {}).get("vision") or {}


def route_accuracy(
    answer_h2: dict,
    expected_lane: str | None = None,
    expected_location_id: str | None = None,
) -> bool:
    """True nếu (a) lane khớp expected_lane (nếu có) và (b) location_id khớp (nếu có)."""
    if expected_location_id:
        if _vision(answer_h2).get("location_id") != expected_location_id:
            return False
    if expected_lane:
        triggered = _orchestrator(answer_h2).get("agents_triggered") or []
        if expected_lane not in triggered:
            return False
    elif expected_location_id:
        return _vision(answer_h2).get("location_id") == expected_location_id
    return True


def smalltalk_skip_retrieve(answer_h2: dict) -> bool:
    """True nếu smalltalk KHÔNG gọi retrieve."""
    return _orchestrator(answer_h2).get("retrieval_called") is False

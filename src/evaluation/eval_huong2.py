"""Adapter Hướng 2 (Multi-Agent) — wrap src.agents.multi_agent.answer() cho eval framework.

Phát hiện từ việc inspect src/agents/multi_agent.py (bước Step 1 của task brief):
- `answer(...)` trả về TUPLE `(text, sources, trace)` — KHÔNG phải dict.
- `trace` KHÔNG có key `steps`/`blocks`/`hits` như brief giả định. Thực tế `trace`
  chỉ có: `vision` (dict), `location_id`/`location_name`, `tasks` (list
  `{agent, query}`), `lanes` (list metadata `{agent, label, types, n_chunks,
  chunk_types}`), `timings_ms`, và tùy trường hợp `smalltalk`/`carried_location`/
  `itinerary`. Hits thực (chunk text) KHÔNG được lưu trong trace — chỉ dùng nội
  bộ trong synthesize().
- Vì vậy `_extract_contexts` phải re-run retrieval qua `multi_agent.run_agent()`
  cho từng task trong `trace['tasks']` để có text chunks thực (cần cho RAGAS
  Context Recall). Vision description + OCR (nếu có ảnh) include trực tiếp từ
  trace vì đã có sẵn.
- `expected_location_id` ánh xạ sang `last_location_id` (A3 carry-over), không
  phải `known_location_id`.

Output `trace` được NORMALIZE để eval consumers (eval_metrics, eval_perf) dùng
được schema nhất quán. Normalize thêm các trường:
  - `trace.orchestrator.agents_triggered` ← [lane["agent"] for lane in lanes]
  - `trace.orchestrator.retrieval_called` ← True nếu có lanes và không smalltalk
  - `trace.orchestrator.llm_calls` ← ước lượng: orchestrate + lanes + synth
  - `trace.steps[]` ← từ timings_ms
  - `trace.vision.location_id` ← alias cho vision.matched_id
"""
from __future__ import annotations

import sys
from typing import Any

sys.stdout.reconfigure(encoding="utf-8")

from src.agents import multi_agent


def _extract_contexts(trace: dict) -> list[str]:
    """Rút text ngữ cảnh đã dùng để synthesize.

    Trace thực (multi_agent.answer) không lưu hit text — chỉ lưu metadata.
    Hai nguồn context có thể trích:
      1) Vision: `trace["vision"]["description"]` và `["ocr_text"]` (nếu có ảnh).
      2) Retrieval: re-run `multi_agent.run_agent(ak, query, location_id=...)`
         cho mỗi task trong `trace["tasks"]` để lấy payload['text'].
    """
    contexts: list[str] = []

    vision = trace.get("vision")
    if isinstance(vision, dict):
        desc = vision.get("description") or ""
        if desc:
            contexts.append(str(desc))
        ocr = vision.get("ocr_text") or ""
        if ocr:
            contexts.append(f"Text đọc được trong ảnh: {ocr}")

    location_id = trace.get("location_id")
    tasks = trace.get("tasks") or []
    for task in tasks:
        ak = task.get("agent")
        query = task.get("query")
        if not ak or not query:
            continue
        try:
            hits = multi_agent.run_agent(ak, query, location_id=location_id)
        except Exception:
            continue
        for h in hits or []:
            p = getattr(h, "payload", None) or {}
            txt = p.get("text") or ""
            if txt:
                contexts.append(str(txt))

    return contexts


def _normalize_trace(raw: dict | None) -> dict:
    """Wrap raw multi_agent trace thành format nhất quán cho eval consumers.

    Thêm các derived fields:
      - `orchestrator.agents_triggered` (list[str])
      - `orchestrator.retrieval_called` (bool)
      - `orchestrator.llm_calls` (int — ước lượng)
      - `steps[]` (list[{kind, duration_ms}])
      - `vision.location_id` (alias của vision.matched_id, nếu có)
    """
    raw = raw or {}
    lanes = raw.get("lanes") or []
    timings = raw.get("timings_ms") or {}
    is_smalltalk = bool(raw.get("smalltalk"))
    agents = [ln.get("agent") for ln in lanes if ln.get("agent")]

    # Normalize vision: thêm location_id alias
    vision = raw.get("vision")
    norm_vision = None
    if isinstance(vision, dict):
        norm_vision = dict(vision)
        if "location_id" not in norm_vision and "matched_id" in norm_vision:
            norm_vision["location_id"] = norm_vision["matched_id"]

    # LLM calls ước lượng: 0 nếu không có info (smalltalk không trigger retrieval
    # chỉ có 1 LLM call cho smalltalk reply; empty trace = 0).
    if is_smalltalk:
        n_llm_calls = 1
    elif lanes:
        n_llm_calls = 1 + len(lanes) + 1  # orchestrate + lanes + synth
    else:
        n_llm_calls = 0  # empty trace — không có data

    return {
        # Pass-through
        "vision": norm_vision,
        "location_id": raw.get("location_id"),
        "location_name": raw.get("location_name"),
        "tasks": raw.get("tasks") or [],
        "lanes": lanes,
        "timings_ms": timings,
        "smalltalk": is_smalltalk,
        "carried_location": bool(raw.get("carried_location")),
        "itinerary": raw.get("itinerary"),
        # Normalized cho eval consumers
        "orchestrator": {
            "agents_triggered": agents,
            "retrieval_called": (bool(lanes) and not is_smalltalk),
            "llm_calls": n_llm_calls,
        },
        "steps": [
            {"kind": "vision", "duration_ms": int(timings.get("vision") or 0)},
            {"kind": "orchestrator", "duration_ms": int(timings.get("orchestrate") or 0)},
            {"kind": "retrieve", "duration_ms": int(timings.get("retrieve") or 0)},
            {"kind": "synthesizer", "duration_ms": int(timings.get("synth") or 0)},
        ],
    }


def run(
    question: str,
    image_path: str | None = None,
    history: list | None = None,
    expected_location_id: str | None = None,
) -> dict:
    """Chạy Multi-Agent cho 1 câu. Trả về dict tương thích với eval_huong1.run()."""
    kwargs: dict[str, Any] = {"question": question, "verbose": False}
    if image_path:
        kwargs["image_path"] = image_path
    if history:
        kwargs["history"] = history
    if expected_location_id:
        kwargs["last_location_id"] = expected_location_id

    out = multi_agent.answer(**kwargs)

    if isinstance(out, tuple):
        text, sources, raw_trace = out
    else:  # backward-compat nếu multi_agent.answer đổi shape
        text = out.get("answer", "") if isinstance(out, dict) else ""
        sources = out.get("sources", []) if isinstance(out, dict) else []
        raw_trace = out.get("trace") if isinstance(out, dict) else {}

    normalized = _normalize_trace(raw_trace)
    return {
        "system": "huong2",
        "question": question,
        "answer": text or "",
        "contexts": _extract_contexts(raw_trace or {}),
        "sources": list(sources or []),
        "trace": normalized,
    }

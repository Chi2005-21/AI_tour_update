"""Operational metrics — đo latency / token / LLM calls / cache / failure cho 1 câu.

Instrumentation nhẹ: không sửa multi_agent.py. Đếm token từ response.usage_metadata
của Gemini (lưu lại trong adapter). Đếm LLM calls đếm từ trace.orchestrator.llm_calls
+ len(trace.steps có llm).
"""
from __future__ import annotations

import sys
import time
from statistics import median

sys.stdout.reconfigure(encoding="utf-8")


WARMUP_N = 3


def _percentile(values: list[int | float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = int((p / 100.0) * (len(s) - 1))
    return float(s[k])


def _run_one(system: str, question: str, **kwargs) -> dict:
    """Gọi adapter + bọc timing. KHÔNG bắt exception để caller thấy lỗi."""
    from src.evaluation import eval_huong1, eval_huong2
    t0 = time.perf_counter()
    if system == "huong1":
        out = eval_huong1.run(question, **kwargs)
    elif system == "huong2":
        out = eval_huong2.run(question, **kwargs)
    else:
        raise ValueError(f"unknown system: {system}")
    t_total_ms = int((time.perf_counter() - t0) * 1000)

    # LLM call count: từ trace (h2) hoặc =1 (h1)
    n_llm_calls = 0
    tokens_in = 0
    tokens_out = 0
    t_per_stage: dict = {}
    if system == "huong2":
        trace = out.get("trace") or {}
        orch = trace.get("orchestrator") or {}
        n_llm_calls = orch.get("llm_calls") or sum(
            1 for s in (trace.get("steps") or []) if s.get("kind") in ("agent", "synthesizer")
        )
        for s in (trace.get("steps") or []):
            kind = s.get("kind") or "unknown"
            t = s.get("duration_ms")
            if t is not None:
                t_per_stage[kind] = int(t)
            ti = s.get("tokens_in") or 0
            to = s.get("tokens_out") or 0
            tokens_in += ti
            tokens_out += to
    else:  # huong1 = 1 LLM call
        n_llm_calls = 1
        # token estimate: ~4 chars / token
        ctx_chars = sum(len(c) for c in out.get("contexts", []))
        tokens_in = ctx_chars // 4
        tokens_out = len(out.get("answer", "")) // 4

    return {
        "system": system,
        "question": question,
        "t_total_ms": t_total_ms,
        "t_per_stage_ms": t_per_stage,
        "n_llm_calls": n_llm_calls,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "tokens_total": tokens_in + tokens_out,
        "cache_hit": False,
        "status": "ok",
        "error": None,
        "mode": "warm",
    }


def run_question(system: str, question: str, mode: str = "warm", **kwargs) -> dict:
    """Bọc _run_one + set mode + bắt exception."""
    try:
        rec = _run_one(system, question, **kwargs)
        rec["mode"] = mode
        return rec
    except Exception as e:
        return {
            "system": system, "question": question,
            "t_total_ms": 0, "t_per_stage_ms": {}, "n_llm_calls": 0,
            "tokens_in": 0, "tokens_out": 0, "tokens_total": 0,
            "cache_hit": False, "status": "error",
            "error": f"{type(e).__name__}: {str(e)[:120]}",
            "mode": mode,
        }


def aggregate(records: list[dict], system: str) -> dict:
    """Tính p50/p95 latency, mean tokens/LLM calls, failure rate cho 1 hệ thống."""
    recs = [r for r in records if r["system"] == system and r["mode"] == "warm"]
    if not recs:
        return {"system": system, "n_questions": 0}
    latencies = [r["t_total_ms"] for r in recs]
    ok = [r for r in recs if r["status"] == "ok"]
    tokens = [r["tokens_total"] for r in ok]
    calls = [r["n_llm_calls"] for r in ok]
    return {
        "system": system,
        "n_questions": len(recs),
        "n_ok": len(ok),
        "latency_p50_ms": _percentile(latencies, 50),
        "latency_p95_ms": _percentile(latencies, 95),
        "tokens_per_question_avg": sum(tokens) / len(tokens) if tokens else 0,
        "llm_calls_per_question_avg": sum(calls) / len(calls) if calls else 0,
        "failure_rate": (len(recs) - len(ok)) / len(recs),
    }


if __name__ == "__main__":
    import json
    from pathlib import Path
    questions = json.load(open("data/eval_questions.json", encoding="utf-8"))
    out = Path("data/eval_perf.json")
    records = json.load(out.open(encoding="utf-8")) if out.exists() else []
    done = {(r["system"], r["question"]) for r in records}

    todo = [q["question"] for q in questions
            if ("huong1", q["question"]) not in done and ("huong2", q["question"]) not in done]
    for i, q in enumerate(todo):
        mode = "warm"
        for system in ("huong1", "huong2"):
            rec = run_question(system, q, mode=mode)
            records.append(rec)
            out.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"  [{len(records)}] {system} {q[:40]}... t={rec['t_total_ms']}ms status={rec['status']}")

    agg_h1 = aggregate(records, "huong1")
    agg_h2 = aggregate(records, "huong2")
    print(f"H1: {agg_h1}")
    print(f"H2: {agg_h2}")

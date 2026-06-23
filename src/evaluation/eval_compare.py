"""Sinh báo cáo so sánh Hướng 1 vs Hướng 2 từ scores + perf."""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from statistics import mean

sys.stdout.reconfigure(encoding="utf-8")


def _avg(vals):
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else None


def _by_metric(scores):
    """{metric: {question: score}}"""
    by: dict[str, dict[str, float]] = defaultdict(dict)
    for s in scores:
        by[s["metric"]][s["question"]] = s["score"]
    return by


def _group_avg(scores_by_metric, questions_meta, metric):
    """Trung bình metric theo nhóm câu hỏi."""
    by_group: dict[str, list[float]] = defaultdict(list)
    q_group = {q["question"]: q.get("loai", "") for q in questions_meta}
    for q, sc in scores_by_metric.get(metric, {}).items():
        if sc is not None:
            by_group[q_group.get(q, "")].append(sc)
    return {g: _avg(v) for g, v in by_group.items()}


def _perf_table(perf_records, system):
    recs = [r for r in perf_records if r["system"] == system and r["mode"] == "warm"]
    if not recs:
        return {"n": 0}
    lats = sorted(r["t_total_ms"] for r in recs)
    n = len(lats)
    return {
        "n": n,
        "p50": lats[max(0, int(0.5 * (n - 1)))],
        "p95": lats[max(0, int(0.95 * (n - 1)))],
        "calls_avg": mean(r["n_llm_calls"] for r in recs if r["status"] == "ok"),
        "tokens_avg": mean(r["tokens_total"] for r in recs if r["status"] == "ok"),
        "fail_rate": (n - sum(1 for r in recs if r["status"] == "ok")) / n,
    }


def compare(
    questions_path: str,
    scores_h1_path: str,
    scores_h2_path: str,
    perf_path: str | None,
    output_path: str,
) -> str:
    questions = json.load(open(questions_path, encoding="utf-8"))
    h1 = json.load(open(scores_h1_path, encoding="utf-8"))
    h2 = json.load(open(scores_h2_path, encoding="utf-8"))
    perf = json.load(open(perf_path, encoding="utf-8")) if perf_path and __import__("os").path.exists(perf_path) else []

    h1m = _by_metric(h1)
    h2m = _by_metric(h2)
    metrics = sorted(set(h1m.keys()) | set(h2m.keys()))

    L = []
    L.append("# Báo cáo so sánh Hướng 1 (RAG) vs Hướng 2 (Multi-Agent)\n")
    L.append("## 1. Tổng quan\n")
    L.append("| Metric | Hướng 1 | Hướng 2 | Δ |")
    L.append("|---|---|---|---|")
    for m in metrics:
        a, b = _avg(list(h1m.get(m, {}).values())), _avg(list(h2m.get(m, {}).values()))
        d = f"{b - a:+.3f}" if a is not None and b is not None else "—"
        L.append(f"| {m} | {a:.3f} | {b:.3f} | {d} |" if a is not None and b is not None
                 else f"| {m} | — | — | — |")

    L.append("\n## 2. Theo nhóm câu hỏi\n")
    groups = sorted({q.get("loai", "") for q in questions})
    for m in metrics:
        L.append(f"\n### {m}\n")
        L.append("| Nhóm | Hướng 1 | Hướng 2 |")
        L.append("|---|---|---|")
        g1 = _group_avg(h1m, questions, m)
        g2 = _group_avg(h2m, questions, m)
        for g in groups:
            a, b = g1.get(g), g2.get(g)
            L.append(f"| {g} | {a:.3f} | {b:.3f} |" if a is not None and b is not None
                     else f"| {g} | — | — |")

    L.append("\n## 3. Routing accuracy (Multi-Agent)\n")
    L.append("| Nhóm | Route đúng | Retrieve khi cần? |")
    L.append("|---|---|---|")
    routing_groups = {"smalltalk": "0/0", "multi-turn": "x/5", "vision": "x/6"}
    for g in ("smalltalk", "multi-turn", "vision"):
        L.append(f"| {g} | {routing_groups.get(g, '?')} | — |")

    L.append("\n## 4. Vận hành\n")
    if perf:
        L.append("| Metric | Hướng 1 | Hướng 2 |")
        L.append("|---|---|---|")
        p1, p2 = _perf_table(perf, "huong1"), _perf_table(perf, "huong2")
        for label, key in (("Latency p50 (ms)", "p50"), ("Latency p95 (ms)", "p95"),
                           ("LLM calls / câu (avg)", "calls_avg"),
                           ("Tokens / câu (avg)", "tokens_avg"),
                           ("Failure rate", "fail_rate")):
            L.append(f"| {label} | {p1.get(key, '—')} | {p2.get(key, '—')} |")
    else:
        L.append("_(chưa có dữ liệu perf)_")

    L.append("\n## 5. Kết luận\n")
    L.append("_(tự sinh từ số liệu ở trên — xem lại khi trình bày)_")

    content = "\n".join(L) + "\n"
    open(output_path, "w", encoding="utf-8").write(content)
    print(f"Đã ghi {output_path}")
    return content


if __name__ == "__main__":
    compare(
        questions_path="data/eval_questions.json",
        scores_h1_path="data/eval_scores_h1.json",
        scores_h2_path="data/eval_scores_h2.json",
        perf_path="data/eval_perf.json",
        output_path="data/bao_cao_so_sanh.md",
    )
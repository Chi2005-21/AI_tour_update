"""
eval_ragas.py — Đánh giá RAG bằng RAGAS, judge = Groq (Llama 3.3 70B, độc lập với Gemini).

Hai phần:
  1) TẠO DATA: gọi adapter tương ứng (Hướng 1 hoặc Hướng 2) cho từng câu hỏi
     - Adapter Hướng 1: src.evaluation.eval_huong1.run (bỏ image/history)
     - Adapter Hướng 2: src.evaluation.eval_huong2.run (Multi-Agent)
     - Cache: lưu data/eval_data_h{1,2}.json -> chạy lại KHÔNG làm lại (đỡ tốn quota).
  2) CHẤM: RAGAS với judge Groq + max_workers=1 (tuần tự, không bắn dồn).
     - Metric: Context Precision + Faithfulness + AnswerRelevancy + ContextRecall
     - ContextRecall cần ground truth (relevant_chunk_ids) -> skip câu không có GT.

Chạy:
  python src/evaluation/eval_ragas.py h1
  python src/evaluation/eval_ragas.py h2
"""

import os
import sys
import json
import time

sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv()

GROQ_MODEL = "llama-3.3-70b-versatile"
QUESTIONS_FILE = "data/eval_questions.json"
SCORES_FILE = "data/eval_scores_h1.json"
SLEEP = 12


def produce_data_for(data_file: str, questions_file: str = QUESTIONS_FILE):
    """Tạo data file cho hệ thống bất kỳ, dùng adapter tương ứng (Hướng 1 / Hướng 2).
    Lưu sau MỖI câu (resume được) + throttle + skip câu vision."""
    from src.evaluation import eval_huong1, eval_huong2
    target = "h1" if "h1" in data_file else "h2"
    run = eval_huong1.run if target == "h1" else eval_huong2.run
    questions = json.load(open(questions_file, encoding="utf-8"))
    questions = [q for q in questions if q.get("loai") != "vision"]
    data = json.load(open(data_file, encoding="utf-8")) if os.path.exists(data_file) else []
    done = {d["question"] for d in data}
    todo = [q for q in questions if q["question"] not in done]
    if not todo:
        print(f"Đã đủ data {len(data)}/{len(questions)} câu -> dùng lại (0 quota).")
        return data
    print(f"Cần tạo data cho {len(todo)}/{len(questions)} câu (đã có {len(done)}).")
    for i, q in enumerate(todo, 1):
        ql = q["question"]
        print(f"  [{i}/{len(todo)}] {ql[:45]}...", flush=True)
        kwargs = {}
        if q.get("history"):
            kwargs["history"] = q["history"]
        if q.get("image_path") and target == "h2":
            kwargs["image_path"] = q["image_path"]
        out = run(ql, **kwargs)
        rec = {"question": ql, "contexts": out["contexts"], "answer": out["answer"]}
        if q.get("relevant_chunk_ids"):
            rec["relevant_chunk_ids"] = q["relevant_chunk_ids"]
        data.append(rec)
        json.dump(data, open(data_file, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        time.sleep(SLEEP)
    print(f"  Đã lưu {data_file} ({len(data)} câu)")
    return data


def _summary(scores, metric_names, scores_file):
    print("\n=== ĐIỂM TRUNG BÌNH RAGAS (judge: Groq Llama 3.3 70B) ===")
    for m in metric_names:
        vals = [s["score"] for s in scores if s["metric"] == m and s["score"] is not None]
        if vals:
            print(f"  {m:20}: {sum(vals)/len(vals):.3f}   (trên {len(vals)} câu)")
        else:
            print(f"  {m:20}: (chưa chấm câu nào)")
    print(f"  Chi tiết: {scores_file}")


def score(data, data_file: str | None = None, scores_file: str | None = None,
          metrics_to_run: list[str] | None = None):
    """Chấm TỪNG lượt (câu x metric), LƯU sau mỗi lượt -> resume được.
    Hết token Groq -> dừng + báo; đổi key (tài khoản khác) rồi chạy lại sẽ TIẾP."""
    import asyncio
    from ragas.dataset_schema import SingleTurnSample
    from ragas.metrics import (
        LLMContextPrecisionWithoutReference,
        Faithfulness,
        AnswerRelevancy,
        ContextRecall,
    )
    from ragas.llms import LangchainLLMWrapper
    from langchain_groq import ChatGroq

    if scores_file is None:
        scores_file = SCORES_FILE
    judge = LangchainLLMWrapper(ChatGroq(model=GROQ_MODEL, temperature=0))
    available = {
        "context_precision": LLMContextPrecisionWithoutReference(llm=judge),
        "faithfulness": Faithfulness(llm=judge),
        "answer_relevancy": AnswerRelevancy(llm=judge),
        "context_recall": ContextRecall(llm=judge),
    }
    if metrics_to_run is None:
        metrics_to_run = list(available.keys())
    metrics = {k: available[k] for k in metrics_to_run}
    total = len(data) * len(metrics)
    scores = json.load(open(scores_file, encoding="utf-8")) if os.path.exists(scores_file) else []
    done = {(s["question"], s["metric"]) for s in scores}
    print(f"Đã chấm {len(scores)}/{total} lượt trước đó (resume).")

    gt_map: dict = {}
    if data_file and os.path.exists(data_file):
        for d in json.load(open(data_file, encoding="utf-8")):
            if d.get("relevant_chunk_ids"):
                gt_map[d["question"]] = d["relevant_chunk_ids"]

    for d in data:
        relevant_ids = gt_map.get(d["question"]) if "context_recall" in metrics else None
        sample_kwargs = {
            "user_input": d["question"],
            "retrieved_contexts": d["contexts"],
            "response": d["answer"],
        }
        if relevant_ids:
            sample_kwargs["reference_contexts"] = relevant_ids
        sample = SingleTurnSample(**sample_kwargs)
        for mname, metric in metrics.items():
            if mname == "context_recall" and not relevant_ids:
                continue  # skip nếu không có GT
            if (d["question"], mname) in done:
                continue
            try:
                val = asyncio.run(metric.single_turn_ascore(sample))
            except Exception as e:
                es = str(e)
                low = es.lower()
                if "rate_limit" in low or "429" in es or "tokens per day" in low or "quota" in low:
                    print(f"\n  [HẾT TOKEN GROQ] đã chấm {len(scores)}/{total}.")
                    print(f"  -> ĐỔI sang API key Groq TÀI KHOẢN KHÁC trong .env rồi CHẠY LẠI để tiếp (resume).")
                    print(f"  (lỗi: {es[:110]})")
                    _summary(scores, list(metrics.keys()), scores_file)
                    return
                raise
            scores.append({"question": d["question"], "metric": mname, "score": float(val)})
            json.dump(scores, open(scores_file, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            print(f"  [{len(scores)}/{total}] {mname:18} = {val:.3f} | {d['question'][:30]}...", flush=True)
            time.sleep(2)

    print("\n=== HOÀN TẤT — đã chấm đủ tất cả lượt ===")
    _summary(scores, list(metrics.keys()), scores_file)


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "h1"
    if target not in ("h1", "h2"):
        raise SystemExit(f"usage: python eval_ragas.py [h1|h2] (got: {target!r})")
    data_file = f"data/eval_data_{target}.json"
    scores_file = f"data/eval_scores_{target}.json"
    print(f"--- Đánh giá {target.upper()} ---")
    print(f"--- Phần 1: tạo data -> {data_file} ---")
    data = produce_data_for(data_file)
    print(f"--- Phần 2: chấm điểm ({len(data)} câu, Groq judge) -> {scores_file} ---")
    score(data, data_file=data_file, scores_file=scores_file)


if __name__ == "__main__":
    main()
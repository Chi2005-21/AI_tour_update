"""RAG Hướng 1 (MVP) — hybrid retrieve (dense + BM25 + RRF) + Gemini trả lời.

Extract từ src/evaluation/eval_ragas.py để tái sửng cho eval framework
mà không phụ thuộc vào script eval.
"""
from __future__ import annotations

import os
import sys
import time
from typing import Any

sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv()

from google import genai
from google.genai import types
from qdrant_client import QdrantClient
from qdrant_client import models as qm
from fastembed import SparseTextEmbedding

QDRANT_PATH = "./qdrant_data"
COLLECTION = "tourism"
EMBED_MODEL = "gemini-embedding-001"
ANSWER_MODEL = "gemini-2.5-flash-lite"
TOP_K = 6

TYPE_LABEL = {"description": "mô tả", "storytelling": "câu chuyện", "fun_fact": "điều thú vị",
              "practical": "thông tin thực dụng", "image": "mô tả ảnh"}

PROMPT = """Bạn là hướng dẫn viên du lịch ảo. Trả lời câu hỏi của khách DỰA TRÊN phần NGỮ CẢNH bên dưới.

QUY TẮC BẮT BUỘC:
- CHỈ dùng thông tin trong NGỮ CẢNH. TUYỆT ĐỐI KHÔNG bịa, không thêm kiến thức ngoài.
- Nếu NGỮ CẢNH không đủ -> nói rõ: "Tôi chưa có thông tin chắc chắn về điều này."
- Trả lời bằng ĐÚNG ngôn ngữ của câu hỏi.
- Giọng thân thiện như hướng dẫn viên, bám sát dữ liệu.

NGỮ CẢNH:
{context}

CÂU HỎI: {question}

TRẢ LỜI:"""


def _to_sparse(sv):
    return qm.SparseVector(indices=sv.indices.tolist(), values=sv.values.tolist())


def _call_with_retry(fn, what: str, max_retries: int = 8):
    """Gọi API, retry: 429 -> đợi 65s; lỗi mạng -> đợi 10s."""
    for _ in range(max_retries):
        try:
            return fn()
        except Exception as e:
            es = str(e).lower()
            if "429" in es or "resource_exhausted" in es or "quota" in es:
                time.sleep(65)
            elif any(k in es for k in ("timeout", "connection", "unavailable", "503", "deadline")):
                time.sleep(10)
            else:
                raise
    raise RuntimeError(f"{what} lỗi dai dẳng")


def _clients() -> tuple[Any, Any, Any]:
    """Lazy init — chỉ tạo khi gọi lần đầu."""
    g = genai.Client(api_key=os.environ.get("GEMINI_API_KEY", ""))
    q = QdrantClient(path=QDRANT_PATH)
    bm25 = SparseTextEmbedding("Qdrant/bm25")
    return g, q, bm25


def answer(question: str) -> dict:
    """Hybrid retrieve + Gemini trả lời grounded. Trả về {answer, contexts, sources}."""
    g, q, bm25 = _clients()
    dq = _call_with_retry(
        lambda: g.models.embed_content(
            model=EMBED_MODEL, contents=[question],
            config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
        ).embeddings[0].values,
        "embed")
    sq = list(bm25.embed([question]))[0]
    hits = q.query_points(
        collection_name=COLLECTION,
        prefetch=[qm.Prefetch(query=dq, using="dense", limit=20),
                  qm.Prefetch(query=_to_sparse(sq), using="bm25", limit=20)],
        query=qm.FusionQuery(fusion=qm.Fusion.RRF), limit=TOP_K,
    ).points
    contexts = [h.payload.get("text", "") for h in hits]
    sources = [{"id": h.payload.get("id"), "name": h.payload.get("name"),
                "type": h.payload.get("type"), "location": h.payload.get("location")}
               for h in hits]
    ctx_str = "\n\n".join(
        f"[Nguồn: {h.payload.get('name')} | {TYPE_LABEL.get(h.payload.get('type'), h.payload.get('type'))}]\n{h.payload.get('text')}"
        for h in hits)
    ans = _call_with_retry(
        lambda: (g.models.generate_content(
            model=ANSWER_MODEL,
            contents=[PROMPT.format(context=ctx_str, question=question)]).text or "").strip(),
        "generate")
    return {"answer": ans, "contexts": contexts, "sources": sources}

"""
demo_type_filter.py — Chứng minh giá trị của metadata filter (type=practical).

So sánh retrieve cho câu THỰC DỤNG (giờ/vé):
  - KHÔNG lọc (Hướng 1 hiện tại)  -> top-k lẫn nhiều type -> precision thấp
  - CÓ lọc type=practical (Hướng 2) -> chỉ chunk practical -> precision cao

Quota: chỉ vài Gemini query-embed (nhỏ). Không dùng Groq.
Chạy: python scripts/demo_type_filter.py
"""

import os
import sys
import time

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
K = 6

g = genai.Client(api_key=os.environ.get("GEMINI_API_KEY", ""))
q = QdrantClient(path=QDRANT_PATH)
bm25 = SparseTextEmbedding("Qdrant/bm25")


def to_sparse(sv):
    return qm.SparseVector(indices=sv.indices.tolist(), values=sv.values.tolist())


def retrieve(question, type_filter=None, k=K):
    dq = g.models.embed_content(
        model=EMBED_MODEL, contents=[question],
        config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
    ).embeddings[0].values
    sq = list(bm25.embed([question]))[0]
    flt = None
    if type_filter:
        flt = qm.Filter(must=[qm.FieldCondition(key="type", match=qm.MatchValue(value=type_filter))])
    return q.query_points(
        collection_name=COLLECTION,
        prefetch=[
            qm.Prefetch(query=dq, using="dense", limit=20, filter=flt),
            qm.Prefetch(query=to_sparse(sq), using="bm25", limit=20, filter=flt),
        ],
        query=qm.FusionQuery(fusion=qm.Fusion.RRF), limit=k,
    ).points


def show(question):
    print("=" * 70)
    print("CÂU HỎI:", question)
    for label, tf in [("KHÔNG lọc (Hướng 1)", None), ("CÓ lọc type=practical (Hướng 2)", "practical")]:
        hits = retrieve(question, type_filter=tf)
        types_list = [h.payload.get("type") for h in hits]
        n_practical = sum(1 for t in types_list if t == "practical")
        print(f"\n  >>> {label}")
        for h in hits:
            p = h.payload
            mark = " <-- practical" if p.get("type") == "practical" else ""
            print(f"      [{p.get('type'):12}] {p.get('location_id'):16}{mark}")
        print(f"      => chunk practical trong top-{K}: {n_practical}/{K}  "
              f"(tỉ lệ 'đúng loại' = {n_practical/K:.2f})")
        time.sleep(1)
    print()


if __name__ == "__main__":
    for ql in [
        "Bảo tàng Dân tộc học mở cửa lúc mấy giờ?",
        "Giá vé vào Bảo tàng Dân tộc học là bao nhiêu?",
    ]:
        show(ql)

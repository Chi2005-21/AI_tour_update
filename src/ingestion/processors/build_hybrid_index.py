"""
build_hybrid_index.py — Nâng collection 'tourism' lên HYBRID (dense + sparse BM25).

- TÁI DÙNG dense vector đã có trong Qdrant (đọc lại bằng scroll) -> KHÔNG gọi lại
  Gemini -> KHÔNG tốn quota.
- Thêm sparse BM25 (FastEmbed, chạy LOCAL, free) -> khớp tên riêng tiếng Việt.
- Tạo lại collection với named vectors: 'dense' + 'bm25', upsert lại.
- Test 1 query hybrid (dense + sparse, gộp bằng RRF).

Chạy: python scripts/build_hybrid_index.py
"""

import os
import sys

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
DIM = 3072
EMBED_MODEL = "gemini-embedding-001"


def to_sparse(sv):
    return qm.SparseVector(indices=sv.indices.tolist(), values=sv.values.tolist())


def main():
    q = QdrantClient(path=QDRANT_PATH)
    if not q.collection_exists(COLLECTION):
        print("Chưa có collection 'tourism'. Chạy build_index.py trước.")
        return

    # 1. Đọc toàn bộ điểm hiện có (dense vector + payload) — KHÔNG gọi Gemini
    print("Đọc dense vectors đã có từ Qdrant (không gọi Gemini)...")
    points = []
    offset = None
    while True:
        recs, offset = q.scroll(COLLECTION, limit=500, offset=offset,
                                with_payload=True, with_vectors=True)
        points.extend(recs)
        if offset is None:
            break
    print(f"  Lấy được {len(points)} điểm.")
    if not points:
        print("  Collection rỗng. Dừng.")
        return

    # 2. Tính sparse BM25 cục bộ cho text của từng chunk
    print("Tính sparse BM25 (local, free)...")
    bm25 = SparseTextEmbedding("Qdrant/bm25")
    texts = [p.payload["text"] for p in points]
    sparse_vecs = list(bm25.embed(texts))

    # 3. Tạo lại collection với named vectors: dense + bm25
    print("Tạo lại collection ở dạng hybrid...")
    q.recreate_collection(
        collection_name=COLLECTION,
        vectors_config={"dense": qm.VectorParams(size=DIM, distance=qm.Distance.COSINE)},
        sparse_vectors_config={"bm25": qm.SparseVectorParams()},
    )

    # 4. Upsert lại: dense (tái dùng) + bm25 (mới)
    new_points = []
    for p, sv in zip(points, sparse_vecs):
        dense = p.vector
        if isinstance(dense, dict):              # phòng trường hợp named
            dense = dense.get("dense") or next(iter(dense.values()))
        new_points.append(qm.PointStruct(
            id=p.id,
            vector={"dense": dense, "bm25": to_sparse(sv)},
            payload=p.payload,
        ))

    B = 100
    for i in range(0, len(new_points), B):
        q.upsert(collection_name=COLLECTION, points=new_points[i:i + B])
        print(f"  upsert {min(i + B, len(new_points))}/{len(new_points)}")

    print(f"=== Hybrid '{COLLECTION}' có {q.count(COLLECTION).count} điểm (dense + bm25) ===")

    # 5. Test query hybrid (chọn câu có TÊN RIÊNG để thấy keyword phát huy)
    g = genai.Client(api_key=os.environ.get("GEMINI_API_KEY", ""))
    ql = "Chùa Bút Tháp"
    dq = g.models.embed_content(
        model=EMBED_MODEL, contents=[ql],
        config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
    ).embeddings[0].values
    sq = list(bm25.embed([ql]))[0]

    res = q.query_points(
        collection_name=COLLECTION,
        prefetch=[
            qm.Prefetch(query=dq, using="dense", limit=10),
            qm.Prefetch(query=to_sparse(sq), using="bm25", limit=10),
        ],
        query=qm.FusionQuery(fusion=qm.Fusion.RRF),
        limit=3,
    ).points
    print(f'\nTest HYBRID: "{ql}"')
    for h in res:
        p = h.payload
        print(f"  [{h.score:.3f}] {p.get('location_id')} / {p.get('type')} : {p.get('text', '')[:55]}...")


if __name__ == "__main__":
    main()

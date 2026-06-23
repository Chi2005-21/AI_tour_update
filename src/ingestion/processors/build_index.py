"""
build_index.py — Embed chunks (gemini-embedding-001) -> Qdrant local.

- Đọc data/chunks.json
- Embed gemini-embedding-001 (task_type RETRIEVAL_DOCUMENT), theo batch
- Lưu Qdrant ./qdrant_data, collection 'tourism' (3072 chiều, cosine)
- ID điểm = uuid5(chunk id) -> ỔN ĐỊNH + RESUME (chạy lại bỏ qua chunk đã có,
  không trùng, không tốn quota lại)
- Hết quota -> dừng + báo; chạy lại để index tiếp
- Cuối: test 1 câu truy vấn

Chạy: python scripts/build_index.py
"""

import os
import sys
import json
import time
import uuid

sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv()

from google import genai
from google.genai import types
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

CHUNKS = "data/chunks.json"
QDRANT_PATH = "./qdrant_data"
COLLECTION = "tourism"
EMBED_MODEL = "gemini-embedding-001"
DIM = 3072
BATCH = 20
SLEEP_BETWEEN = 15   # giãn giữa batch để dưới giới hạn/phút
WAIT_ON_429 = 65     # gặp 429 -> đợi cửa sổ phút reset rồi thử lại CÙNG batch
MAX_429 = 6          # 429 dai dẳng sau ngần này lần đợi -> coi như hết quota NGÀY, dừng


def embed(client, texts, task):
    r = client.models.embed_content(
        model=EMBED_MODEL, contents=texts,
        config=types.EmbedContentConfig(task_type=task),
    )
    return [e.values for e in r.embeddings]


def pid_of(chunk_id):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_id))


def main():
    g = genai.Client(api_key=os.environ.get("GEMINI_API_KEY", ""))
    chunks = json.load(open(CHUNKS, encoding="utf-8"))
    q = QdrantClient(path=QDRANT_PATH)

    # tạo collection nếu chưa có; nếu có -> đọc danh sách điểm đã index (để resume)
    if not q.collection_exists(COLLECTION):
        q.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=DIM, distance=Distance.COSINE),
        )
        existing = set()
    else:
        existing = set()
        offset = None
        while True:
            recs, offset = q.scroll(COLLECTION, limit=1000, offset=offset,
                                    with_payload=False, with_vectors=False)
            existing.update(str(r.id) for r in recs)
            if offset is None:
                break

    todo = [c for c in chunks if pid_of(c["id"]) not in existing]
    print(f"Tổng {len(chunks)} chunk | đã index {len(existing)} | cần embed {len(todo)}")

    done = 0
    i = 0
    waits = 0
    while i < len(todo):
        batch = todo[i:i + BATCH]
        try:
            vecs = embed(g, [c["text"] for c in batch], "RETRIEVAL_DOCUMENT")
        except Exception as e:
            es = str(e)
            if "429" in es or "RESOURCE_EXHAUSTED" in es.upper() or "quota" in es.lower():
                waits += 1
                if waits > MAX_429:
                    print(f"  [Vẫn 429 sau {MAX_429} lần đợi -> có thể đã hết quota NGÀY. "
                          f"Dừng, đã index {done} lần này. Chạy lại sau (resume).]")
                    break
                print(f"  [giới hạn/phút -> đợi {WAIT_ON_429}s cho reset rồi thử lại batch này ({waits}/{MAX_429})]", flush=True)
                time.sleep(WAIT_ON_429)
                continue   # thử lại CÙNG batch, không bỏ chunk nào
            print(f"  [lỗi batch] {es[:140]}")
            raise
        pts = [PointStruct(id=pid_of(c["id"]), vector=v, payload=c)
               for c, v in zip(batch, vecs)]
        q.upsert(collection_name=COLLECTION, points=pts)
        done += len(batch)
        waits = 0   # thành công -> reset đếm chờ
        print(f"  indexed {done}/{len(todo)}  (tổng {len(existing) + done}/{len(chunks)})", flush=True)
        i += BATCH
        time.sleep(SLEEP_BETWEEN)

    total = q.count(COLLECTION).count
    print(f"\n=== Qdrant '{COLLECTION}' hiện có {total}/{len(chunks)} chunk ===")

    # test 1 câu truy vấn
    if total > 0:
        ql = "Vịnh Hạ Long có gì đặc biệt?"
        try:
            qv = embed(g, [ql], "RETRIEVAL_QUERY")[0]
            hits = q.query_points(collection_name=COLLECTION, query=qv, limit=3).points
            print(f'\nTest truy vấn: "{ql}"')
            for h in hits:
                p = h.payload
                print(f"  [{h.score:.3f}] {p.get('location_id')} / {p.get('type')} : {p.get('text','')[:60]}...")
        except Exception as e:
            print(f"  (bỏ test query: {str(e)[:80]})")


if __name__ == "__main__":
    main()

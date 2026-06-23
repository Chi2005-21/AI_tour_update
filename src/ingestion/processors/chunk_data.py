"""
Structural chunking THUẦN (KHÔNG gọi API) cho 30 địa điểm.

- Trường text đơn (summary/story/fun_fact) -> 1 chunk, gắn type.
- practical (dict) -> format thành 1 chunk text type=practical.
- image_caption -> 1 chunk type=image.
- full_text -> tách theo ĐOẠN, gom ~TARGET chữ; đoạn quá dài -> cắt theo CÂU cho vừa cỡ.
- Mỗi chunk: text + type + language + metadata + id ỔN ĐỊNH (deterministic).

Ghi chú: KHÔNG dùng embedding ở bước này. Muốn "semantic chunking" thật cho đoạn
dài thì làm ở bước embedding sau (cần API). Hiện đoạn dài cắt theo câu (structural).

Output: data/chunks.json (để xem trước khi embed).
Chạy: python scripts/chunk_data.py
"""

import os
import re
import sys
import glob
import json
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")

PROCESSED_DIR = "data/processed"
OUT = "data/chunks.json"
TARGET_WORDS = 250   # cỡ chunk mục tiêu (~"chữ"/token tiếng Việt)

SIMPLE_FIELDS = [
    ("summary", "description"),
    ("story", "storytelling"),
    ("fun_fact", "fun_fact"),
]


def wc(t):
    return len(t.split()) if isinstance(t, str) else 0


def split_sentences(text):
    parts = re.split(r"(?<=[.!?…])\s+", text.replace("\n", " "))
    return [p.strip() for p in parts if p.strip()]


def size_split(text):
    """Cắt đoạn dài thành các chunk ~TARGET chữ, theo ranh giới CÂU (không API)."""
    sents = split_sentences(text)
    chunks, cur, cur_w = [], [], 0
    for s in sents:
        w = wc(s)
        if cur and cur_w + w > TARGET_WORDS:
            chunks.append(" ".join(cur))
            cur, cur_w = [], 0
        cur.append(s)
        cur_w += w
    if cur:
        chunks.append(" ".join(cur))
    return chunks or [text]


def chunk_full_text(full_text):
    """Tách full_text theo đoạn -> gom ~TARGET chữ; đoạn dài -> cắt theo câu."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", full_text) if p.strip()]
    pieces = []
    for p in paras:
        if wc(p) > TARGET_WORDS:
            pieces.extend(size_split(p))
        else:
            pieces.append(p)
    chunks, cur, cur_w = [], [], 0
    for p in pieces:
        w = wc(p)
        if cur and cur_w + w > TARGET_WORDS:
            chunks.append("\n\n".join(cur))
            cur, cur_w = [], 0
        cur.append(p)
        cur_w += w
    if cur:
        chunks.append("\n\n".join(cur))
    return chunks


def format_practical(pr):
    label = {"opening_hours": "Giờ mở cửa", "ticket_price": "Giá vé", "phone": "SĐT",
             "website": "Website", "address": "Địa chỉ", "note": "Ghi chú"}
    parts = [f"{lab}: {pr.get(k)}" for k, lab in label.items()
             if isinstance(pr.get(k), str) and pr.get(k)]
    return ". ".join(parts) if parts else None


def add_chunk(out, cid, text, ctype, lang, meta, extra=None):
    if not isinstance(text, str) or not text.strip():
        return
    chunk = {"id": cid, "text": text, "type": ctype, "language": lang, **meta}
    if extra:
        chunk.update(extra)
    out.append(chunk)


def main():
    files = sorted(glob.glob(f"{PROCESSED_DIR}/*.json"))
    all_chunks = []

    for path in files:
        d = json.load(open(path, encoding="utf-8"))
        loc_id = d.get("id")
        meta = {
            "location_id": loc_id,
            "name": d.get("name"),
            "source": d.get("source"),
            "last_updated": d.get("last_updated"),
            "coordinates": d.get("coordinates"),
        }

        for lang in ("vi", "en"):
            for field, ctype in SIMPLE_FIELDS:
                add_chunk(all_chunks, f"{loc_id}_{field}_{lang}",
                          d.get(f"{field}_{lang}"), ctype, lang, meta)
            ft = d.get(f"full_text_{lang}")
            if isinstance(ft, str) and ft.strip():
                for i, ch in enumerate(chunk_full_text(ft)):
                    add_chunk(all_chunks, f"{loc_id}_fulltext_{lang}_{i}",
                              ch, "description", lang, meta)

        add_chunk(all_chunks, f"{loc_id}_caption", d.get("image_caption"),
                  "image", "vi", meta)

        pr = d.get("practical") or {}
        add_chunk(all_chunks, f"{loc_id}_practical", format_practical(pr),
                  "practical", "vi", meta, extra={"source_url": pr.get("source_url")})

    json.dump(all_chunks, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    by_type = Counter(c["type"] for c in all_chunks)
    by_lang = Counter(c["language"] for c in all_chunks)
    lens = [wc(c["text"]) for c in all_chunks]
    print(f"=== Đã tạo {len(all_chunks)} chunk từ {len(files)} địa điểm (THUẦN structural, không API) ===")
    print("Theo type:", dict(by_type))
    print("Theo ngôn ngữ:", dict(by_lang))
    print(f"Độ dài chunk (chữ): min={min(lens)}  max={max(lens)}  trung bình={sum(lens)//len(lens)}")
    print(f"Số chunk > {TARGET_WORDS} chữ: {sum(1 for l in lens if l > TARGET_WORDS)}")
    print(f"Đã lưu: {OUT}")


if __name__ == "__main__":
    main()

"""
build_inner_tour.py — Trích "lộ trình tham quan TRONG 1 địa điểm" (inner_tour) từ full_text
bằng Gemini, theo Hướng C (bán tự động: máy trích -> người review).

Mỗi hạng mục: {order, name, desc, minutes}
  - desc: rút TỪ văn bản (grounded, không bịa)
  - minutes: thời gian tham quan ƯỚC LƯỢNG (gợi ý, không phải dữ liệu chính thức)

Chạy:
    python -m src.ingestion.processors.build_inner_tour --id van_mieu   # test 1 điểm, chỉ in
    python -m src.ingestion.processors.build_inner_tour --all           # chạy + lưu vào JSON
"""

import os
import sys
import time
import json
import glob

sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv()

from google import genai

MODEL = "gemini-2.5-flash-lite"
PROCESSED_DIR = "data/processed"
_g = genai.Client(api_key=os.environ.get("GEMINI_API_KEY", ""))


def _parse_json(text):
    t = (text or "").strip()
    if t.startswith("```"):
        t = t.split("```", 2)[1]
        if t.startswith("json"):
            t = t[4:]
    i, j = t.find("{"), t.rfind("}")
    if i == -1 or j == -1:
        return None
    try:
        return json.loads(t[i:j + 1])
    except Exception:
        return None


PROMPT = """Bạn là hướng dẫn viên du lịch. Dưới đây là mô tả về danh thắng "{name}".

NHIỆM VỤ: Trích DANH SÁCH các HẠNG MỤC / CÔNG TRÌNH tham quan BÊN TRONG địa điểm này, sắp theo THỨ TỰ THAM QUAN THỰC TẾ của một du khách.

QUY TẮC:
- CHỈ lấy các hạng mục ĐƯỢC NHẮC trong văn bản. KHÔNG bịa hạng mục không có.
- KHÔNG đưa tên TỔNG THỂ của cả khu (trùng / gần trùng tên "{name}") làm hạng mục — chỉ lấy các CÔNG TRÌNH / KHU CỤ THỂ bên trong (cổng, lầu, gác, điện, bia, giếng, nhà, hồ, vườn...).
- THỨ TỰ THAM QUAN THỰC TẾ: khu nằm NGOÀI / TRƯỚC cổng chính mà khách đi qua trước (vd hồ, vườn ở phía ngoài) đặt TRƯỚC; sau đó theo TRỤC CHÍNH từ cổng ngoài → các sân / cổng giữa → công trình thờ chính ở trong cùng.
- GỘP các hạng mục nằm CHUNG một sân / khu thành 1 mục (vd "Giếng Thiên Quang và Bia Tiến Sĩ" cùng một sân).
- "desc": 1-2 câu rút gọn TỪ văn bản (không thêm kiến thức ngoài).
- "minutes": thời gian tham quan ước lượng hợp lý (số nguyên phút).
- Nếu văn bản KHÔNG nêu hạng mục cụ thể nào -> trả "inner_tour": [].

VĂN BẢN:
{full_text}

Trả về DUY NHẤT JSON (không markdown):
{{"inner_tour":[{{"order":1,"name":"<tên hạng mục>","desc":"<mô tả ngắn từ văn bản>","minutes":<số phút>}}]}}"""


def _llm(contents, retries=4):
    """generate_content có retry/backoff khi 429/503 (free-tier giới hạn theo phút)."""
    for i in range(retries):
        try:
            return _g.models.generate_content(model=MODEL, contents=contents)
        except Exception as e:
            msg = str(e)
            if ("429" in msg or "RESOURCE_EXHAUSTED" in msg or "503" in msg) and i < retries - 1:
                wait = 15 * (i + 1)
                print(f"   [quota] chờ {wait}s rồi thử lại ({i+1}/{retries-1})...")
                time.sleep(wait)
                continue
            raise


def extract_inner_tour(d):
    name = d.get("name", d.get("id"))
    # Lấy nhiều văn bản hơn (18k ký tự) — nhiều điểm có full_text dài, hạng mục
    # tham quan nằm SAU phần lịch sử dài ở đầu (vd Hoa Lư ~27k ký tự).
    ft = (d.get("full_text_vi") or d.get("summary_vi") or "")[:18000]
    if not ft.strip():
        return []
    prompt = PROMPT.format(name=name, full_text=ft)
    resp = _llm([prompt])
    r = _parse_json(resp.text) or {}
    tour = r.get("inner_tour", [])
    # chuẩn hoá + giữ thứ tự
    out = []
    for i, s in enumerate(tour, 1):
        if not s.get("name"):
            continue
        out.append({
            "order": i,
            "name": s.get("name"),
            "desc": s.get("desc", ""),
            "minutes": int(s.get("minutes") or 0) or None,
        })
    return out


def main():
    args = sys.argv[1:]
    save = "--all" in args or "--id" in args   # cả --id cũng lưu (1 điểm)
    preview_only = "--preview" in args          # chỉ in, không lưu
    force = "--force" in args                   # chạy lại cả điểm đã có
    target_id = None
    if "--id" in args:
        target_id = args[args.index("--id") + 1]

    paths = sorted(glob.glob(f"{PROCESSED_DIR}/*.json"))
    if target_id:
        paths = [p for p in paths if os.path.splitext(os.path.basename(p))[0] == target_id]

    done = skipped = 0
    for idx, path in enumerate(paths):
        d = json.load(open(path, encoding="utf-8"))
        print("=" * 60)
        print(f"[{idx+1}/{len(paths)}] ĐỊA ĐIỂM:", d.get("name"), f"({d.get('id')})")

        # Resume: đã có inner_tour rồi -> bỏ qua (trừ khi --force)
        if d.get("inner_tour") and not force:
            print("  (đã có inner_tour -> bỏ qua, dùng --force để chạy lại)")
            skipped += 1
            continue

        tour = extract_inner_tour(d)
        if not tour:
            print("  (không trích được hạng mục từ văn bản)")
            continue
        total = sum(s["minutes"] or 0 for s in tour)
        for s in tour:
            mins = f" · ~{s['minutes']} phút" if s["minutes"] else ""
            print(f"  {s['order']}. {s['name']}{mins}")
            print(f"     {s['desc']}")
        print(f"  → Tổng thời gian tham quan ước lượng: ~{total} phút")
        if save:
            d["inner_tour"] = tour
            json.dump(d, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            print("  ✅ Đã lưu inner_tour vào", path)


if __name__ == "__main__":
    main()

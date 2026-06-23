"""
Sinh image_caption cho 30 ảnh địa điểm bằng Gemini 2.5 Flash Vision (miễn phí).

Nguyên tắc chống đọc sai:
  - ĐƯA SẴN tên địa điểm cho model -> không phải đoán danh tính -> hết nhận nhầm.
  - ÉP "chỉ tả cái NHÌN THẤY trong ảnh", không suy diễn/không thêm kiến thức ngoài -> không bịa.
  - Model tự chấm độ rõ -> đánh dấu needs_review cho ảnh mờ/không đặc trưng.

CACHE SKIP: ảnh nào đã có image_caption rồi -> bỏ qua (trừ --force).
=> Thay vài ảnh rồi chạy lại chỉ tốn quota cho ảnh mới.

Yêu cầu: pip install google-genai python-dotenv ; GEMINI_API_KEY trong .env

Cách chạy:
    python scripts/generate_captions.py            # chỉ ảnh chưa có caption
    python scripts/generate_captions.py --force     # làm lại tất cả
"""

import sys
import os
import glob
import json
import time

sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv()

from google import genai
from google.genai import types

PROCESSED_DIR = "data/processed"
MODEL = "gemini-2.5-flash-lite"   # rẻ + quota free cao hơn flash (RPM ~30), đủ tốt để tả ảnh

MEDIA_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}

PROMPT_TMPL = """Đây là ảnh của địa điểm du lịch: "{name}" (miền Bắc Việt Nam).
Hãy mô tả ngắn gọn những gì NHÌN THẤY trong ảnh, để dùng cho việc NHẬN DIỆN HÌNH ẢNH.

QUY TẮC BẮT BUỘC:
- CHỈ tả những gì thực sự xuất hiện trong ảnh: kiến trúc, vật thể, màu sắc, bố cục, khung cảnh, góc chụp.
- TUYỆT ĐỐI KHÔNG thêm thông tin lịch sử / kiến thức bên ngoài. KHÔNG suy diễn cái không thấy.
- Nếu ảnh mờ, chụp xa, hoặc không thấy đặc trưng nào để nhận diện -> nói rõ điều đó.

Trả về DUY NHẤT một JSON (không kèm giải thích, không markdown):
{{
  "image_caption": "<1-3 câu tiếng Việt tả những gì thấy trong ảnh>",
  "image_clarity": "<'ro' nếu thấy rõ đặc trưng | 'mo_xa' nếu mờ/xa | 'khong_dac_trung' nếu không có đặc trưng nhận diện>",
  "needs_review": <true nếu ảnh khó dùng để nhận diện, false nếu ổn>
}}"""


def parse_json(text: str) -> dict | None:
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


class QuotaExhausted(Exception):
    """Hết quota/credit -> retry vô ích -> dừng cả script."""


def caption_image(client, name: str, img_path: str, max_retries: int = 3) -> dict | None:
    ext = os.path.splitext(img_path)[1].lower()
    mime = MEDIA_TYPES.get(ext)
    if not mime:
        print(f"    [SKIP] đuôi ảnh lạ: {ext}")
        return None
    with open(img_path, "rb") as f:
        img_bytes = f.read()
    part = types.Part.from_bytes(data=img_bytes, mime_type=mime)
    prompt = PROMPT_TMPL.format(name=name)

    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.generate_content(model=MODEL, contents=[part, prompt])
            return parse_json(response.text)
        except Exception as e:
            es = str(e)
            low = es.lower()
            transient = "unavailable" in low or "503" in es or "timeout" in low or "connection" in low
            quota = ("resource_exhausted" in low or "429" in es or "quota" in low
                     or "credit" in low or "insufficient" in low or "billing" in low)

            if transient:   # mạng/quá tải tạm thời -> đáng thử lại
                if attempt < max_retries:
                    print(f"    (tạm thời, đợi 8s thử lại {attempt}/{max_retries - 1})", flush=True)
                    time.sleep(8)
                    continue
                print(f"    [BỎ sau {max_retries} lần] {es[:80]}")
                return None

            if quota:   # hết quota/credit -> thử 1 lần phòng giới hạn/phút thoáng qua, rồi DỪNG HẲN
                if attempt == 1:
                    print("    (giới hạn, đợi 15s thử lại 1 lần)", flush=True)
                    time.sleep(15)
                    continue
                raise QuotaExhausted(es[:160])

            print(f"    [ERROR] {es[:100]}")   # lỗi khác -> bỏ ảnh này, không retry
            return None
    return None


def main():
    force = "--force" in sys.argv

    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        print("[ERROR] Chưa có GEMINI_API_KEY trong .env")
        return
    client = genai.Client(api_key=key)

    files = sorted(f for f in os.listdir(PROCESSED_DIR) if f.endswith(".json"))
    done, skipped, review = 0, 0, []

    print(f"=== Sinh caption bằng {MODEL} cho {len(files)} địa điểm ===\n")

    for filename in files:
        path = os.path.join(PROCESSED_DIR, filename)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        loc_id = data.get("id")
        name = data.get("name", loc_id)
        img_path = (data.get("image_path") or "").replace("\\", "/")  # chuẩn hóa path

        if not force and data.get("image_caption"):
            print(f"  [{loc_id}] skip (đã có caption)")
            skipped += 1
            continue

        if not img_path or not os.path.exists(img_path):
            # fallback: tìm file ảnh theo id (xử lý lệch đuôi .jpg/.png)
            matches = glob.glob(f"data/images/{loc_id}.*")
            if matches:
                img_path = matches[0].replace("\\", "/")
                data["image_path"] = img_path   # sửa lại path đúng vào JSON
            else:
                print(f"  [{loc_id}] KHÔNG tìm thấy file ảnh -> bỏ qua")
                continue

        print(f"  [{loc_id}]", end=" ")
        try:
            result = caption_image(client, name, img_path)
        except QuotaExhausted as e:
            print("HẾT QUOTA")
            print(f"\n=== DỪNG: hết quota/credit ({e}) ===")
            print(f"Đã caption {done} ảnh mới ở lần chạy này. Chạy lại NGÀY MAI khi quota Gemini reset.")
            break
        if not result or not result.get("image_caption"):
            print("thất bại -> bỏ qua")
            continue

        data["image_caption"] = result["image_caption"]
        data["image_clarity"] = result.get("image_clarity")
        data["image_needs_review"] = bool(result.get("needs_review"))
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        flag = "  ⚠️ NÊN XEM LẠI" if data["image_needs_review"] else ""
        print(f"OK [{data.get('image_clarity')}]{flag} | {result['image_caption'][:60]}...")
        if data["image_needs_review"]:
            review.append(loc_id)
        done += 1
        time.sleep(5)  # free tier gemini-2.0-flash 15 req/phút -> ~5s/ảnh là an toàn

    print(f"\n=== Xong: {done} caption mới, {skipped} skip ===")
    if review:
        print(f"⚠️ Ảnh NÊN XEM LẠI / thay (model thấy mờ hoặc không đặc trưng): {review}")
    else:
        print("Không có ảnh nào bị đánh dấu cần xem lại.")


if __name__ == "__main__":
    main()

"""
Sinh image_caption cho 30 ảnh địa điểm bằng OpenAI gpt-4o-mini Vision.

Nguyên tắc chống đọc sai:
  - ĐƯA SẴN tên địa điểm cho model -> không phải đoán danh tính -> hết nhận nhầm.
  - ÉP "chỉ tả cái NHÌN THẤY trong ảnh", không suy diễn/không thêm kiến thức ngoài -> không bịa.
  - Model tự chấm độ rõ -> đánh dấu needs_review cho ảnh mờ/không đặc trưng.

CACHE SKIP: ảnh nào đã có image_caption rồi -> bỏ qua (trừ --force).
=> Thay vài ảnh rồi chạy lại chỉ tốn tiền cho ảnh mới.

Yêu cầu: pip install openai python-dotenv ; OPENAI_API_KEY trong .env

Cách chạy:
    python scripts/generate_captions_openai.py            # chỉ ảnh chưa có caption
    python scripts/generate_captions_openai.py --force     # làm lại tất cả
"""

import sys
import os
import glob
import json
import time
import base64

sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI

PROCESSED_DIR = "data/processed"
MODEL = "gpt-4o-mini"  # Rẻ, chất lượng cao

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


def caption_image(client, name: str, img_path: str, max_retries: int = 5) -> dict | None:
    ext = os.path.splitext(img_path)[1].lower()
    mime = MEDIA_TYPES.get(ext)
    if not mime:
        print(f"    [SKIP] đuôi ảnh lạ: {ext}")
        return None

    with open(img_path, "rb") as f:
        img_bytes = f.read()

    img_base64 = base64.standard_b64encode(img_bytes).decode("utf-8")
    prompt = PROMPT_TMPL.format(name=name)

    for attempt in range(1, max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                max_tokens=200,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime};base64,{img_base64}",
                                },
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ],
                    }
                ],
            )
            return parse_json(response.choices[0].message.content)
        except Exception as e:
            es = str(e)
            if "rate_limit" in es.lower() or "429" in es:
                wait = 5
            elif "timeout" in es.lower() or "connection" in es.lower():
                wait = 3
            else:
                print(f"    [ERROR] {es[:100]}")
                return None
            if attempt < max_retries:
                print(f"    (lỗi, đợi {wait}s rồi thử lại {attempt}/{max_retries - 1})", flush=True)
                time.sleep(wait)
            else:
                print(f"    [BỎ sau {max_retries} lần thử] {es[:80]}")
                return None
    return None


def main():
    force = "--force" in sys.argv

    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        print("[ERROR] Chưa có OPENAI_API_KEY trong .env")
        return
    client = OpenAI(api_key=key)

    files = sorted(f for f in os.listdir(PROCESSED_DIR) if f.endswith(".json"))
    done, skipped, review = 0, 0, []

    print(f"=== Sinh caption bằng {MODEL} cho {len(files)} địa điểm ===\n")

    for filename in files:
        path = os.path.join(PROCESSED_DIR, filename)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        loc_id = data.get("id")
        name = data.get("name", loc_id)
        img_path = (data.get("image_path") or "").replace("\\", "/")

        if not force and data.get("image_caption"):
            print(f"  [{loc_id}] skip (da co caption)")
            skipped += 1
            continue

        if not img_path or not os.path.exists(img_path):
            matches = glob.glob(f"data/images/{loc_id}.*")
            if matches:
                img_path = matches[0].replace("\\", "/")
                data["image_path"] = img_path
            else:
                print(f"  [{loc_id}] KHONG tim thay file anh -> bo qua")
                continue

        print(f"  [{loc_id}]", end=" ")
        result = caption_image(client, name, img_path)
        if not result or not result.get("image_caption"):
            print("that bai -> bo qua")
            continue

        data["image_caption"] = result["image_caption"]
        data["image_clarity"] = result.get("image_clarity")
        data["image_needs_review"] = bool(result.get("needs_review"))
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        flag = "  CANH BAO: CAN XEM LAI" if data["image_needs_review"] else ""
        print(f"OK [{data.get('image_clarity')}]{flag} | {result['image_caption'][:60]}...")
        if data["image_needs_review"]:
            review.append(loc_id)
        done += 1
        time.sleep(5)  # OpenAI rate limit: ~12 req/phút → need 5s/request

    print(f"\n=== Xong: {done} caption moi, {skipped} skip ===")
    if review:
        print(f"Canh bao: Anh CAN XEM LAI / thay (model thay mo hoac khong dac trung): {review}")
    else:
        print("Khong co anh nao bi danh dau can xem lai.")


if __name__ == "__main__":
    main()

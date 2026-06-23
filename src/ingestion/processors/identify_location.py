"""
PROTOTYPE NHẬN DIỆN (cách A): user gửi 1 ảnh -> Gemini đối chiếu 30 địa điểm
-> trả về địa điểm khớp HOẶC "không thuộc danh sách" (chống đoán bừa).

Caption 30 ảnh đóng vai "thực đơn ứng viên" để model biết có những địa điểm nào.

Cách chạy:
    python scripts/identify_location.py <đường_dẫn_ảnh>
    python scripts/identify_location.py data/images/vinh_ha_long.jpg   # test ảnh đã biết
    python scripts/identify_location.py anh_bat_ky.jpg                  # test ảnh lạ
"""

import sys
import os
import glob
import json

sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv()

from google import genai
from google.genai import types

PROCESSED_DIR = "data/processed"
MODEL = "gemini-2.5-flash-lite"
CONF_THRESHOLD = 0.55   # dưới ngưỡng này -> coi như KHÔNG nhận ra (dù model có đoán)

MEDIA_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}


def parse_json(text: str):
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


def load_candidates():
    cands = []
    for path in sorted(glob.glob(f"{PROCESSED_DIR}/*.json")):
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        cands.append({
            "id": d.get("id"),
            "name": d.get("name"),
            "caption": d.get("image_caption") or "",
        })
    return cands


def build_prompt(cands):
    menu = "\n".join(f'- id="{c["id"]}" | {c["name"]} | {c["caption"]}' for c in cands)
    return f"""Người dùng gửi 1 ảnh. Dưới đây là DANH SÁCH 30 địa điểm du lịch miền Bắc Việt Nam (kèm mô tả ảnh mẫu của từng nơi):

{menu}

NHIỆM VỤ: Nhìn ảnh người dùng gửi, xác định nó có phải MỘT trong 30 địa điểm trên không.

QUY TẮC BẮT BUỘC:
- Chỉ trả id khi bạn THỰC SỰ thấy đặc trưng khớp với địa điểm đó.
- Nếu ảnh KHÔNG thuộc 30 địa điểm trên (nơi khác, vật thể bất kỳ, ảnh không liên quan) -> matched_id = null. TUYỆT ĐỐI KHÔNG đoán bừa cho có.
- confidence là mức độ chắc chắn từ 0.0 đến 1.0.

Trả về DUY NHẤT một JSON (không markdown, không giải thích thêm):
{{"matched_id": "<id hoặc null>", "matched_name": "<tên hoặc null>", "confidence": <số 0.0-1.0>, "reason": "<1 câu: thấy gì trong ảnh + vì sao khớp/không khớp>"}}"""


def identify(img_path: str):
    ext = os.path.splitext(img_path)[1].lower()
    mime = MEDIA_TYPES.get(ext)
    if not mime:
        print(f"[LỖI] đuôi ảnh không hỗ trợ: {ext}")
        return
    if not os.path.exists(img_path):
        print(f"[LỖI] không tìm thấy ảnh: {img_path}")
        return

    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        print("[LỖI] chưa có GEMINI_API_KEY trong .env")
        return
    client = genai.Client(api_key=key)

    with open(img_path, "rb") as f:
        part = types.Part.from_bytes(data=f.read(), mime_type=mime)

    cands = load_candidates()
    prompt = build_prompt(cands)

    print(f"Đang nhận diện: {img_path} (đối chiếu {len(cands)} địa điểm)...\n")
    try:
        resp = client.models.generate_content(model=MODEL, contents=[part, prompt])
    except Exception as e:
        print(f"[LỖI gọi API] {str(e)[:150]}")
        return

    r = parse_json(resp.text)
    if not r:
        print("[LỖI] model trả về không phải JSON hợp lệ:")
        print(resp.text[:300])
        return

    mid = r.get("matched_id")
    conf = float(r.get("confidence") or 0)
    reason = r.get("reason", "")

    # Áp NGƯỠNG: model đoán có id nhưng tin cậy thấp -> vẫn coi là không nhận ra
    if mid and conf >= CONF_THRESHOLD:
        print(f"✅ NHẬN RA: {r.get('matched_name')}  (id={mid})")
        print(f"   Độ tin cậy: {conf:.0%}")
        print(f"   Lý do: {reason}")
    else:
        print("❓ KHÔNG NHẬN RA — ảnh này không thuộc 30 địa điểm đã biết.")
        if mid:
            print(f"   (model có đoán '{mid}' nhưng tin cậy {conf:.0%} < ngưỡng {CONF_THRESHOLD:.0%})")
        print(f"   Lý do: {reason}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Dùng: python scripts/identify_location.py <đường_dẫn_ảnh>")
        sys.exit(1)
    identify(sys.argv[1].replace("\\", "/"))

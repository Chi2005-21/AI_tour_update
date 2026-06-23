"""
Biên tập nội dung tự động: đọc Wikipedia thô → Gemini viết lại theo phong cách
hướng dẫn viên du lịch → lưu vào data/processed/

Kết quả mỗi địa điểm gồm:
  - story_vi   : 2-3 đoạn kể chuyện bằng tiếng Việt (giọng HDV thân thiện)
  - fun_fact_vi: 1 điều thú vị / "bí mật" ít người biết
  - story_en   : bản tiếng Anh ngắn gọn
  - fun_fact_en: bản tiếng Anh

Cách chạy:
    python scripts/rewrite_content.py --test          # thử 1 địa điểm (van_mieu)
    python scripts/rewrite_content.py --all           # chạy cả 30

Yêu cầu:
    pip install google-genai python-dotenv
    Đặt GEMINI_API_KEY trong file .env
"""

import sys
import os
import json
import argparse
import time

from google import genai
from dotenv import load_dotenv

load_dotenv()
sys.stdout.reconfigure(encoding="utf-8")

RAW_DIR       = "data/raw"
PROCESSED_DIR = "data/processed"

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
MODEL  = "gemini-2.5-flash"

PROMPT_TEMPLATE = """Bạn là một hướng dẫn viên du lịch người Việt Nam, am hiểu lịch sử và văn hóa, có giọng kể chuyện cuốn hút, thân thiện, phù hợp với khách du lịch mọi lứa tuổi.

Nhiệm vụ: Viết lại thông tin về địa điểm du lịch theo phong cách kể chuyện (storytelling), KHÔNG copy nguyên văn từ Wikipedia. Ngôn ngữ gần gũi, sinh động, có cảm xúc.

Địa điểm: {name}

Thông tin từ Wikipedia:
{summary}

Trả lời đúng định dạng JSON sau (không có text nào ngoài JSON):
{{
  "story_vi": "2-3 đoạn tiếng Việt, mỗi đoạn 3-5 câu, kể chuyện như HDV đang dẫn tour",
  "fun_fact_vi": "1 điều thú vị hoặc ít người biết về địa điểm này, 1-2 câu",
  "story_en": "2-3 paragraphs in English, same storytelling style",
  "fun_fact_en": "1 interesting or little-known fact, 1-2 sentences"
}}"""


def rewrite_one(data: dict) -> dict:
    prompt = PROMPT_TEMPLATE.format(
        name=data["name"],
        summary=data.get("summary_vi", "")[:800],
    )

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
    )

    raw = response.text.strip()

    # Bóc JSON ra khỏi markdown nếu Gemini bọc trong ```json ... ```
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

    return json.loads(raw)


def process_file(filepath: str):
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    loc_id   = data["id"]
    out_path = os.path.join(PROCESSED_DIR, f"{loc_id}.json")

    if os.path.exists(out_path):
        print(f"  [SKIP] {loc_id} — đã có file processed")
        return None

    print(f"  Đang viết lại: {data['name']} ...", end=" ", flush=True)
    rewritten = rewrite_one(data)

    output = {**data, **rewritten}

    os.makedirs(PROCESSED_DIR, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("OK")
    return rewritten


def run_test():
    test_file = os.path.join(RAW_DIR, "van_mieu.json")
    print("=== TEST: Viết lại Văn Miếu ===\n")
    result = process_file(test_file)
    if result:
        print("\n--- story_vi ---")
        print(result["story_vi"])
        print("\n--- fun_fact_vi ---")
        print(result["fun_fact_vi"])
        print("\nTest OK. Chạy --all để xử lý cả 30 địa điểm.")


def run_all():
    files = sorted(f for f in os.listdir(RAW_DIR) if f.endswith(".json"))
    print(f"=== Biên tập nội dung {len(files)} địa điểm ===\n")
    success, failed = 0, []

    for i, filename in enumerate(files, 1):
        filepath = os.path.join(RAW_DIR, filename)
        print(f"[{i}/{len(files)}]", end=" ")
        try:
            result = process_file(filepath)
            if result is not None:
                success += 1
        except Exception as e:
            loc_id = filename.replace(".json", "")
            print(f"  [ERROR] {loc_id}: {e}")
            failed.append(loc_id)
        time.sleep(1)  # tránh rate limit (15 req/phút)

    print(f"\nHoàn thành: {success}/{len(files)}")
    if failed:
        print(f"Thất bại: {failed}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="Thử 1 địa điểm")
    parser.add_argument("--all",  action="store_true", help="Xử lý cả 30 địa điểm")
    args = parser.parse_args()

    if args.test:
        run_test()
    elif args.all:
        run_all()
    else:
        print("Dùng: python scripts/rewrite_content.py --test | --all")

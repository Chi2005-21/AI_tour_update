"""
Script fetch dữ liệu từ Wikipedia cho 30 địa điểm Miền Bắc.
Chạy thử 1 địa điểm trước, sau đó chạy cả 30.

Cài đặt:
    pip install wikipedia-api

Cách chạy:
    python -m src.ingestion.collectors.wikipedia --test
    python -m src.ingestion.collectors.wikipedia --all
"""

import sys
import wikipediaapi
import json
import os
import time
import argparse
from datetime import date

sys.stdout.reconfigure(encoding="utf-8")

# --- Cấu hình ---
OUTPUT_DIR = "data/raw"
TODAY = str(date.today())

wiki_vi = wikipediaapi.Wikipedia(language="vi", user_agent="TourGuideBot/1.0")
wiki_en = wikipediaapi.Wikipedia(language="en", user_agent="TourGuideBot/1.0")

# --- Danh sách 30 địa điểm Miền Bắc ---
LOCATIONS = [
    # Hà Nội
    {"id": "van_mieu",          "vi": "Văn Miếu - Quốc Tử Giám",       "en": "Temple of Literature, Hanoi"},
    {"id": "ho_hoan_kiem",      "vi": "Hồ Hoàn Kiếm",                   "en": "Hoan Kiem Lake"},
    {"id": "den_ngoc_son",      "vi": "Đền Ngọc Sơn",                   "en": "Ngoc Son Temple"},
    {"id": "hoang_thanh",       "vi": "Hoàng thành Thăng Long",         "en": "Thang Long Imperial Citadel"},
    {"id": "lang_ho_chi_minh",  "vi": "Lăng Chủ tịch Hồ Chí Minh",    "en": "Ho Chi Minh Mausoleum"},
    {"id": "chua_mot_cot",      "vi": "Chùa Một Cột",                   "en": "One Pillar Pagoda"},
    {"id": "pho_co_ha_noi",     "vi": "Phố cổ Hà Nội",                  "en": "Hanoi Old Quarter"},
    {"id": "btdth",             "vi": "Bảo tàng Dân tộc học Việt Nam",  "en": "Vietnam Museum of Ethnology"},
    {"id": "btls",              "vi": "Bảo tàng Lịch sử Việt Nam",          "en": "National Museum of Vietnamese History"},
    {"id": "ho_tay",            "vi": "Hồ Tây",                         "en": "West Lake, Hanoi"},
    {"id": "den_quan_thanh",    "vi": "Đền Quán Thánh",                 "en": "Quan Thanh Temple"},
    {"id": "chua_tran_quoc",    "vi": "Chùa Trấn Quốc",                "en": "Tran Quoc Pagoda"},
    {"id": "nha_tho_lon",       "vi": "Nhà thờ Lớn Hà Nội",            "en": "St. Joseph's Cathedral, Hanoi"},
    # Ninh Bình
    {"id": "trang_an",          "vi": "Tràng An",                       "en": "Trang An"},
    {"id": "tam_coc",           "vi": "Tam Cốc - Bích Động",            "en": "Tam Coc – Bich Dong"},
    {"id": "co_do_hoa_lu",      "vi": "Cố đô Hoa Lư",                  "en": "Hoa Lu"},
    {"id": "nha_tho_phat_diem", "vi": "Nhà thờ đá Phát Diệm",          "en": "Phat Diem Cathedral"},
    # Quảng Ninh
    {"id": "vinh_ha_long",      "vi": "Vịnh Hạ Long",                   "en": "Ha Long Bay"},
    {"id": "dao_cat_ba",        "vi": "Đảo Cát Bà",                    "en": "Cat Ba Island"},
    {"id": "chua_yen_tu",       "vi": "Chùa Yên Tử",                   "en": "Yen Tu"},
    # Lào Cai
    {"id": "sa_pa",             "vi": "Sa Pa",                          "en": "Sa Pa"},
    {"id": "mu_cang_chai",      "vi": "Mù Cang Chải",                  "en": "Mu Cang Chai"},
    # Phú Thọ
    {"id": "den_hung",          "vi": "Đền Hùng",                       "en": "Hung Kings Temple"},
    {"id": "vqg_xuan_son",      "vi": "Vườn quốc gia Xuân Sơn",        "en": "Xuan Son National Park"},
    # Hà Giang
    {"id": "dong_van",          "vi": "Cao nguyên đá Đồng Văn",        "en": "Dong Van Karst Plateau"},
    {"id": "ma_pi_leng",        "vi": "Đèo Mã Pí Lèng",               "en": "Ma Pi Leng Pass"},
    # Điện Biên
    {"id": "dien_bien_phu",     "vi": "Chiến dịch Điện Biên Phủ",      "en": "Battle of Dien Bien Phu"},
    # Bắc Ninh
    {"id": "chua_but_thap",     "vi": "Chùa Bút Tháp",                 "en": "But Thap Pagoda"},
    {"id": "tranh_dong_ho",     "vi": "Tranh dân gian Đông Hồ",        "en": "Dong Ho painting"},
    # Hải Phòng
    {"id": "dao_bach_long_vi",  "vi": "Đảo Bạch Long Vĩ",             "en": "Bach Long Vi Island"},
]


def fetch_location(loc: dict) -> dict | None:
    page_vi = wiki_vi.page(loc["vi"])
    page_en = wiki_en.page(loc["en"])

    if not page_vi.exists():
        print(f"  [WARN] Không tìm thấy trang tiếng Việt: {loc['vi']}")
        return None

    return {
        "id":           loc["id"],
        "name":         loc["vi"],
        "type":         "location",
        "language":     "vi",
        "summary_vi":   page_vi.summary,
        "full_text_vi": page_vi.text,
        "summary_en":   page_en.summary if page_en.exists() else "",
        "full_text_en": page_en.text    if page_en.exists() else "",
        "url_vi":       page_vi.fullurl,
        "url_en":       page_en.fullurl if page_en.exists() else "",
        "source":       "Wikipedia CC BY-SA",
        "last_updated": TODAY,
        # Điền tay sau khi đọc nội dung
        "coordinates":  [],
        "related_to":   [],
        "chunk_index":  0,
    }


def save(data: dict, location_id: str):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, f"{location_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  Saved: {path}")


def run_test():
    print("=== TEST: Fetch Văn Miếu ===")
    loc = LOCATIONS[0]
    data = fetch_location(loc)
    if data:
        save(data, loc["id"])
        print(f"\nSummary (vi):\n{data['summary_vi'][:300]}...")
        print(f"\nSummary (en):\n{data['summary_en'][:300]}...")
        print("\nTest OK. Chạy --all để fetch cả 30 địa điểm.")


def run_all():
    print(f"=== Fetch cả {len(LOCATIONS)} địa điểm ===\n")
    success, failed = 0, []

    for i, loc in enumerate(LOCATIONS, 1):
        print(f"[{i}/{len(LOCATIONS)}] {loc['vi']}")
        try:
            data = fetch_location(loc)
            if data:
                save(data, loc["id"])
                success += 1
            else:
                failed.append(loc["id"])
        except Exception as e:
            print(f"  [ERROR] {e}")
            failed.append(loc["id"])
        time.sleep(0.5)  # tránh spam request

    print(f"\nHoàn thành: {success}/{len(LOCATIONS)}")
    if failed:
        print(f"Thất bại: {failed}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="Fetch thử 1 địa điểm")
    parser.add_argument("--all",  action="store_true", help="Fetch cả 30 địa điểm")
    args = parser.parse_args()

    if args.test:
        run_test()
    elif args.all:
        run_all()
    else:
        print("Dùng: python -m src.ingestion.collectors.wikipedia --test | --all")

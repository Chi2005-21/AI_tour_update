"""
Fetch ảnh cho 7 địa điểm còn thiếu bằng cách tìm trên Wikimedia Commons.

Cách chạy:
    python -m src.ingestion.collectors.images_fallback
"""

import sys
import os
import json
import requests
import time

sys.stdout.reconfigure(encoding="utf-8")

PROCESSED_DIR = "data/processed"
IMAGE_DIR     = "data/images"
HEADERS = {
    "User-Agent": "TourGuideBot/1.0 (educational project; khiemxhbn@gmail.com)",
    "Accept":     "image/webp,image/apng,image/*,*/*;q=0.8",
    "Referer":    "https://commons.wikimedia.org/",
}

# Từ khoá tìm kiếm cho từng địa điểm
MISSING = {
    "chua_but_thap":    "But Thap Pagoda Bac Ninh",
    "co_do_hoa_lu":     "Hoa Lu ancient capital Ninh Binh",
    "dao_bach_long_vi": "Bach Long Vi island Vietnam",
    "den_hung":         "Hung Kings Temple Phu Tho",
    "dong_van":         "Dong Van karst plateau Ha Giang",
    "pho_co_ha_noi":    "Hanoi Old Quarter 36 streets",
    "tam_coc":          "Tam Coc Ninh Binh Vietnam",
}


def search_commons(query: str, limit: int = 5) -> list:
    """
    Tìm ảnh trên Wikimedia Commons, trả về list { url, width, height }.
    Ưu tiên ảnh JPEG có kích thước lớn.
    """
    url = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action":       "query",
        "generator":    "search",
        "gsrnamespace": 6,       # File namespace
        "gsrsearch":    query,
        "gsrlimit":     limit,
        "prop":         "imageinfo",
        "iiprop":       "url|size|mime",
        "iiurlwidth":   1200,
        "format":       "json",
    }
    res  = requests.get(url, params=params, headers=HEADERS, timeout=30)
    data = res.json()

    results = []
    for page in data.get("query", {}).get("pages", {}).values():
        info = page.get("imageinfo", [{}])[0]
        mime = info.get("mime", "")
        if mime not in ("image/jpeg", "image/png", "image/webp"):
            continue
        thumb_url = info.get("thumburl") or info.get("url")
        if not thumb_url:
            continue
        results.append({
            "url":    thumb_url,
            "width":  info.get("thumbwidth") or info.get("width", 0),
            "height": info.get("thumbheight") or info.get("height", 0),
        })

    # Ưu tiên ảnh rộng nhất
    results.sort(key=lambda x: x["width"], reverse=True)
    return results


def download_image(url: str, filepath: str) -> bool:
    for attempt in range(3):
        try:
            res = requests.get(url, headers=HEADERS, timeout=60, stream=True)
            if res.status_code == 200:
                with open(filepath, "wb") as f:
                    for chunk in res.iter_content(64 * 1024):
                        f.write(chunk)
                return True
            print(f"  HTTP {res.status_code}", end=" ")
        except Exception as e:
            print(f"  [{attempt+1}/3] {e}", end=" ")
        time.sleep(2)
    return False


def main():
    os.makedirs(IMAGE_DIR, exist_ok=True)
    success, failed = 0, []

    print(f"=== Fetch ảnh Wikimedia Commons cho {len(MISSING)} địa điểm ===\n")

    for loc_id, query in MISSING.items():
        proc_path = os.path.join(PROCESSED_DIR, f"{loc_id}.json")
        if not os.path.exists(proc_path):
            print(f"  [WARN] Không tìm thấy file: {proc_path}")
            failed.append(loc_id)
            continue

        print(f"  [{loc_id}] Tìm: \"{query}\" ...", end=" ", flush=True)
        results = search_commons(query)

        if not results:
            print("không tìm được ảnh")
            failed.append(loc_id)
            continue

        img_info = results[0]
        url = img_info["url"]
        ext = url.split(".")[-1].lower().split("?")[0]
        if ext not in ("jpg", "jpeg", "png", "webp"):
            ext = "jpg"

        local_path = os.path.join(IMAGE_DIR, f"{loc_id}.{ext}")

        print(f"{img_info['width']}x{img_info['height']} ...", end=" ", flush=True)
        if not download_image(url, local_path):
            print("FAIL")
            failed.append(loc_id)
            continue

        print("OK")

        # Cập nhật processed JSON
        with open(proc_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["image_url"]    = url
        data["image_path"]   = local_path
        data["image_width"]  = img_info["width"]
        data["image_height"] = img_info["height"]
        with open(proc_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        success += 1
        time.sleep(0.5)

    print(f"\n=== Kết quả: {success}/{len(MISSING)} ===")
    if failed:
        print(f"Thất bại: {failed}")


if __name__ == "__main__":
    main()

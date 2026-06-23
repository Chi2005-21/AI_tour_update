"""
Fetch ảnh tham chiếu từ Wikimedia Commons cho 30 địa điểm.

Bước 1: Batch fetch image URL từ Wikipedia EN API (1 lần gọi)
Bước 2: Download ảnh về data/images/
Bước 3: Cập nhật data/processed/ với image_url, image_path

Cách chạy:
    python -m src.ingestion.collectors.images --test
    python -m src.ingestion.collectors.images --all
"""

import sys
import os
import json
import requests
import argparse
import time
import urllib.parse

sys.stdout.reconfigure(encoding="utf-8")

PROCESSED_DIR = "data/processed"
IMAGE_DIR     = "data/images"
HEADERS = {
    "User-Agent": "TourGuideBot/1.0 (educational project; khiemxhbn@gmail.com)",
    "Accept":     "image/webp,image/apng,image/*,*/*;q=0.8",
    "Referer":    "https://en.wikipedia.org/",
}


def en_title_from_url(url_en: str) -> str:
    if not url_en:
        return ""
    title = url_en.split("/wiki/")[-1]
    return urllib.parse.unquote(title).replace("_", " ")


def batch_fetch_image_urls(en_titles: list) -> dict:
    """
    Batch fetch ảnh đại diện từ Wikipedia EN — 1 API call.
    Trả về dict: { en_title -> { url, width, height } }
    """
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action":      "query",
        "titles":      "|".join(en_titles),
        "prop":        "pageimages",
        "piprop":      "thumbnail|original",
        "pithumbsize": 1200,
        "format":      "json",
    }
    res  = requests.get(url, params=params, headers=HEADERS, timeout=30)
    data = res.json()["query"]

    normalized_map = {}
    for entry in data.get("normalized", []):
        normalized_map[entry["to"]] = entry["from"]

    result = {}
    for page in data["pages"].values():
        canonical = page.get("title", "")
        img = page.get("thumbnail") or page.get("original")
        if img:
            original_title = normalized_map.get(canonical, canonical)
            info = {
                "url":    img["source"],
                "width":  img.get("width", 0),
                "height": img.get("height", 0),
            }
            result[original_title] = info
            result[canonical]      = info

    return result


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


def main(test_mode=False):
    # Đọc tất cả file processed
    files = {}
    for filename in sorted(os.listdir(PROCESSED_DIR)):
        if not filename.endswith(".json"):
            continue
        filepath = os.path.join(PROCESSED_DIR, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        loc_id = data["id"]

        if test_mode and loc_id != "van_mieu":
            continue

        files[loc_id] = {
            "filepath": filepath,
            "data":     data,
            "en_title": en_title_from_url(data.get("url_en", "")),
        }

    print(f"=== Fetch ảnh cho {len(files)} địa điểm ===\n")

    # Batch lấy image URLs — 1 API call
    en_titles = [v["en_title"] for v in files.values() if v["en_title"]]
    print(f"[Batch] Wikipedia pageimages — {len(en_titles)} địa điểm...")
    image_map = batch_fetch_image_urls(en_titles)
    print(f"  Tìm được ảnh: {len(set(v['url'] for v in image_map.values()))}/{len(en_titles)}\n")

    os.makedirs(IMAGE_DIR, exist_ok=True)
    success, failed = 0, []

    for loc_id, v in files.items():
        img_info = image_map.get(v["en_title"])

        if not img_info:
            print(f"  --  {loc_id}: không tìm được ảnh")
            failed.append(loc_id)
            continue

        # Xác định đuôi file
        url = img_info["url"]
        ext = url.split(".")[-1].lower().split("?")[0]
        if ext not in ("jpg", "jpeg", "png", "webp"):
            ext = "jpg"

        local_filename = f"{loc_id}.{ext}"
        local_path     = os.path.join(IMAGE_DIR, local_filename)

        if os.path.exists(local_path):
            print(f"  [SKIP] {loc_id} — ảnh đã có")
        else:
            print(f"  [{loc_id}] {img_info['width']}x{img_info['height']} ...", end=" ", flush=True)
            if not download_image(url, local_path):
                print("FAIL")
                failed.append(loc_id)
                continue
            print("OK")

        # Cập nhật processed JSON
        data = v["data"]
        data["image_url"]    = url
        data["image_path"]   = local_path
        data["image_width"]  = img_info["width"]
        data["image_height"] = img_info["height"]

        with open(v["filepath"], "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        success += 1
        time.sleep(0.3)

    print(f"\n=== Kết quả: {success}/{len(files)} ===")
    if failed:
        print(f"Không tìm được ảnh: {failed}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="Thử 1 địa điểm (van_mieu)")
    parser.add_argument("--all",  action="store_true", help="Tất cả 30 địa điểm")
    args = parser.parse_args()

    if args.test:
        main(test_mode=True)
    elif args.all:
        main(test_mode=False)
    else:
        print("Dùng: python -m src.ingestion.collectors.images --test | --all")

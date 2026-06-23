"""
Fetch thông tin thực dụng từ OpenStreetMap Overpass API.
Dùng coordinates đã có để tìm POI gần nhất và lấy:
  - opening_hours, phone, website, fee, address

Kết quả lưu vào data/processed/ (merge vào file đã có).
Trường nào OSM không có → để null (không bịa).

Cách chạy:
    python -m src.ingestion.collectors.osm
"""

import sys
import os
import json
import requests
import time

sys.stdout.reconfigure(encoding="utf-8")

PROCESSED_DIR = "data/processed"
HEADERS       = {"User-Agent": "TourGuideBot/1.0 (educational project; khiemxhbn@gmail.com)"}
OVERPASS_URL  = "https://overpass-api.de/api/interpreter"

# Tags ưu tiên tìm kiếm theo loại địa điểm
SEARCH_TAGS = [
    '"tourism"',
    '"historic"',
    '"leisure"',
    '"amenity"="place_of_worship"',
]


def build_overpass_query(locations: list) -> str:
    """
    Tạo 1 Overpass query cho nhiều địa điểm cùng lúc.
    Mỗi địa điểm tìm trong bán kính 300m.
    """
    parts = []
    for loc in locations:
        lat, lon = loc["coords"]
        for tag in SEARCH_TAGS:
            parts.append(f'node(around:300,{lat},{lon})[{tag}]["name"];')
            parts.append(f'way(around:300,{lat},{lon})[{tag}]["name"];')
            parts.append(f'relation(around:300,{lat},{lon})[{tag}]["name"];')

    query = f"""
[out:json][timeout:60];
(
{''.join(parts)}
);
out tags center;
"""
    return query


def extract_practical(tags: dict) -> dict:
    """Trích thông tin thực dụng từ OSM tags."""
    return {
        "opening_hours": tags.get("opening_hours"),
        "phone":         tags.get("phone") or tags.get("contact:phone"),
        "website":       tags.get("website") or tags.get("contact:website"),
        "fee":           tags.get("fee"),
        "charge":        tags.get("charge"),
        "address":       (
            tags.get("addr:full")
            or ", ".join(filter(None, [
                tags.get("addr:housenumber"),
                tags.get("addr:street"),
                tags.get("addr:suburb"),
                tags.get("addr:city"),
            ]))
            or None
        ),
        "osm_name":      tags.get("name"),
        "osm_name_en":   tags.get("name:en"),
    }


def best_match(elements: list, loc_name: str, lat: float, lon: float) -> dict | None:
    """
    Chọn element OSM gần nhất với tọa độ và tên địa điểm.
    Ưu tiên element có nhiều thông tin thực dụng nhất.
    """
    if not elements:
        return None

    def score(el):
        tags    = el.get("tags", {})
        center  = el.get("center", {})
        el_lat  = center.get("lat") or el.get("lat", lat)
        el_lon  = center.get("lon") or el.get("lon", lon)

        # Điểm khoảng cách (gần hơn = điểm cao hơn)
        dist = abs(el_lat - lat) + abs(el_lon - lon)

        # Điểm thông tin (có nhiều trường thực dụng hơn = tốt hơn)
        practical = extract_practical(tags)
        info_count = sum(1 for v in practical.values() if v)

        return info_count * 10 - dist * 1000

    elements.sort(key=score, reverse=True)
    return elements[0]


def main():
    # Đọc tất cả processed files có coordinates
    locations = []
    for filename in sorted(os.listdir(PROCESSED_DIR)):
        if not filename.endswith(".json"):
            continue
        filepath = os.path.join(PROCESSED_DIR, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        coords = data.get("coordinates")
        if not coords or len(coords) < 2:
            print(f"  [SKIP] {data['id']} — không có coordinates")
            continue
        locations.append({
            "id":       data["id"],
            "name":     data["name"],
            "coords":   coords,
            "filepath": filepath,
        })

    print(f"=== Fetch thông tin thực dụng cho {len(locations)} địa điểm ===\n")
    print("[Batch] Gửi Overpass query...")

    query = build_overpass_query(locations)
    try:
        res = requests.post(OVERPASS_URL, data={"data": query}, headers=HEADERS, timeout=90)
        res.raise_for_status()
        elements = res.json().get("elements", [])
        print(f"  OSM trả về: {len(elements)} elements\n")
    except Exception as e:
        print(f"  [ERROR] Overpass API: {e}")
        return

    # Map kết quả vào từng địa điểm
    success, no_data = 0, []

    for loc in locations:
        lat, lon = loc["coords"]

        # Lọc elements trong bán kính ~500m
        nearby = []
        for el in elements:
            center = el.get("center", {})
            el_lat = center.get("lat") or el.get("lat")
            el_lon = center.get("lon") or el.get("lon")
            if el_lat and el_lon:
                if abs(el_lat - lat) < 0.005 and abs(el_lon - lon) < 0.005:
                    nearby.append(el)

        match = best_match(nearby, loc["name"], lat, lon)

        if not match:
            print(f"  --  {loc['id']}: không tìm được trên OSM")
            no_data.append(loc["id"])
            practical = {k: None for k in ["opening_hours", "phone", "website", "fee", "charge", "address", "osm_name", "osm_name_en"]}
        else:
            practical = extract_practical(match.get("tags", {}))
            filled = sum(1 for v in practical.values() if v)
            print(f"  OK  {loc['id']}: {filled} trường có dữ liệu"
                  + (f" | {practical['opening_hours']}" if practical.get("opening_hours") else ""))

        # Cập nhật processed JSON
        with open(loc["filepath"], "r", encoding="utf-8") as f:
            data = json.load(f)
        data["practical"] = practical
        with open(loc["filepath"], "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        success += 1

    print(f"\n=== Cập nhật: {success}/{len(locations)} file ===")
    if no_data:
        print(f"Không tìm được OSM data: {no_data}")
    print("\nCác trường để null = OSM chưa có dữ liệu thật.")
    print("Bạn có thể tự điền sau tại: data/processed/<id>.json → field 'practical'")


if __name__ == "__main__":
    main()

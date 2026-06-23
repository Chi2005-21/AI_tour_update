"""
Tự động điền related_to cho 30 địa điểm dùng OSRM routing engine (miễn phí).

Dùng OSRM Table API — 1 lần gọi cho toàn bộ ma trận 30×30.
Kết quả: distance (km) và duration (phút) đường đi thực tế.

Ngưỡng related_to: <= 50km đường bộ.

Cách chạy:
    python -m src.ingestion.collectors.routing
"""

import sys
import os
import json
import requests
import math
import time

sys.stdout.reconfigure(encoding="utf-8")

PROCESSED_DIR = "data/processed"
HEADERS       = {"User-Agent": "TourGuideBot/1.0 (educational project; khiemxhbn@gmail.com)"}
OSRM_URL      = "http://router.project-osrm.org/table/v1/driving"

MAX_DISTANCE_KM = 50  # Chỉ lấy địa điểm trong vòng 50km đường bộ


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    """Tính khoảng cách đường chim bay (km) để lọc sơ bộ."""
    R = 6371
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = math.sin(d_lat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon/2)**2
    return R * 2 * math.asin(math.sqrt(a))


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
            "lat":      coords[0],
            "lon":      coords[1],
            "filepath": filepath,
        })

    print(f"=== Build related_to cho {len(locations)} địa điểm dùng OSRM ===\n")

    # OSRM Table API: lon,lat (chú ý thứ tự lon trước lat)
    coords_str = ";".join(f"{loc['lon']},{loc['lat']}" for loc in locations)
    url = f"{OSRM_URL}/{coords_str}?sources=all&destinations=all&annotations=distance,duration"

    print("[Batch] Gửi OSRM Table API request...")
    try:
        res = requests.get(url, headers=HEADERS, timeout=60)
        res.raise_for_status()
        data = res.json()
    except Exception as e:
        print(f"  [ERROR] OSRM API: {e}")
        return

    if data.get("code") != "Ok":
        print(f"  [ERROR] OSRM response: {data.get('message')}")
        return

    durations = data["durations"]   # giây
    distances = data["distances"]   # mét
    print(f"  Nhận được ma trận {len(locations)}×{len(locations)}\n")

    # Xây dựng related_to cho từng địa điểm
    for i, loc in enumerate(locations):
        related = []

        for j, other in enumerate(locations):
            if i == j:
                continue

            dur_sec  = durations[i][j]
            dist_m   = distances[i][j]

            # OSRM trả về null nếu không có đường bộ
            if dur_sec is None or dist_m is None:
                continue

            dist_km  = round(dist_m / 1000, 1)
            dur_min  = round(dur_sec / 60)

            if dist_km <= MAX_DISTANCE_KM:
                related.append({
                    "id":          other["id"],
                    "name":        other["name"],
                    "distance_km": dist_km,
                    "duration_min": dur_min,
                })

        # Sắp xếp theo khoảng cách gần nhất
        related.sort(key=lambda x: x["distance_km"])

        # Cập nhật file
        with open(loc["filepath"], "r", encoding="utf-8") as f:
            file_data = json.load(f)
        file_data["related_to"] = related
        with open(loc["filepath"], "w", encoding="utf-8") as f:
            json.dump(file_data, f, ensure_ascii=False, indent=2)

        print(f"  {loc['id']}: {len(related)} địa điểm liên quan"
              + (f" | gần nhất: {related[0]['name']} ({related[0]['distance_km']}km, {related[0]['duration_min']} phút)" if related else ""))

    print(f"\n=== Hoàn thành: {len(locations)}/{len(locations)} ===")


if __name__ == "__main__":
    main()

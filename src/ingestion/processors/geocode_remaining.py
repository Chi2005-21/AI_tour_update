import requests
import json

HEADERS = {"User-Agent": "TourGuideBot/1.0"}

# Tìm tọa độ làng Đông Hồ
queries = [
    "Song Ho Thuan Thanh Bac Ninh Vietnam",
    "Dong Ho Bac Ninh Vietnam",
    "Thuan Thanh Bac Ninh Vietnam",
]

for query in queries:
    res = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": query, "format": "json", "limit": 1},
        headers=HEADERS
    ).json()
    if res:
        lat  = round(float(res[0]["lat"]), 6)
        lon  = round(float(res[0]["lon"]), 6)
        name = res[0]["display_name"]
        print(f"Query: {query}")
        print(f"  [{lat}, {lon}] — {name[:80]}")

        path = "data/raw/tranh_dong_ho.json"
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["coordinates"] = [lat, lon]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("  Saved!")
        break
    else:
        print(f"Not found: {query}")

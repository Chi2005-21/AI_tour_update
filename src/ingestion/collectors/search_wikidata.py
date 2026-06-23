import requests
import json
import os

HEADERS = {"User-Agent": "TourGuideBot/1.0"}
RAW_DIR = "data/raw"

# Wikidata IDs đã xác nhận
MANUAL_WIDS = {
    "dao_bach_long_vi": "Q1136869",
    "tam_coc":          "Q1406000",
    "tranh_dong_ho":    "Q1923756",
}

# Tìm thêm Phố Cổ Hà Nội
def search_pho_co():
    url = "https://www.wikidata.org/w/api.php"
    for query in ["Khu pho co Ha Noi", "Old Quarter Hanoi", "36 streets Hanoi"]:
        params = {"action": "wbsearchentities", "search": query, "language": "en", "format": "json", "limit": 3}
        res = requests.get(url, params=params, headers=HEADERS).json()
        print(f"\nTìm '{query}':")
        for item in res.get("search", []):
            print(f"  {item['id']} — {item.get('label','')} — {item.get('description','')}")

search_pho_co()

# Lấy coordinates từ Wikidata cho 3 cái đã biết ID
print("\n--- Lấy coordinates ---")
values = " ".join([f"wd:{qid}" for qid in MANUAL_WIDS.values()])
query = f"""
SELECT ?item ?lat ?lon WHERE {{
  VALUES ?item {{ {values} }}
  ?item wdt:P625 ?coord .
  BIND(geof:latitude(?coord)  AS ?lat)
  BIND(geof:longitude(?coord) AS ?lon)
}}
"""
res = requests.get(
    "https://query.wikidata.org/sparql",
    params={"query": query, "format": "json"},
    headers=HEADERS, timeout=30
)
coords_map = {}
for row in res.json()["results"]["bindings"]:
    qid = row["item"]["value"].split("/")[-1]
    coords_map[qid] = [round(float(row["lat"]["value"]), 6), round(float(row["lon"]["value"]), 6)]

print("Coordinates tìm được:")
for loc_id, wid in MANUAL_WIDS.items():
    coords = coords_map.get(wid)
    print(f"  {loc_id}: {wid} → {coords}")
    if coords:
        path = os.path.join(RAW_DIR, f"{loc_id}.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["wikidata_id"]  = wid
        data["coordinates"]  = coords
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"    Saved!")

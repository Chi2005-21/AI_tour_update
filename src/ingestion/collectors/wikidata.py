"""
Fetch tọa độ GPS từ Wikidata cho 30 địa điểm — dùng batch (tối đa 3 lần gọi API).

Bước 1: Batch Wikipedia tiếng Việt  → lấy Wikidata IDs
Bước 2: Batch Wikipedia tiếng Anh   → lấy Wikidata IDs cho những cái còn thiếu
Bước 3: Batch Wikidata SPARQL       → lấy hết coordinates cùng lúc
Bước 4: Cập nhật 30 file JSON

Cách chạy:
    python -m src.ingestion.collectors.wikidata
"""

import requests
import json
import os
import urllib.parse

RAW_DIR = "data/raw"
HEADERS = {"User-Agent": "TourGuideBot/1.0 (educational project)"}


def batch_wikidata_ids(titles: list, lang: str) -> dict:
    """
    Gọi Wikipedia API 1 lần với nhiều tiêu đề.
    Trả về dict: { tiêu_đề_gốc -> wikidata_id }
    """
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "titles": "|".join(titles),
        "prop":   "pageprops",
        "ppprop": "wikibase_item",
        "format": "json"
    }
    res  = requests.get(url, params=params, headers=HEADERS, timeout=30)
    data = res.json()["query"]

    # Map tiêu đề đã chuẩn hóa → tiêu đề gốc
    normalized_map = {}
    for entry in data.get("normalized", []):
        normalized_map[entry["to"]] = entry["from"]

    result = {}
    for page_id, page in data["pages"].items():
        if page_id != "-1":
            canonical = page.get("title", "")
            wid       = page.get("pageprops", {}).get("wikibase_item")
            if wid:
                original = normalized_map.get(canonical, canonical)
                result[original] = wid
                result[canonical] = wid

    return result


def batch_get_coordinates(wikidata_ids: list) -> dict:
    """
    Gọi Wikidata SPARQL 1 lần để lấy coordinates cho nhiều IDs.
    Trả về dict: { wikidata_id -> [lat, lon] }
    """
    values = " ".join([f"wd:{qid}" for qid in wikidata_ids])
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
        headers=HEADERS,
        timeout=30
    )
    result = {}
    for row in res.json()["results"]["bindings"]:
        qid = row["item"]["value"].split("/")[-1]
        lat = round(float(row["lat"]["value"]), 6)
        lon = round(float(row["lon"]["value"]), 6)
        result[qid] = [lat, lon]
    return result


def en_title_from_url(url_en: str) -> str:
    """Trích tên tiếng Anh từ URL Wikipedia."""
    if not url_en:
        return ""
    title = url_en.split("/wiki/")[-1]
    return urllib.parse.unquote(title).replace("_", " ")


def main():
    # Đọc tất cả file JSON
    files = {}  # location_id -> { filepath, name_vi, name_en }
    for filename in sorted(os.listdir(RAW_DIR)):
        if not filename.endswith(".json"):
            continue
        filepath = os.path.join(RAW_DIR, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        files[data["id"]] = {
            "filepath": filepath,
            "name_vi":  data["name"],
            "name_en":  en_title_from_url(data.get("url_en", "")),
        }

    print(f"=== Batch fetch coordinates cho {len(files)} địa điểm ===\n")

    # --- Bước 1: Wikipedia tiếng Việt ---
    vi_names = [v["name_vi"] for v in files.values()]
    print(f"[Batch 1/3] Wikipedia tiếng Việt — {len(vi_names)} địa điểm...")
    name_to_wid = batch_wikidata_ids(vi_names, lang="vi")
    found_vi = len(set(name_to_wid.values()))
    print(f"  Tìm được: {found_vi}/{len(vi_names)}")

    # --- Bước 2: Fallback English Wikipedia cho những cái còn thiếu ---
    missing_ids = [
        loc_id for loc_id, v in files.items()
        if v["name_vi"] not in name_to_wid
    ]
    if missing_ids:
        en_names = [(loc_id, files[loc_id]["name_en"]) for loc_id in missing_ids if files[loc_id]["name_en"]]
        if en_names:
            print(f"\n[Batch 2/3] Wikipedia tiếng Anh — {len(en_names)} địa điểm còn thiếu...")
            en_titles = [name for _, name in en_names]
            en_result = batch_wikidata_ids(en_titles, lang="en")
            # Map ngược lại về location_id
            for loc_id, en_title in en_names:
                wid = en_result.get(en_title)
                if wid:
                    name_to_wid[files[loc_id]["name_vi"]] = wid
            found_en = len(set(name_to_wid.values())) - found_vi
            print(f"  Tìm thêm được: {found_en}")

    total_wids = list(set(name_to_wid.values()))
    print(f"\nTổng Wikidata IDs: {len(total_wids)}/{len(files)}")

    # --- Bước 3: Wikidata SPARQL lấy hết coordinates ---
    print(f"\n[Batch 3/3] Wikidata SPARQL — lấy coordinates...")
    wid_to_coords = batch_get_coordinates(total_wids)
    print(f"  Lấy được: {len(wid_to_coords)}/{len(total_wids)} coordinates")

    # --- Bước 4: Cập nhật files ---
    print("\n[Bước 4] Cập nhật files...")
    success, failed = 0, []

    for loc_id, v in files.items():
        wid    = name_to_wid.get(v["name_vi"])
        coords = wid_to_coords.get(wid) if wid else None

        if coords:
            with open(v["filepath"], "r", encoding="utf-8") as f:
                data = json.load(f)
            data["wikidata_id"]  = wid
            data["coordinates"]  = coords
            with open(v["filepath"], "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"  OK  {loc_id}: {coords}")
            success += 1
        else:
            reason = "không có Wikidata ID" if not wid else "không có coordinates"
            print(f"  --  {loc_id}: {reason}")
            failed.append(loc_id)

    print(f"\n=== Kết quả: {success}/{len(files)} ===")
    if failed:
        print(f"Chưa lấy được: {failed}")


if __name__ == "__main__":
    main()

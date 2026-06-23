"""
Tạo trang HTML để SOÁT caption bằng mắt: ảnh nằm cạnh caption.
Mở review_captions.html bằng trình duyệt -> lướt kiểm cả 30 ảnh trong 1 phút.

Cách chạy:
    python scripts/review_captions.py
"""

import os
import glob
import json
import html

PROCESSED_DIR = "data/processed"
OUT = "review_captions.html"

rows = []
for path in sorted(glob.glob(f"{PROCESSED_DIR}/*.json")):
    with open(path, "r", encoding="utf-8") as f:
        d = json.load(f)
    img = (d.get("image_path") or "").replace("\\", "/")
    name = html.escape(d.get("name", d.get("id", "")))
    loc_id = html.escape(d.get("id", ""))
    cap = html.escape(d.get("image_caption") or "(CHƯA CÓ CAPTION)")
    clarity = d.get("image_clarity") or "?"
    need = d.get("image_needs_review")

    flag_color = "#c00" if (need or not d.get("image_caption")) else "#0a0"
    flag_text = "⚠️ XEM LẠI" if need else ("❌ THIẾU" if not d.get("image_caption") else "✓ OK")

    rows.append(f"""
    <div class="card">
      <img src="{html.escape(img)}" loading="lazy" />
      <div class="info">
        <div class="title">{name} <span class="id">[{loc_id}]</span></div>
        <div class="caption">{cap}</div>
        <div class="meta">
          <span class="badge" style="background:{flag_color}">{flag_text}</span>
          <span class="clarity">độ rõ: {html.escape(str(clarity))}</span>
        </div>
      </div>
    </div>""")

doc = f"""<!doctype html>
<html lang="vi"><head><meta charset="utf-8">
<title>Soát caption ({len(rows)} ảnh)</title>
<style>
  body {{ font-family: system-ui, sans-serif; background:#f4f1ea; margin:0; padding:20px; }}
  h1 {{ font-size:20px; }}
  .hint {{ color:#666; margin-bottom:16px; font-size:14px; }}
  .card {{ display:flex; gap:16px; background:#fff; border-radius:10px;
           padding:12px; margin-bottom:14px; box-shadow:0 1px 4px rgba(0,0,0,.1); }}
  .card img {{ width:280px; height:200px; object-fit:cover; border-radius:6px; flex:none; background:#eee; }}
  .info {{ flex:1; }}
  .title {{ font-weight:600; font-size:16px; margin-bottom:6px; }}
  .id {{ color:#999; font-weight:400; font-size:13px; }}
  .caption {{ font-size:15px; line-height:1.5; color:#222; }}
  .meta {{ margin-top:10px; display:flex; gap:12px; align-items:center; }}
  .badge {{ color:#fff; padding:2px 8px; border-radius:4px; font-size:12px; }}
  .clarity {{ color:#666; font-size:13px; }}
</style></head><body>
<h1>Soát caption — {len(rows)} ảnh</h1>
<div class="hint">Nhìn ảnh, đọc caption bên phải. Kiểm: (1) tả ĐÚNG cái trong ảnh không?
(2) có chi tiết để nhận diện hay chỉ chung chung? (3) có bịa thông tin ngoài ảnh không?</div>
{''.join(rows)}
</body></html>"""

with open(OUT, "w", encoding="utf-8") as f:
    f.write(doc)

print(f"Da tao {OUT} ({len(rows)} anh). Mo bang trinh duyet de soat.")

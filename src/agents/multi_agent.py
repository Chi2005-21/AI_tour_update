"""
multi_agent.py — Hướng 2: Multimodal + Multi-Agent trên cùng xương sống RAG.

Vì sao KHÔNG rerank?  Vấn đề của hệ thống này là "type confusion" (retrieve lẫn
loại chunk), KHÔNG phải sai thứ tự. Rerank chỉ sắp lại 1 pool nhiễu -> vẫn nhiễu.
Type filter loại nhiễu TỪ ĐẦU. Mỗi agent = 1 "lane" sạch (lọc đúng type của mình).

Xử lý PROMPT DÀI NHIỀU CHỦ ĐỀ:
  Orchestrator PHÂN RÃ câu hỏi -> các sub-query theo intent.
  Mỗi sub-query đi vào ĐÚNG 1 lane (type filter + truy vấn riêng) -> retrieve sắc.
  Synthesizer gộp các context đã gán nhãn -> 1 câu trả lời mạch lạc.

Luồng:
  [ảnh? -> Vision Agent nhận diện -> location_id]   (multimodal, tùy chọn)
        -> Orchestrator (phân loại + phân rã)
        -> N agent chạy song song, mỗi agent lọc type của mình (+ khóa location nếu có)
        -> Synthesizer trả lời grounded, có nguồn, đúng ngôn ngữ

Chạy:
    python scripts/multi_agent.py "Văn Miếu mở cửa mấy giờ và có giai thoại gì hay?"
    python scripts/multi_agent.py --image data/images/vinh_ha_long.jpg "Kể chuyện và giá vé chỗ này"
    python scripts/multi_agent.py          # vài câu demo (gồm câu dài nhiều chủ đề)
"""

import os
import sys
import time
import json
import glob
import math
import threading
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor

sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv()

from google import genai
from google.genai import types
from qdrant_client import QdrantClient
from qdrant_client import models as qm
from fastembed import SparseTextEmbedding

try:
    from . import weather as wx          # khi import dạng package (src.agents.multi_agent)
except ImportError:
    import weather as wx                 # khi chạy trực tiếp file trong src/agents/

QDRANT_PATH = "./qdrant_data"
COLLECTION = "tourism"
EMBED_MODEL = "gemini-embedding-001"
LLM_MODEL = "gemini-2.5-flash-lite"
PROCESSED_DIR = "data/processed"

@dataclass
class _Hit:
    """Hit giả cho Route Agent — cùng interface với Qdrant ScoredPoint."""
    id: str
    payload: dict = field(default_factory=dict)


# ── Danh sách 30 địa điểm + lộ trình (load lúc setup) ──────────────────────────
_LOCATIONS = {}   # {id: name}
_ROUTES = {}      # {id: [{"id","name","distance_km","duration_min"}, ...]}
_COORDS = {}      # {id: (lat, lon)} — cho agent thời tiết + lập lịch trình
_PRACTICAL = {}   # {id: {"opening_hours","ticket_price","website",...}} — cho lịch trình
_INNER_TOUR = {}  # {id: [{"order","name","desc","minutes"}, ...]} — lộ trình BÊN TRONG 1 địa điểm
VISION_CONF_THRESHOLD = 0.55
ITINERARY_PER_DAY = 4   # số điểm tham quan mặc định mỗi ngày (thực tế cho 1 ngày)
MEDIA_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}

# ── Cấu hình CHI PHÍ (cho agent budget) — Mô hình "đọc sẵn": số có CƠ SỞ, ghi nguồn ──
# Vé = giá THẬT đọc từ practical (có source_url). Lưu trú/ăn = MỨC ước lượng tham khảo
# (không phải giá khách sạn cụ thể) — bot LUÔN gắn nhãn "ước lượng" + nguồn + ngày.
BUDGET_TIERS = {
    "bình dân":   {"luu_tru": (300_000, 500_000),    "an": (150_000, 250_000)},
    "trung bình": {"luu_tru": (700_000, 1_200_000),  "an": (300_000, 500_000)},
    "cao cấp":    {"luu_tru": (2_000_000, 4_000_000), "an": (600_000, 1_000_000)},
}
BUDGET_TIER_NGUON = "mặt bằng giá lưu trú/ăn uống phổ biến ở VN (ước lượng tham khảo)"
BUDGET_TIER_CAPNHAT = "2026-06"   # để bot nói rõ 'số liệu cập nhật ...'
BUDGET_KM_RATE = (3_000, 9_000)   # đ/km: (xe máy ~xăng, taxi/Grab phổ thông) — giá tham khảo

# ── Đăng ký agent: mỗi agent là 1 LANE retrieval, sở hữu (các) type riêng ──────
AGENTS = {
    "info": {
        "label": "Thông tin / Mô tả",
        "types": ["description"],
        "desc": "mô tả tổng quan, kiến trúc, lịch sử khái quát, hỏi-đáp kiến thức chung về địa điểm",
    },
    "story": {
        "label": "Kể chuyện",
        "types": ["storytelling", "fun_fact"],
        "desc": "kể chuyện, giai thoại, sự tích, nhân vật, điều thú vị ít người biết",
    },
    "practical": {
        "label": "Thông tin thực dụng",
        "types": ["practical"],
        "desc": "giờ mở cửa, giá vé, địa chỉ, số điện thoại, website — thông tin để đi tham quan",
    },
    "route": {
        "label": "Lộ trình / Địa điểm gần",
        "types": [],   # không dùng Qdrant — đọc related_to trực tiếp
        "desc": "gợi ý ĐỊA ĐIỂM KHÁC Ở GẦN để đi tiếp / kết hợp nhiều nơi (vd 'gần Văn Miếu có gì', "
                "'quanh đây đi đâu', 'từ X sang chỗ nào'); khoảng cách & thời gian di chuyển GIỮA các địa điểm",
    },
    "weather": {
        "label": "Thời tiết",
        "types": [],   # không dùng Qdrant — gọi WeatherAPI theo toạ độ
        "desc": "thời tiết, dự báo, nhiệt độ, mưa nắng, nên mang gì theo thời tiết, đi vào lúc này trời thế nào",
    },
    "itinerary": {
        "label": "Lịch trình nhiều ngày",
        "types": [],   # không dùng Qdrant — tự tính cụm điểm + nearest-neighbor
        "desc": "lập kế hoạch/lịch trình đi chơi NHIỀU NGÀY (2 ngày, 3 ngày...), đi những đâu mỗi ngày, "
                "xếp lộ trình tham quan, cần chuẩn bị/mang theo gì cho chuyến đi",
    },
    "inner_tour": {
        "label": "Lộ trình bên trong địa điểm",
        "types": [],   # không dùng Qdrant — đọc inner_tour trực tiếp
        "desc": "tham quan BÊN TRONG một địa điểm: vào trong rồi đi đâu/xem gì trước, các khu/hạng mục, "
                "thứ tự tham quan và thời gian gợi ý từng khu (vd 'trong Văn Miếu thăm gì', 'tham quan Văn Miếu 1 tiếng đi đâu')",
    },
    "budget": {
        "label": "Chi phí / Ngân sách",
        "types": [],   # không dùng Qdrant — tự tính từ vé thật + khoảng cách + mức ước lượng
        "desc": "CHI PHÍ chuyến đi: đi N ngày tốn bao nhiêu tiền; có sẵn X tiền thì đi được mấy ngày/những đâu; "
                "ước tính tiền vé + đi lại + ăn ở; tiết kiệm/giá rẻ hay cao cấp (vd 'đi 3 ngày tốn bao nhiêu', "
                "'tôi có 3 triệu đi được đâu', 'chi phí đi Hạ Long')",
    },
}

TYPE_LABEL = {"description": "mô tả", "storytelling": "câu chuyện", "fun_fact": "điều thú vị",
              "practical": "thông tin thực dụng", "image": "mô tả ảnh", "weather": "thời tiết",
              "route": "lộ trình", "itinerary": "lịch trình nhiều ngày", "inner_tour": "lộ trình bên trong",
              "budget": "chi phí"}

# Ngữ cảnh hội thoại: chỉ giữ vài lượt gần nhất để prompt không phình to (đủ để
# hiểu "chỗ này", "thế còn giờ mở cửa?" mà vẫn rẻ + nhanh).
HISTORY_MAX_TURNS = 6


def _format_history(history):
    """history = [{"role":"user"/"assistant","content":...}] -> đoạn text ngắn gọn.
    Cắt còn HISTORY_MAX_TURNS lượt cuối, mỗi lượt rút gọn để giữ prompt nhẹ."""
    if not history:
        return ""
    recent = history[-HISTORY_MAX_TURNS:]
    lines = []
    for m in recent:
        role = m.get("role")
        text = (m.get("content") or "").strip().replace("\n", " ")
        if not text:
            continue
        who = "Khách" if role == "user" else "Trợ lý"
        lines.append(f"{who}: {text[:300]}")
    return "\n".join(lines)


_g = _q = _bm25 = None
_q_lock = threading.Lock()   # Qdrant local mode KHÔNG thread-safe -> khóa khi query


def setup():
    global _g, _q, _bm25, _LOCATIONS
    _g = genai.Client(api_key=os.environ.get("GEMINI_API_KEY", ""))
    _q = QdrantClient(path=QDRANT_PATH)
    _bm25 = SparseTextEmbedding("Qdrant/bm25")
    for path in sorted(glob.glob(f"{PROCESSED_DIR}/*.json")):
        d = json.load(open(path, encoding="utf-8"))
        lid = d["id"]
        _LOCATIONS[lid] = d.get("name", lid)
        rt = d.get("related_to")
        if rt:
            _ROUTES[lid] = rt
        c = d.get("coordinates")
        if c and len(c) == 2:
            _COORDS[lid] = (c[0], c[1])
        pr = d.get("practical")
        if pr:
            _PRACTICAL[lid] = pr
        it = d.get("inner_tour")
        if it:
            _INNER_TOUR[lid] = it


def _llm(contents, retries=4):
    """generate_content có retry. Tối ưu cho WEB (không để treo lâu):
    - 429 (hết quota): retry 1 lần ngắn (2s) rồi BÁO LỖI NGAY — quota không hồi trong vài giây,
      retry dài chỉ làm web 'đang xử lý mãi'.
    - 503 (quá tải tạm thời): retry ngắn vì thường tự khỏi."""
    for i in range(retries):
        try:
            return _g.models.generate_content(model=LLM_MODEL, contents=contents)
        except Exception as e:
            msg = str(e)
            if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                if i == 0:
                    print("      [gemini 429] thử lại nhanh 1 lần...")
                    time.sleep(2)
                    continue
                raise   # vẫn 429 -> báo lỗi ngay, không treo
            if "503" in msg or "UNAVAILABLE" in msg:
                if i < retries - 1:
                    print(f"      [gemini 503] chờ {5*(i+1)}s rồi thử lại...")
                    time.sleep(5 * (i + 1))
                    continue
                raise
            raise


# ── Groq (Llama 3.3 70B): sinh text — gánh phần KHÔNG cần đa phương thức ───────
# Mục đích: bớt phụ thuộc quota Gemini. Orchestrator + Smalltalk chạy hẳn Groq;
# Synthesizer chạy Gemini chính, lỗi thì tự fallback Groq (giữ chất lượng, không chết).
GROQ_MODEL = "llama-3.3-70b-versatile"
_groq = None


class _Resp:
    """Bọc kết quả Groq cho cùng interface với Gemini response (.text)."""
    def __init__(self, text):
        self.text = text


def _get_groq():
    global _groq
    if _groq is None:
        from groq import Groq
        _groq = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))
    return _groq


def _llm_groq(contents, json_mode=False, temperature=0.4):
    """Sinh text bằng Groq Llama. contents = list (chỉ lấy phần TEXT — Groq không nhận ảnh).
    json_mode=True ép trả JSON (cho orchestrator)."""
    prompt = "\n\n".join(c for c in contents if isinstance(c, str))
    kwargs = {"model": GROQ_MODEL, "temperature": temperature,
              "messages": [{"role": "user", "content": prompt}]}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    r = _get_groq().chat.completions.create(**kwargs)
    return _Resp(r.choices[0].message.content or "")


def _llm_text(contents):
    """Sinh text user-facing: Gemini CHÍNH (giọng mượt), lỗi (429/sai key...) -> fallback Groq."""
    try:
        return _llm(contents)
    except Exception as e:
        print(f"      [fallback] Gemini lỗi ({str(e)[:50]}) -> dùng Groq")
        return _llm_groq(contents)


# ── Hạ tầng retrieval (tái dùng từ Hướng 1, thêm lọc type + location) ──────────
def _to_sparse(sv):
    return qm.SparseVector(indices=sv.indices.tolist(), values=sv.values.tolist())


def filtered_retrieve(question, types=None, location_id=None, k=6):
    """Hybrid retrieve (dense + BM25 + RRF) CÓ lọc theo type và/hoặc location."""
    dq = _g.models.embed_content(
        model=EMBED_MODEL, contents=[question],
        config=types_cfg(),
    ).embeddings[0].values
    sq = list(_bm25.embed([question]))[0]

    conds = []
    if types:
        conds.append(qm.FieldCondition(key="type", match=qm.MatchAny(any=list(types))))
    if location_id:
        conds.append(qm.FieldCondition(key="location_id", match=qm.MatchValue(value=location_id)))
    flt = qm.Filter(must=conds) if conds else None

    with _q_lock:
        return _q.query_points(
            collection_name=COLLECTION,
            prefetch=[
                qm.Prefetch(query=dq, using="dense", limit=20, filter=flt),
                qm.Prefetch(query=_to_sparse(sq), using="bm25", limit=20, filter=flt),
            ],
            query=qm.FusionQuery(fusion=qm.Fusion.RRF), limit=k,
        ).points


def types_cfg():
    return types.EmbedContentConfig(task_type="RETRIEVAL_QUERY")


def _parse_json(text):
    t = (text or "").strip()
    if t.startswith("```"):
        t = t.split("```", 2)[1]
        if t.startswith("json"):
            t = t[4:]
    i, j = t.find("{"), t.rfind("}")
    if i == -1 or j == -1:
        return None
    try:
        return json.loads(t[i:j + 1])
    except Exception:
        return None


# ── Vision Agent (multimodal): ảnh -> nhận diện + mô tả + OCR ──────────────────
# Vision CHỈ cung cấp thông tin thị giác; nội dung trả lời do RAG kiểm chứng.

def _load_candidates():
    cands = []
    for path in sorted(glob.glob(f"{PROCESSED_DIR}/*.json")):
        d = json.load(open(path, encoding="utf-8"))
        cands.append({"id": d.get("id"), "name": d.get("name"), "caption": d.get("image_caption") or ""})
    return cands


def vision_identify(img_path):
    """Nhận diện + mô tả + OCR ảnh trong 1 API call duy nhất.

    Trả về dict với:
        matched_id    : location_id nếu khớp 30 điểm, None nếu không
        matched_name  : tên địa điểm
        confidence    : 0.0–1.0
        reason        : lý do nhận diện
        description   : mô tả chi tiết những gì NHÌN THẤY trong ảnh
        ocr_text      : text đọc được từ biển hiệu/bảng chỉ dẫn (null nếu không có)
    """
    ext = os.path.splitext(img_path)[1].lower()
    mime = MEDIA_TYPES.get(ext)
    if not mime or not os.path.exists(img_path):
        return {"matched_id": None, "matched_name": None, "confidence": 0.0,
                "reason": "ảnh không hợp lệ hoặc không tồn tại",
                "description": "", "ocr_text": None}
    with open(img_path, "rb") as f:
        part = types.Part.from_bytes(data=f.read(), mime_type=mime)
    cands = _load_candidates()
    menu = "\n".join(f'- id="{c["id"]}" | {c["name"]}' for c in cands)
    prompt = f"""Bạn là chuyên gia du lịch Việt Nam, nhận diện địa danh trong ảnh. Làm ĐÚNG THỨ TỰ các bước.

BƯỚC 1 — MÔ TẢ ("description"): Tả CHÍNH XÁC những gì BẠN NHÌN THẤY trong ảnh (kiến trúc, vật thể, màu sắc, bố cục). Chỉ tả ảnh thật.

BƯỚC 2 — ĐẶC TRƯNG ĐỘC NHẤT ("key_features"): Nêu 1-3 đặc điểm ĐỘC NHẤT để phân biệt (vd: "tháp đá xám nhiều tầng đứng riêng giữa sân chùa", "ngôi chùa dựng trên một cột đá giữa hồ"). Đặc điểm CHUNG CHUNG (mái ngói đỏ, sân gạch, cây xanh, tường vàng) KHÔNG tính vì nơi nào cũng có.

BƯỚC 3 — NHẬN DIỆN BẰNG KIẾN THỨC ("guess_name"): Dựa vào KIẾN THỨC của bạn về danh thắng Việt Nam (KHÔNG dựa vào danh sách phía dưới), ảnh này nhiều khả năng là địa danh CỤ THỂ nào? Ghi tên thật. Nếu không nhận ra -> ghi "không rõ".
   Lưu ý phân biệt: tháp ĐÁ cổ trong khuôn viên CHÙA (vd Bút Tháp) ≠ tháp bát giác của TÒA NHÀ kiểu Pháp (vd Bảo tàng Lịch sử). Chùa gỗ mái cong ≠ bảo tàng tường vàng.

BƯỚC 4 — TRA DANH SÁCH: Tên ở bước 3 có nằm trong 30 địa điểm này không?
{menu}
   - Có -> matched_id = id tương ứng.
   - Bước 3 "không rõ" HOẶC tên không có trong danh sách -> matched_id=null. KHÔNG đoán bừa, KHÔNG ép khớp.
   - confidence = độ chắc THẬT của bước 3 (mơ hồ -> <0.5).

BƯỚC 5 — OCR: chữ trên biển hiệu/bảng trong ảnh (không có -> null).

Trả về DUY NHẤT JSON, GIỮ ĐÚNG THỨ TỰ KHÓA:
{{"description":"<mô tả ảnh thật>","key_features":"<đặc trưng độc nhất>","guess_name":"<tên địa danh theo kiến thức / không rõ>","matched_id":"<id|null>","matched_name":"<tên trong danh sách|null>","confidence":<0.0-1.0>,"reason":"<vì sao>","ocr_text":"<text|null>"}}"""
    try:
        resp = _llm([part, prompt])
    except Exception as e:
        return {"matched_id": None, "matched_name": None, "confidence": 0.0,
                "reason": f"lỗi gọi Vision: {str(e)[:100]}",
                "description": "", "ocr_text": None}
    r = _parse_json(resp.text) or {}
    mid = r.get("matched_id")
    conf = float(r.get("confidence") or 0)
    valid_ids = {c["id"] for c in cands}
    ok = bool(mid) and mid in valid_ids and conf >= VISION_CONF_THRESHOLD
    result = {
        "matched_id": mid if ok else None,
        "matched_name": r.get("matched_name") if ok else None,
        "confidence": conf,
        "reason": r.get("reason", ""),
        "description": r.get("description", ""),
        "key_features": r.get("key_features", ""),
        "guess_name": r.get("guess_name", ""),
        "ocr_text": r.get("ocr_text"),
    }
    return result


# ── Orchestrator: phân loại + PHÂN RÃ query dài nhiều chủ đề thành sub-task ────
ORCH_PROMPT = """Bạn là bộ điều phối (orchestrator) của trợ lý du lịch. Người dùng có thể hỏi DÀI và NHIỀU CHỦ ĐỀ trong 1 câu.

Có các agent chuyên trách sau:
{agent_menu}

DANH SÁCH 30 ĐỊA ĐIỂM (id | tên):
{location_menu}
{history_block}
NHIỆM VỤ:
1. SMALLTALK: Nếu tin nhắn chỉ là chào hỏi / cảm ơn / tạm biệt / hỏi "bạn là ai, làm được gì" / nói chuyện phiếm — KHÔNG phải câu hỏi về địa điểm du lịch -> "smalltalk": true, "tasks": [], "location_id": null.
   Ngược lại (có hỏi về du lịch/địa điểm) -> "smalltalk": false rồi làm bước 2-3.
2. Xác định người dùng đang hỏi về ĐỊA ĐIỂM NÀO trong danh sách trên. Rõ ràng -> "location_id". Không rõ / hỏi chung -> null.
   QUAN TRỌNG — dựa vào LỊCH SỬ HỘI THOẠI ở trên: nếu câu hiện tại KHÔNG nêu tên địa điểm nhưng nối tiếp câu trước (vd "thế giờ mở cửa?", "vé bao nhiêu?", "kể chuyện ở đó đi", "gần đó có gì?"), thì HIỂU địa điểm đang nói tới là địa điểm của lượt trước -> điền "location_id" tương ứng. Đồng thời viết lại "query" của các sub-task cho RÕ TÊN địa điểm đó (vd "giờ mở cửa Văn Miếu") để truy xuất chính xác.
3. Phân rã câu hỏi thành các sub-task, mỗi sub-task giao cho ĐÚNG 1 agent phù hợp.
- Câu hỏi chạm nhiều chủ đề -> tách thành NHIỀU sub-task.
- Mỗi sub-task có "query" NGẮN GỌN, tập trung đúng khía cạnh của agent đó (giữ tên địa điểm).
- Chỉ chọn agent THỰC SỰ cần. Không nhồi agent thừa.
- Với agent "weather": đặt "query" = ĐÚNG TÊN ĐỊA DANH cần xem thời tiết (vd "Hà Nội", "Sa Pa", "Hạ Long"), KHÔNG viết cả câu. Địa danh này có thể NGOÀI 30 điểm (vd "Hà Nội") — vẫn cho phép.
- Với agent "itinerary" (lập lịch trình NHIỀU NGÀY): CHỈ dùng khi người dùng muốn kế hoạch đi chơi 2-3 ngày / "đi mấy ngày nên đi đâu" / "cần mang gì cho chuyến đi". Khi đó GIỮ NGUYÊN số ngày trong "query" (vd "lịch trình 2 ngày Văn Miếu"), và phải có "location_id" là điểm gốc. KHÔNG thêm agent practical/route/weather riêng nữa — agent itinerary đã tự gộp giờ/vé/khoảng cách/thời tiết.
- PHÂN BIỆT "inner_tour" vs "route" (RẤT HAY NHẦM):
  * "inner_tour" = THAM QUAN / THĂM / DÀNH THỜI GIAN tại CHÍNH 1 địa điểm đó → xem các KHU BÊN TRONG. Dấu hiệu: "tham quan X", "thăm X", "vào X", "X có gì xem", "X trong 1 tiếng đi đâu/xem gì". Phải có "location_id"; GIỮ thời lượng trong "query" nếu user nêu.
  * "route" = đi tới ĐỊA ĐIỂM KHÁC ở gần / kết hợp nhiều nơi. Dấu hiệu: "GẦN X có gì", "QUANH X", "từ X SANG đâu", "đi đâu TIẾP".
  * VÍ DỤ: "tham quan Văn Miếu 1 tiếng đi đâu" → **inner_tour** (thăm bên trong Văn Miếu), KHÔNG phải route. Còn "gần Văn Miếu có gì chơi" → route.
- Với agent "budget" (CHI PHÍ/TIỀN): dùng khi câu hỏi nhắc TIỀN/CHI PHÍ/NGÂN SÁCH — "tốn bao nhiêu", "chi phí", "giá cả chuyến đi", "có X tiền đi được đâu/mấy ngày", "đi tiết kiệm/giá rẻ/cao cấp". GIỮ NGUYÊN trong "query" cả SỐ NGÀY, SỐ TIỀN và MỨC (tiết kiệm/cao cấp) nếu user nêu (vd "chi phí 3 ngày Văn Miếu mức tiết kiệm", "có 3 triệu quanh Hạ Long"). Cần "location_id" là điểm gốc nếu user có nêu địa danh. KHÔNG thêm itinerary/practical riêng — budget đã tự tính vé + đi lại + ăn ở.
{vision_hint}
Trả về DUY NHẤT JSON (không markdown):
{{"smalltalk":<true|false>,"location_id":"<id hoặc null>","tasks":[{{"agent":"<key agent>","query":"<truy vấn tập trung>"}}]}}

CÂU HỎI NGƯỜI DÙNG: {question}"""


def orchestrate(question, known_location_id=None, known_location_name=None, history=None):
    """Trả về (tasks, location_id, smalltalk)."""
    menu = "\n".join(f'- "{k}": {a["desc"]}' for k, a in AGENTS.items())
    loc_menu = "\n".join(f'- {lid} | {lname}' for lid, lname in _LOCATIONS.items())
    vhint = ""
    if known_location_name:
        vhint = (f'\nLƯU Ý: ảnh đã được nhận diện là "{known_location_name}" (id={known_location_id}). '
                 f'Nếu câu hỏi nói "chỗ này/nơi này", hiểu là địa điểm đó. Dùng location_id="{known_location_id}".\n')
    hist_txt = _format_history(history)
    hist_block = f"\nLỊCH SỬ HỘI THOẠI (gần nhất ở cuối):\n{hist_txt}\n" if hist_txt else ""
    prompt = ORCH_PROMPT.format(agent_menu=menu, location_menu=loc_menu, vision_hint=vhint,
                                history_block=hist_block, question=question)
    smalltalk = False
    try:
        resp = _llm_groq([prompt], json_mode=True)   # Orchestrator -> Groq (việc cấu trúc, đỡ quota Gemini)
        r = _parse_json(resp.text) or {}
        smalltalk = bool(r.get("smalltalk"))
        tasks = [t for t in r.get("tasks", []) if t.get("agent") in AGENTS and t.get("query")]
        detected_loc = r.get("location_id")
    except Exception:
        tasks = []
        detected_loc = None
    # Có ảnh nhận diện được -> luôn coi là câu hỏi du lịch (không smalltalk)
    if known_location_id:
        smalltalk = False
    if smalltalk:
        return [], None, True
    if not tasks:  # fallback: không phân rã được -> hỏi cả info (an toàn, grounded)
        tasks = [{"agent": "info", "query": question}]
    loc_id = known_location_id or detected_loc  # ưu tiên Vision > text detect
    if loc_id and loc_id not in _LOCATIONS:
        loc_id = None  # LLM trả id sai -> bỏ qua filter location
    return tasks, loc_id, False


# ── Mỗi agent: retrieve LANE riêng (type filter + sub-query + khóa location) ───
def _route_hits(location_id):
    """Route Agent: đọc related_to trực tiếp từ data, trả _Hit giả cùng interface."""
    if not location_id or location_id not in _ROUTES:
        return []
    nearby = _ROUTES[location_id]
    origin_name = _LOCATIONS.get(location_id, location_id)
    lines = [f"Từ {origin_name}, các địa điểm gần có thể kết hợp:"]
    for p in nearby:
        lines.append(
            f"- {p['name']} ({p['id']}): {p['distance_km']:.1f} km, ~{p['duration_min']} phút lái xe"
        )
    text = "\n".join(lines)
    return [_Hit(id=f"route_{location_id}", payload={
        "type": "route", "name": origin_name,
        "location_id": location_id, "text": text,
    })]


def _weather_hits(location_id, place=None):
    """Weather Agent: ưu tiên toạ độ của 30 điểm; nếu không có thì geocode theo TÊN
    địa danh (vd 'Hà Nội') để vẫn trả được thời tiết. place = tên do orchestrator tách."""
    name = _LOCATIONS.get(location_id, location_id) if location_id else (place or "")
    if not wx.is_configured():
        text = "Tính năng thời tiết chưa được bật (thiếu WEATHERAPI_KEY trong .env)."
    elif location_id and location_id in _COORDS:
        lat, lon = _COORDS[location_id]
        fc = wx.get_forecast(lat, lon, days=3)
        text = wx.format_forecast_text(name, fc) if fc else \
            f"Hiện chưa lấy được thời tiết cho {name} (lỗi kết nối WeatherAPI). Vui lòng thử lại sau."
    elif place:
        fc = wx.get_forecast_by_place(place, days=3)
        if fc:
            name = place   # hiển thị tên gốc có dấu người dùng nhập
            text = wx.format_forecast_text(name, fc)
        else:
            text = f"Hiện chưa tra được thời tiết cho '{place}' (không tìm thấy địa danh hoặc lỗi kết nối)."
    else:
        text = "Chưa rõ bạn muốn xem thời tiết ở đâu. Hãy nêu tên địa điểm (vd Hà Nội, Sa Pa, Hạ Long)."
    return [_Hit(id=f"weather_{location_id or place}", payload={
        "type": "weather", "name": name or "Thời tiết", "location_id": location_id, "text": text,
    })]


# ── Itinerary Planner (Lớp 1): code tính TOÀN BỘ con số, LLM chỉ diễn đạt ──────
# Vì sao tự tính: để các số (khoảng cách, thứ tự, tổng quãng) CHÍNH XÁC từ toạ độ
# thật — không để LLM bịa. LLM (Lớp 2) chỉ xếp giờ trong ngày + gợi ý mang gì.

def _haversine(c1, c2):
    """Khoảng cách đường chim bay (km) giữa 2 toạ độ (lat, lon)."""
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(math.radians, (c1[0], c1[1], c2[0], c2[1]))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _practical_brief(lid):
    """Rút giờ mở cửa + vé của 1 điểm (None nếu thiếu) — grounded, không bịa."""
    pr = _PRACTICAL.get(lid) or {}
    return {"opening_hours": pr.get("opening_hours"), "ticket_price": pr.get("ticket_price")}


def plan_itinerary(origin_id, days=2, per_day=ITINERARY_PER_DAY):
    """Lập khung lịch trình quanh origin_id (1 trong 30 điểm).

    Thuật toán (tất cả con số do CODE tính, grounded từ toạ độ thật):
      1. Cụm ứng viên = origin + các điểm trong related_to (đã là điểm gần thực tế).
      2. Chọn tối đa days*per_day điểm gần origin nhất (theo đường chim bay).
      3. Nearest-neighbor: bắt đầu từ origin, lặp chọn điểm gần nhất chưa thăm -> thứ tự.
      4. Chia thứ tự đó thành `days` ngày, ~per_day điểm/ngày.
    Trả về dict mô tả lịch (chưa diễn đạt) cho LLM ở Lớp 2.
    """
    if origin_id not in _COORDS:
        return None
    days = max(1, min(int(days), 5))
    # 1) cụm ứng viên: ưu tiên related_to (điểm gần thực tế), fallback toàn bộ 30 điểm
    cand_ids = [p["id"] for p in _ROUTES.get(origin_id, []) if p["id"] in _COORDS]
    if not cand_ids:
        cand_ids = [lid for lid in _COORDS if lid != origin_id]
    # 2) lấy gần origin nhất, đủ cho days*per_day điểm (gồm cả origin)
    cand_ids.sort(key=lambda lid: _haversine(_COORDS[origin_id], _COORDS[lid]))
    need = days * per_day - 1
    chosen = [origin_id] + cand_ids[:max(0, need)]
    # 3) nearest-neighbor xếp thứ tự thăm, bắt đầu từ origin
    unvisited = set(chosen)
    order = [origin_id]
    unvisited.discard(origin_id)
    while unvisited:
        last = order[-1]
        nxt = min(unvisited, key=lambda lid: _haversine(_COORDS[last], _COORDS[lid]))
        order.append(nxt)
        unvisited.discard(nxt)
    # 4) chia đều theo ngày + tính quãng mỗi chặng
    plan_days, total_km = [], 0.0
    for di in range(days):
        chunk = order[di * per_day:(di + 1) * per_day]
        if not chunk:
            break
        stops = []
        for i, lid in enumerate(chunk):
            prev = chunk[i - 1] if i > 0 else None
            leg = _haversine(_COORDS[prev], _COORDS[lid]) if prev else 0.0
            total_km += leg
            stops.append({
                "id": lid, "name": _LOCATIONS.get(lid, lid),
                "leg_km": round(leg, 1),
                "practical": _practical_brief(lid),
            })
        plan_days.append({"day": di + 1, "stops": stops})
    return {"origin_id": origin_id, "origin_name": _LOCATIONS.get(origin_id, origin_id),
            "days_count": len(plan_days), "days": plan_days, "total_km": round(total_km, 1)}


def _itinerary_hits(location_id, days=2):
    """Itinerary Agent: trả 1 _Hit chứa khung lịch trình đã tính + dự báo thời tiết.
    Toàn bộ là dữ liệu grounded để Synthesizer (Lớp 2) diễn đạt thành lịch trình."""
    if not location_id or location_id not in _COORDS:
        return [_Hit(id="itinerary_none", payload={
            "type": "itinerary", "name": "Lịch trình", "location_id": location_id,
            "text": "Chưa rõ lập lịch trình quanh địa điểm nào. Hãy nêu 1 địa điểm cụ thể "
                    "(vd: lịch trình 2 ngày quanh Văn Miếu).",
        })]
    plan = plan_itinerary(location_id, days=days)
    name = _LOCATIONS.get(location_id, location_id)
    lines = [f"KHUNG LỊCH TRÌNH {plan['days_count']} NGÀY quanh {name} "
             f"(các điểm + khoảng cách do hệ thống tính từ toạ độ, đường chim bay ước lượng; "
             f"tổng ~{plan['total_km']} km):"]
    for d in plan["days"]:
        lines.append(f"\n== NGÀY {d['day']} ==")
        for s in d["stops"]:
            pr = s["practical"]
            oh = pr.get("opening_hours") or "(chưa có dữ liệu giờ mở cửa)"
            tk = pr.get("ticket_price") or "(chưa có dữ liệu giá vé)"
            leg = f" — cách điểm trước ~{s['leg_km']} km" if s["leg_km"] else ""
            lines.append(f"- {s['name']}{leg}\n    Giờ mở cửa: {oh}\n    Vé: {tk}")
    # thời tiết theo toạ độ origin (≤3 ngày do free-tier)
    if wx.is_configured():
        lat, lon = _COORDS[location_id]
        fc = wx.get_forecast(lat, lon, days=min(plan["days_count"], 3))
        if fc:
            lines.append("\n" + wx.format_forecast_text(name, fc))
    text = "\n".join(lines)
    return [_Hit(id=f"itinerary_{location_id}", payload={
        "type": "itinerary", "name": name, "location_id": location_id,
        "text": text, "plan": plan,
    })]


def _parse_minutes(text):
    """Lấy thời lượng (phút) từ sub-query: '90 phút'->90, '1 tiếng'/'1 giờ'->60,
    'nửa ngày'->180, 'cả ngày'->360. Không nêu -> None (trả toàn tuyến)."""
    import re
    t = (text or "").lower()
    m = re.search(r"(\d+)\s*ph[uú]t", t)
    if m:
        return max(10, int(m.group(1)))
    m = re.search(r"(\d+)\s*(ti[eế]ng|gi[oờ]|h)\b", t)
    if m:
        return max(10, int(m.group(1)) * 60)
    if "nửa ngày" in t or "nua ngay" in t:
        return 180
    if "cả ngày" in t or "ca ngay" in t:
        return 360
    return None


def _inner_tour_hits(location_id, minutes=None):
    """Inner-Tour Agent: lộ trình tham quan BÊN TRONG 1 địa điểm.
    CODE chọn các điểm theo thứ tự `order`, cộng dồn `minutes`, cắt theo ngân sách thời gian;
    Synthesizer (Lớp 2) diễn đạt thành tuyến. Mọi con số do CODE -> không bịa."""
    if not location_id or location_id not in _INNER_TOUR:
        return [_Hit(id="inner_tour_none", payload={
            "type": "inner_tour", "name": _LOCATIONS.get(location_id, "Địa điểm"),
            "location_id": location_id,
            "text": "Chưa có dữ liệu lộ trình tham quan bên trong địa điểm này.",
        })]
    stops = sorted(_INNER_TOUR[location_id], key=lambda s: s.get("order", 0))
    name = _LOCATIONS.get(location_id, location_id)
    full_total = sum(int(s.get("minutes") or 0) for s in stops)

    # CODE chọn điểm vừa khung giờ (nếu có ngân sách); luôn lấy ít nhất 1 điểm
    if minutes:
        chosen, used = [], 0
        for s in stops:
            m = int(s.get("minutes") or 0)
            if not chosen or used + m <= minutes:
                chosen.append(s); used += m
            else:
                break
    else:
        chosen, used = stops, full_total

    head = (f"LỘ TRÌNH THAM QUAN BÊN TRONG {name} — {len(chosen)}/{len(stops)} điểm, "
            f"tổng ~{used} phút"
            + (f" (khách có ~{minutes} phút; toàn tuyến đầy đủ ~{full_total} phút)" if minutes
               else f" (toàn tuyến)") + ":")
    lines = [head]
    for s in chosen:
        lines.append(f"{s.get('order')}. {s.get('name')} (~{s.get('minutes')} phút): {s.get('desc')}")
    if minutes and len(chosen) < len(stops):
        chosen_orders = {s.get("order") for s in chosen}
        skipped = [s.get("name") for s in stops if s.get("order") not in chosen_orders]
        lines.append(f"(Vượt thời gian nên tạm bỏ qua: {', '.join(skipped)})")
    return [_Hit(id=f"inner_tour_{location_id}", payload={
        "type": "inner_tour", "name": name, "location_id": location_id,
        "text": "\n".join(lines),
    })]


def run_agent(agent_key, sub_query, location_id=None, k=6):
    if agent_key == "route":
        return _route_hits(location_id)
    if agent_key == "weather":
        return _weather_hits(location_id, place=sub_query)
    if agent_key == "itinerary":
        return _itinerary_hits(location_id, days=_parse_days(sub_query))
    if agent_key == "inner_tour":
        return _inner_tour_hits(location_id, minutes=_parse_minutes(sub_query))
    if agent_key == "budget":
        return _budget_hits(location_id, sub_query)
    types_ = AGENTS[agent_key]["types"]
    return filtered_retrieve(sub_query, types=types_, location_id=location_id, k=k)


def _parse_days(text):
    """Lấy số ngày từ sub-query (vd 'lịch trình 3 ngày' -> 3). Mặc định 2."""
    import re
    m = re.search(r"(\d+)\s*ng[aà]y", (text or "").lower())
    if m:
        return max(1, min(int(m.group(1)), 5))
    return 2


# ── Agent CHI PHÍ (budget): code tính số có cơ sở -> LLM diễn đạt, không bịa ───
def _fmt_vnd(n):
    """120000 -> '120.000đ'."""
    return f"{int(round(n)):,}".replace(",", ".") + "đ"


def _parse_ticket_vnd(s):
    """Lấy giá vé NGƯỜI LỚN (VND) từ chuỗi practical.ticket_price. None nếu không rõ -> KHÔNG bịa.
    'Người lớn 70.000đ; HS-SV 35.000đ' -> 70000 ; 'miễn phí' -> 0."""
    if not isinstance(s, str) or not s.strip():
        return None
    import re
    nums = re.findall(r"\d{1,3}(?:[.,]\d{3})+", s)   # số có phân cách nghìn: 70.000
    if nums:
        return int(nums[0].replace(".", "").replace(",", ""))
    low = s.lower()
    if "miễn phí" in low or "mien phi" in low or "free" in low:
        return 0
    return None


def _parse_tier(text):
    """Mức chi tiêu từ câu hỏi. Mặc định 'trung bình'."""
    t = (text or "").lower()
    if any(k in t for k in ["tiết kiệm", "tiet kiem", "bình dân", "binh dan", "giá rẻ", "gia re",
                            " rẻ", "ít tiền", "it tien", "sinh viên", "budget", "bụi"]):
        return "bình dân"
    if any(k in t for k in ["cao cấp", "cao cap", "sang", "5 sao", "đắt", "luxury", "vip"]):
        return "cao cấp"
    return "trung bình"


def _parse_budget(text):
    """Ngân sách (VND): '3 triệu'->3_000_000, '1.5tr'->1_500_000, '500k'->500_000, '2000000'."""
    import re
    t = (text or "").lower().replace(",", ".")
    m = re.search(r"(\d+(?:\.\d+)?)\s*(triệu|trieu|tr|củ|cu)\b", t)
    if m:
        return int(float(m.group(1)) * 1_000_000)
    m = re.search(r"(\d+(?:\.\d+)?)\s*(nghìn|nghin|ngàn|ngan|k)\b", t)
    if m:
        return int(float(m.group(1)) * 1_000)
    m = re.search(r"\b(\d{6,})\b", t.replace(".", ""))   # số trần >= 100.000
    if m:
        return int(m.group(1))
    return None


def plan_budget(origin_id, days=2, tier="trung bình"):
    """Dự toán chi phí cho khung lịch trình quanh origin_id. TẤT CẢ số do CODE tính.
    Vé = giá thật (practical); đi lại/lưu trú/ăn = ước lượng có cơ sở (km thật, mức tier)."""
    plan = plan_itinerary(origin_id, days=days)
    if not plan:
        return None
    t = BUDGET_TIERS.get(tier, BUDGET_TIERS["trung bình"])
    tickets, ticket_lines, unknown = 0, [], []
    for d in plan["days"]:
        for s in d["stops"]:
            v = _parse_ticket_vnd((s.get("practical") or {}).get("ticket_price"))
            if v is None:
                unknown.append(s["name"])
            else:
                tickets += v
                if v > 0:
                    ticket_lines.append(f"{s['name']}: {_fmt_vnd(v)}")
    n_days = plan["days_count"]
    nights = max(0, n_days - 1)
    km = plan["total_km"]
    transport = (km * BUDGET_KM_RATE[0], km * BUDGET_KM_RATE[1])
    lodging = (nights * t["luu_tru"][0], nights * t["luu_tru"][1])
    food = (n_days * t["an"][0], n_days * t["an"][1])
    total = (tickets + transport[0] + lodging[0] + food[0],
             tickets + transport[1] + lodging[1] + food[1])
    return {
        "origin_id": origin_id, "origin_name": plan["origin_name"],
        "days": n_days, "nights": nights, "tier": tier, "total_km": km,
        "tickets": tickets, "ticket_lines": ticket_lines, "unknown_ticket": unknown,
        "transport": transport, "lodging": lodging, "food": food, "total": total,
    }


def _max_days_for_budget(origin_id, budget, tier):
    """Bài toán ngược: ngân sách đủ ~bao nhiêu ngày (dùng mức GIỮA min–max cho an toàn)."""
    best = 0
    for d in range(1, 6):
        bp = plan_budget(origin_id, days=d, tier=tier)
        if not bp:
            break
        mid = (bp["total"][0] + bp["total"][1]) / 2
        if mid <= budget:
            best = d
        else:
            break
    return best


def _budget_text(bp):
    """Khung dự toán (đã tính) -> text có gắn nhãn THẬT/ƯỚC LƯỢNG cho Synthesizer diễn đạt."""
    L = [f"DỰ TOÁN CHI PHÍ — {bp['days']} ngày quanh {bp['origin_name']} — mức {bp['tier']} (1 người):"]
    L.append(f"• Vé tham quan (GIÁ THẬT, nguồn chính thức): tổng {_fmt_vnd(bp['tickets'])}")
    for tl in bp["ticket_lines"]:
        L.append(f"    - {tl}")
    if bp["unknown_ticket"]:
        L.append(f"    - (chưa có dữ liệu giá vé, không tính: {', '.join(bp['unknown_ticket'])})")
    L.append(f"• Di chuyển (ƯỚC LƯỢNG): ~{bp['total_km']} km × {_fmt_vnd(BUDGET_KM_RATE[0])}–{_fmt_vnd(BUDGET_KM_RATE[1])}/km "
             f"= {_fmt_vnd(bp['transport'][0])}–{_fmt_vnd(bp['transport'][1])}")
    L.append(f"• Lưu trú (ƯỚC LƯỢNG, mức {bp['tier']}): {bp['nights']} đêm "
             f"= {_fmt_vnd(bp['lodging'][0])}–{_fmt_vnd(bp['lodging'][1])}")
    L.append(f"• Ăn uống (ƯỚC LƯỢNG, mức {bp['tier']}): {bp['days']} ngày "
             f"= {_fmt_vnd(bp['food'][0])}–{_fmt_vnd(bp['food'][1])}")
    L.append(f"→ TỔNG ƯỚC TÍNH: {_fmt_vnd(bp['total'][0])} – {_fmt_vnd(bp['total'][1])} / người")
    L.append(f"CƠ SỞ: vé = giá niêm yết thật (có nguồn). Đi lại/lưu trú/ăn = {BUDGET_TIER_NGUON}, "
             f"cập nhật {BUDGET_TIER_CAPNHAT}; giá thực tế thay đổi theo thời điểm & lựa chọn "
             f"(tham khảo Booking/Agoda).")
    return "\n".join(L)


def _budget_hits(location_id, sub_query):
    tier = _parse_tier(sub_query)
    budget = _parse_budget(sub_query)
    if not location_id or location_id not in _COORDS:
        # Chưa rõ địa điểm -> vẫn cho mức chi/ngày (grounded theo tier), xin thêm địa điểm
        t = BUDGET_TIERS[tier]
        txt = (f"Chưa rõ đi đâu nên chưa tính được vé + đi lại. Riêng ăn ở mức {tier} (ƯỚC LƯỢNG): "
               f"lưu trú {_fmt_vnd(t['luu_tru'][0])}–{_fmt_vnd(t['luu_tru'][1])}/đêm, "
               f"ăn {_fmt_vnd(t['an'][0])}–{_fmt_vnd(t['an'][1])}/ngày. "
               f"Hãy nêu 1 địa điểm (vd 'chi phí 3 ngày quanh Văn Miếu') để tính trọn gói.")
        return [_Hit(id="budget_none", payload={"type": "budget", "name": "Chi phí",
                                                "location_id": location_id, "text": txt})]
    if budget:   # Mode B: có ngân sách -> đủ mấy ngày
        d = _max_days_for_budget(location_id, budget, tier)
        if d == 0:
            bp1 = plan_budget(location_id, days=1, tier=tier)
            txt = (f"Với {_fmt_vnd(budget)} ở mức {tier}, e rằng CHƯA đủ cho 1 ngày trọn gói quanh "
                   f"{bp1['origin_name']} (1 ngày ước ~{_fmt_vnd(bp1['total'][0])}–{_fmt_vnd(bp1['total'][1])}). "
                   f"Gợi ý: hạ xuống mức bình dân, hoặc tăng ngân sách.\n\n" + _budget_text(bp1))
            bp = bp1
        else:
            bp = plan_budget(location_id, days=d, tier=tier)
            note = "" if bp["days"] >= d else f" (quanh đây đủ điểm tham quan cho ~{bp['days']} ngày)"
            txt = (f"VỚI NGÂN SÁCH {_fmt_vnd(budget)} (mức {tier}) → đủ cho khoảng {bp['days']} ngày quanh "
                   f"{bp['origin_name']}{note}.\n\n" + _budget_text(bp))
    else:        # Mode A: tính chi phí cho N ngày
        bp = plan_budget(location_id, days=_parse_days(sub_query), tier=tier)
        txt = _budget_text(bp)
    return [_Hit(id=f"budget_{location_id}", payload={
        "type": "budget", "name": bp["origin_name"], "location_id": location_id,
        "text": txt, "budget_plan": bp,
    })]


# ── Synthesizer: gộp các context đã gán nhãn agent -> 1 câu trả lời ────────────
SYNTH_PROMPT = """Bạn là HƯỚNG DẪN VIÊN du lịch ảo thân thiện, am hiểu. Trả lời khách DỰA TRÊN các khối NGỮ CẢNH bên dưới (mỗi khối do một chuyên viên thu thập).

QUY TẮC BẮT BUỘC (chống bịa — KHÔNG được phá):
- {lang_rule}
- CHỈ dùng thông tin trong NGỮ CẢNH. TUYỆT ĐỐI KHÔNG bịa, không thêm kiến thức ngoài.
- Số liệu (km, giờ mở cửa, giá vé, thời gian) GIỮ ĐÚNG như NGỮ CẢNH — không chế, không đổi.
- Khía cạnh nào NGỮ CẢNH không có -> nói rõ "mình chưa có thông tin chắc chắn về điều này" (đúng ngôn ngữ câu hỏi), KHÔNG bịa.
- Câu hỏi nhiều ý -> trả lời ĐỦ các ý. Dùng LỊCH SỬ HỘI THOẠI (nếu có) chỉ để HIỂU câu nối tiếp; nội dung vẫn lấy từ NGỮ CẢNH.

GIỌNG HƯỚNG DẪN VIÊN (đây là cách NÓI, KHÔNG phải bịa thêm dữ kiện):
- Nói ẤM ÁP, có chút nhiệt tình như đang dẫn khách đi thật — ĐỪNG liệt kê khô khan từng dòng số.
- GOM/KẾT NỐI thông tin cho mượt thay vì gạch đầu dòng rời rạc (vd "mấy điểm này nằm sát nhau, bạn đi bộ là tới"; "ghé X trước rồi vòng qua Y").
- Gợi ý THỨ TỰ / cách kết hợp hợp lý DỰA TRÊN số liệu sẵn có (gần thì đi trước, cùng tuyến thì gộp) — nhưng không bịa lý do.
- Mở đầu mời gọi, kết một câu thân thiện. Vừa đủ, đừng lê thê.
{history_block}
{context}

CÂU HỎI: {question}

TRẢ LỜI (giọng hướng dẫn viên, bám sát số liệu):"""


def _block(agent_key, hits):
    head = f"### NGỮ CẢNH — {AGENTS[agent_key]['label']}"
    if not hits:
        return f"{head}\n(không tìm thấy dữ liệu phù hợp)"
    lines = []
    for h in hits:
        p = h.payload
        lab = TYPE_LABEL.get(p.get("type"), p.get("type"))
        lines.append(f"[Nguồn: {p.get('name')} | {lab}]\n{p.get('text')}")
    return head + "\n" + "\n\n".join(lines)


# Ký tự dấu đặc trưng tiếng Việt (chỉ cần XUẤT HIỆN 1 ký tự là đủ kết luận VI).
_VI_CHARS = set("ăâđêôơưàáảãạằắẳẵặầấẩẫậèéẻẽẹềếểễệìíỉĩịòóỏõọồốổỗộờớởỡợùúủũụừứửữựỳýỷỹỵ"
                "ĂÂĐÊÔƠƯÀÁẢÃẠẰẮẲẴẶẦẤẨẪẬÈÉẺẼẸỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌỒỐỔỖỘỜỚỞỠỢÙÚỦŨỤỪỨỬỮỰỲÝỶỸỴ")


def _detect_lang(text):
    """Có BẤT KỲ dấu tiếng Việt nào -> Vietnamese. Đáng tin hơn đếm tỉ lệ ASCII
    (câu ngắn ít dấu như "xin chào" trước đây bị nhận nhầm là tiếng Anh)."""
    return "Vietnamese" if any(c in _VI_CHARS for c in text) else "English"


SMALLTALK_PROMPT = """Bạn là trợ lý hướng dẫn viên du lịch ảo, CHỈ phục vụ 30 địa danh nổi tiếng MIỀN BẮC VIỆT NAM.
Người dùng vừa nói: "{question}"

Tin nhắn này KHÔNG phải câu hỏi về một địa điểm trong phạm vi. Đáp lại NGẮN GỌN, lịch sự ({lang}), theo ĐÚNG 1 trong 2 trường hợp:

A. NẾU người dùng hỏi/nhắc tới một nơi hoặc chủ đề NGOÀI phạm vi (nước khác như Hàn Quốc/Nhật, vùng miền khác, ẩm thực, khách sạn, chuyện không liên quan...):
   → MỞ ĐẦU bằng lời XIN LỖI và NÓI RÕ bạn CHƯA HỖ TRỢ điều đó, vì bạn chỉ chuyên 30 địa danh MIỀN BẮC VIỆT NAM. Nêu đích danh thứ họ hỏi (vd "mình chưa hỗ trợ du lịch Hàn Quốc").

B. NẾU chỉ là chào hỏi / cảm ơn / xã giao:
   → Chào lại thân thiện.

Sau đó (cả 2 trường hợp): giới thiệu NGẮN bạn giúp được gì (kể chuyện - lịch sử, giờ/vé, gợi ý lộ trình, nhận diện ảnh) và gợi ý 1 ví dụ trong phạm vi.
KHÔNG bịa thông tin. Trả lời ĐÚNG ngôn ngữ vừa nêu.
{history_block}"""


def _smalltalk_reply(question, history=None):
    lang = _detect_lang(question)
    hist_txt = _format_history(history)
    hist_block = f"\nLỊCH SỬ HỘI THOẠI (gần nhất ở cuối, để hiểu ngữ cảnh):\n{hist_txt}" if hist_txt else ""
    resp = _llm_groq([SMALLTALK_PROMPT.format(question=question, lang=lang, history_block=hist_block)])  # Smalltalk -> Groq
    return (resp.text or "").strip()


def synthesize(question, agent_hits, extra_context="", history=None):
    context = "\n\n".join(_block(ak, hits) for ak, hits in agent_hits)
    if extra_context:
        context += extra_context
    lang = _detect_lang(question)
    lang_rule = f"REPLY IN {lang.upper()} ONLY — the user's question is in {lang}."
    hist_txt = _format_history(history)
    hist_block = f"\n### LỊCH SỬ HỘI THOẠI (gần nhất ở cuối)\n{hist_txt}\n" if hist_txt else ""
    prompt = SYNTH_PROMPT.format(context=context, question=question,
                                 lang_rule=lang_rule, history_block=hist_block)
    resp = _llm_text([prompt])   # Synthesizer: Gemini chính (giọng mượt), lỗi -> fallback Groq
    sources, seen = [], set()
    for _, hits in agent_hits:
        for h in hits:
            nm = h.payload.get("name")
            if nm and nm not in seen:
                seen.add(nm)
                sources.append(nm)
    return (resp.text or "").strip(), sources


# ── Synthesizer cho LỊCH TRÌNH (Lớp 2): LLM chỉ diễn đạt khung đã tính sẵn ─────
ITINERARY_PROMPT = """Bạn là hướng dẫn viên du lịch ảo, soạn LỊCH TRÌNH DU LỊCH hoàn chỉnh cho khách dựa HOÀN TOÀN trên KHUNG LỊCH TRÌNH đã được hệ thống tính sẵn bên dưới.

QUY TẮC BẮT BUỘC:
- {lang_rule}
- Các con số (thứ tự điểm, khoảng cách km, tổng quãng, giờ mở cửa, giá vé, thời tiết) ĐÃ ĐÚNG trong KHUNG — GIỮ NGUYÊN, KHÔNG tự đổi, KHÔNG bịa thêm số mới.
- Trình bày theo TỪNG NGÀY. Mỗi ngày: chia buổi (Sáng/Chiều) hợp lý theo GIỜ MỞ CỬA của từng điểm; nêu điểm thăm, giá vé, quãng di chuyển giữa các điểm.
- Mục "🎒 Nên mang theo": suy luận TỪ DỰ BÁO THỜI TIẾT trong khung (mưa → ô/áo mưa; lạnh → áo ấm; nắng nóng → mũ, nước, kem chống nắng). Nếu khung KHÔNG có thời tiết → ghi "chưa có dữ liệu thời tiết để tư vấn đồ mang theo", KHÔNG bịa.
- Điểm nào khung ghi "(chưa có dữ liệu giờ mở cửa/giá vé)" → nói rõ là chưa có thông tin, KHÔNG tự chế.
- Giọng thân thiện, gọn, dễ theo. Có thể nhắc khách khoảng cách là ước lượng đường chim bay.
{history_block}
{context}

YÊU CẦU CỦA KHÁCH: {question}

LỊCH TRÌNH:"""


def synthesize_itinerary(question, agent_hits, history=None):
    """Diễn đạt khung lịch trình (đã tính ở Lớp 1) thành lịch trình hoàn chỉnh."""
    context = "\n\n".join(_block(ak, hits) for ak, hits in agent_hits)
    lang = _detect_lang(question)
    lang_rule = f"REPLY IN {lang.upper()} ONLY — the user's question is in {lang}."
    hist_txt = _format_history(history)
    hist_block = f"\n### LỊCH SỬ HỘI THOẠI (gần nhất ở cuối)\n{hist_txt}\n" if hist_txt else ""
    prompt = ITINERARY_PROMPT.format(context=context, question=question,
                                     lang_rule=lang_rule, history_block=hist_block)
    resp = _llm_text([prompt])   # Gemini chính, lỗi -> fallback Groq
    # Nguồn = tên TẤT CẢ điểm trong lịch (để hiện "📚 Nguồn"), gộp không trùng
    sources, seen = [], set()
    for _, hits in agent_hits:
        for h in hits:
            plan = h.payload.get("plan")
            names = ([st["name"] for d in plan["days"] for st in d["stops"]]
                     if plan and plan.get("days") else [h.payload.get("name")])
            for nm in names:
                if nm and nm not in seen:
                    seen.add(nm)
                    sources.append(nm)
    return (resp.text or "").strip(), sources


BUDGET_PROMPT = """Bạn là hướng dẫn viên du lịch ảo, trình bày DỰ TOÁN CHI PHÍ cho khách dựa HOÀN TOÀN trên KHUNG DỰ TOÁN đã được hệ thống tính sẵn bên dưới.

QUY TẮC BẮT BUỘC:
- {lang_rule}
- MỌI CON SỐ (tiền vé, đi lại, lưu trú, ăn, tổng, số ngày, km) ĐÃ ĐÚNG trong KHUNG — GIỮ NGUYÊN, KHÔNG tự đổi, KHÔNG bịa số mới.
- PHẢI nói rõ đâu là GIÁ THẬT (vé — có nguồn) và đâu là ƯỚC LƯỢNG (đi lại/lưu trú/ăn). Giữ dạng KHOẢNG (min–max), KHÔNG ép thành 1 số cứng.
- PHẢI nêu lại CƠ SỞ ước lượng (mức chi tiêu tham khảo + ngày cập nhật) và nhắc giá thực tế thay đổi — đúng như dòng CƠ SỞ trong khung.
- Điểm nào khung ghi "(chưa có dữ liệu giá vé)" → nói rõ là chưa có, KHÔNG tự chế giá.
- Giọng thân thiện, gọn, dễ hiểu. Có thể gợi ý đổi mức (tiết kiệm/cao cấp) hoặc điều chỉnh số ngày.
{history_block}
{context}

YÊU CẦU CỦA KHÁCH: {question}

DỰ TOÁN:"""


def synthesize_budget(question, agent_hits, history=None):
    """Diễn đạt khung dự toán chi phí (đã tính ở Lớp 1) thành câu trả lời, giữ nguyên số + nhãn nguồn."""
    context = "\n\n".join(_block(ak, hits) for ak, hits in agent_hits)
    lang = _detect_lang(question)
    lang_rule = f"REPLY IN {lang.upper()} ONLY — the user's question is in {lang}."
    hist_txt = _format_history(history)
    hist_block = f"\n### LỊCH SỬ HỘI THOẠI (gần nhất ở cuối)\n{hist_txt}\n" if hist_txt else ""
    prompt = BUDGET_PROMPT.format(context=context, question=question,
                                  lang_rule=lang_rule, history_block=hist_block)
    resp = _llm_text([prompt])
    sources, seen = [], set()
    for _, hits in agent_hits:
        for h in hits:
            nm = h.payload.get("name")
            if nm and nm not in seen:
                seen.add(nm)
                sources.append(nm)
    return (resp.text or "").strip(), sources


# ── Pipeline đầu-cuối ─────────────────────────────────────────────────────────
def answer(question, image_path=None, verbose=True, on_step=None, history=None,
           last_location_id=None):
    """Trả về (text, sources, trace). trace = dict mô tả từng bước (cho API/UI).
    on_step(name): callback tùy chọn báo tiến trình ("vision"/"orchestrate"/"retrieve"/"synth").
    history: [{"role":"user"/"assistant","content":...}] các lượt TRƯỚC (không gồm câu hiện tại)
             -> để hiểu câu hỏi nối tiếp ("thế còn giờ mở cửa?", "kể chuyện ở đó").
    last_location_id: địa điểm của lượt trả lời gần nhất (A3 carry-over) -> nếu lượt mới
             KHÔNG nêu địa điểm nào thì dùng lại cái này (nhớ "chỗ đang nói" mà không tốn LLM call)."""
    def _step(name):
        if on_step:
            on_step(name)
    trace = {"vision": None, "location_id": None, "location_name": None,
             "tasks": [], "lanes": [], "timings_ms": {}}
    vision_loc_id = vision_loc_name = None
    vision_description = ""
    vision_ocr = None

    # 1) Multimodal: nếu có ảnh -> Vision nhận diện + mô tả + OCR
    if image_path:
        _step("vision")
        _t = time.perf_counter()
        vr = vision_identify(image_path)
        trace["timings_ms"]["vision"] = int((time.perf_counter() - _t) * 1000)
        vision_loc_id = vr["matched_id"]
        vision_loc_name = vr["matched_name"]
        vision_description = vr.get("description", "")
        vision_ocr = vr.get("ocr_text")
        trace["vision"] = {
            "matched_id": vision_loc_id, "matched_name": vision_loc_name,
            "confidence": vr.get("confidence", 0.0), "reason": vr.get("reason", ""),
            "description": vision_description, "ocr_text": vision_ocr,
        }
        if verbose:
            if vision_loc_id:
                print(f"  [Vision] Nhận ra: {vision_loc_name} (id={vision_loc_id}, tin cậy {vr['confidence']:.0%})")
            else:
                print(f"  [Vision] Không nhận ra địa điểm (tin cậy {vr['confidence']:.0%}). Lý do: {vr['reason']}")
            if vision_description:
                print(f"  [Vision] Mô tả: {vision_description[:120]}...")
            if vision_ocr:
                print(f"  [Vision] OCR: {vision_ocr}")

    # 2) Orchestrator phân rã + detect location từ text
    #    Nếu Vision có OCR text -> bổ sung vào câu hỏi để BM25 khớp tên riêng
    enriched_question = question
    if vision_ocr:
        enriched_question = f"{question} (biển hiệu ghi: {vision_ocr})"

    _step("orchestrate")
    _t = time.perf_counter()
    tasks, location_id, smalltalk = orchestrate(
        enriched_question,
        known_location_id=vision_loc_id,
        known_location_name=vision_loc_name,
        history=history,
    )
    trace["timings_ms"]["orchestrate"] = int((time.perf_counter() - _t) * 1000)

    # Smalltalk (chào hỏi / cảm ơn / ngoài phạm vi) -> trả lời hội thoại, KHÔNG retrieve, KHÔNG nguồn
    if smalltalk:
        trace["smalltalk"] = True
        _step("synth")
        _t = time.perf_counter()
        text = _smalltalk_reply(question, history=history)
        trace["timings_ms"]["synth"] = int((time.perf_counter() - _t) * 1000)
        return text, [], trace

    # A3 — carry-over: lượt mới KHÔNG xác định được địa điểm nhưng lượt trước có
    #   -> dùng lại địa điểm cũ (vd: "Văn Miếu có gì?" rồi "thế giờ mở cửa?").
    #   Chỉ áp khi không có ảnh (ảnh đã cho location riêng) và last_location_id hợp lệ.
    if not location_id and last_location_id in _LOCATIONS:
        location_id = last_location_id
        trace["carried_location"] = True

    trace["location_id"] = location_id
    trace["location_name"] = _LOCATIONS.get(location_id) if location_id else None
    trace["tasks"] = [{"agent": t["agent"], "query": t["query"]} for t in tasks]
    if verbose:
        loc_label = f"{_LOCATIONS.get(location_id, '?')} ({location_id})" if location_id else "không xác định"
        print(f"  [Orchestrator] location={loc_label}")
        print("  [Orchestrator] sub-task:",
              " | ".join(f'{t["agent"]}<-"{t["query"]}"' for t in tasks))

    # 3) Các lane chạy SONG SONG (parallel retrieval per type) — gộp task cùng agent
    #    Nếu Vision có mô tả -> thêm làm query bổ sung cho agent info (Vision mô tả -> RAG kiểm chứng)
    merged = {}
    for t in tasks:
        merged.setdefault(t["agent"], []).append(t["query"])
    if vision_description:
        merged.setdefault("info", []).append(vision_description)

    def _lane(ak, queries):
        hits, seen_ids = [], set()
        for sq in queries:
            for h in run_agent(ak, sq, location_id=location_id):
                if h.id not in seen_ids:
                    seen_ids.add(h.id)
                    hits.append(h)
        return ak, hits

    _step("retrieve")
    _t = time.perf_counter()
    with ThreadPoolExecutor(max_workers=len(merged)) as ex:
        agent_hits = list(ex.map(lambda kv: _lane(*kv), merged.items()))
    trace["timings_ms"]["retrieve"] = int((time.perf_counter() - _t) * 1000)

    for ak, hits in agent_hits:
        trace["lanes"].append({
            "agent": ak, "label": AGENTS[ak]["label"], "types": AGENTS[ak]["types"],
            "n_chunks": len(hits),
            "chunk_types": [h.payload.get("type") for h in hits],
        })
        if verbose:
            locs = set(h.payload.get("location_id", "?") for h in hits)
            print(f"  [{ak}] lọc type={AGENTS[ak]['types']} + location={location_id or 'any'} -> {len(hits)} chunk, locations={locs}")

    # 4) Synthesizer — bổ sung mô tả ảnh vào context nếu có
    extra_context = ""
    if vision_description:
        extra_context = f"\n\n### NGỮ CẢNH — Mô tả ảnh người dùng gửi (từ Vision)\n{vision_description}"
        if vision_ocr:
            extra_context += f"\nText đọc được trong ảnh: {vision_ocr}"
    _step("synth")
    _t = time.perf_counter()
    # Có lane itinerary -> dùng synthesizer lập lịch riêng (khung đã tính sẵn ở Lớp 1).
    has_itinerary = any(ak == "itinerary" and hits for ak, hits in agent_hits)
    has_budget = any(ak == "budget" and hits for ak, hits in agent_hits)
    # Câu hỏi TIỀN -> budget ưu tiên (kể cả khi orchestrator gắn kèm itinerary);
    # synthesize_budget vẫn nhận context itinerary nên có thể nhắc lịch trình nếu cần.
    if has_budget:
        text, sources = synthesize_budget(question, agent_hits, history=history)
        for ak, hits in agent_hits:
            if ak == "budget" and hits and hits[0].payload.get("budget_plan"):
                trace["budget"] = hits[0].payload["budget_plan"]
                break
    elif has_itinerary:
        text, sources = synthesize_itinerary(question, agent_hits, history=history)
        # Gắn khung lịch vào trace để UI hiển thị (số liệu code đã tính)
        for ak, hits in agent_hits:
            if ak == "itinerary" and hits and hits[0].payload.get("plan"):
                trace["itinerary"] = hits[0].payload["plan"]
                break
    else:
        text, sources = synthesize(question, agent_hits, extra_context=extra_context, history=history)
    trace["timings_ms"]["synth"] = int((time.perf_counter() - _t) * 1000)
    return text, sources, trace


def main():
    setup()
    image_path = None
    args = sys.argv[1:]
    if args and args[0] == "--image":
        image_path = args[1].replace("\\", "/")
        args = args[2:]
    questions = args or [
        "Văn Miếu mở cửa mấy giờ, giá vé bao nhiêu, và có giai thoại gì hay không?",
        "What is special about Ha Long Bay and how much is the ticket?",
        "Tôi đang ở Bảo tàng Dân tộc học, từ đây đi đâu gần được?",
        "Kể chuyện Hồ Hoàn Kiếm và gợi ý lộ trình kết hợp gần đó",
    ]
    for q in questions:
        print("=" * 70)
        print("HỎI:", q)
        try:
            ans, srcs, _ = answer(q, image_path=image_path)
            print("\nĐÁP:", ans)
            print("\n(Nguồn:", ", ".join(srcs), ")")
        except Exception as e:
            print("  [lỗi]", str(e)[:160])
        print()
        image_path = None  # ảnh chỉ áp cho câu đầu khi truyền --image


if __name__ == "__main__":
    main()

"""
api.py — FastAPI backend bọc pipeline Multimodal + Multi-Agent (multi_agent.py).
Đồng thời PHỤC VỤ luôn web UI tĩnh ở thư mục web/ (chat đẹp thay Streamlit).

Endpoint:
    GET  /               -> web UI (web/index.html)
    GET  /health         -> trạng thái + số địa điểm đã nạp
    GET  /locations      -> 30 địa điểm kèm toạ độ + ảnh (cho bản đồ)
    POST /chat           -> hỏi-đáp: form "question" (+ file "image") -> {answer, sources, trace}
    POST /stt            -> form "audio" -> {text, language}   (Groq Whisper, free)
    POST /tts            -> json {text, lang?} -> audio/mpeg    (Edge TTS, free)

Chạy (từ thư mục gốc dự án, env có RAG stack):
    python -m src.api.main           # http://127.0.0.1:8000  (docs: /docs)
"""

import os
import re
import glob
import json
import base64
import tempfile
import contextlib

import src.agents.multi_agent as ma
import src.agents.voice as voice

from fastapi import FastAPI, Form, UploadFile, File, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

# Đường dẫn frontend tính theo vị trí file này -> chạy từ đâu cũng đúng.
# Frontend React đã build sẵn trong demo_VietGuide_AI-main/dist/ và commit cùng repo.
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEMO_DIST_DIR = os.path.join(ROOT_DIR, "demo_VietGuide_AI-main", "dist")
FRONTEND_DIR = DEMO_DIST_DIR

LOCATION_META = {}  # {id: {name, lat, lon, image_url, caption}}


def _load_location_meta():
    meta = {}
    for path in sorted(glob.glob(f"{ma.PROCESSED_DIR}/*.json")):
        with open(path, encoding="utf-8") as location_file:
            d = json.load(location_file)
        c = d.get("coordinates")
        meta[d["id"]] = {
            "name": d.get("name", d["id"]),
            "lat": c[0] if c and len(c) == 2 else None,
            "lon": c[1] if c and len(c) == 2 else None,
            "image_url": d.get("image_url"),
            "caption": (d.get("image_caption") or d.get("summary_vi") or "")[:160],
        }
    return meta


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    ma.setup()   # nạp Gemini client, Qdrant, BM25, danh sách địa điểm + lộ trình (1 lần)
    global LOCATION_META
    LOCATION_META = _load_location_meta()
    yield


app = FastAPI(title="AI Trợ Lý Hướng Dẫn Viên Du Lịch Ảo", version="1.0", lifespan=lifespan)

# CORS mở cho frontend (dev). Siết lại domain cụ thể khi deploy.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

ALLOWED_IMG_EXT = set(ma.MEDIA_TYPES.keys())


class ChatResponse(BaseModel):
    answer: str
    sources: list[str]
    trace: dict
    audio_b64: str | None = None   # mp3 base64 — chỉ có khi client bật "tự đọc" (tts=1)


def _strip_md(t: str) -> str:
    """Bỏ markdown để Edge TTS đọc tự nhiên (không đọc '###', '**')."""
    t = re.sub(r"```[\s\S]*?```", " ", t)
    t = re.sub(r"`([^`]+)`", r"\1", t)
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)   # link -> giữ chữ
    t = re.sub(r"^#{1,6}\s+", "", t, flags=re.M)
    t = re.sub(r"\*\*([^*]+)\*\*", r"\1", t)
    t = re.sub(r"\*([^*]+)\*", r"\1", t)
    t = re.sub(r"^\s*[-*+]\s+", "", t, flags=re.M)
    t = re.sub(r"^\s*\d+\.\s+", "", t, flags=re.M)
    t = t.replace("|", " ")
    return re.sub(r"[ \t]{2,}", " ", t).strip()


# ── API ───────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "n_locations": len(ma._LOCATIONS), "agents": list(ma.AGENTS.keys())}


@app.get("/locations")
def locations():
    """30 địa điểm kèm toạ độ + ảnh — cho bản đồ ở frontend."""
    return [{"id": lid, **LOCATION_META.get(lid, {"name": name})}
            for lid, name in ma._LOCATIONS.items()]


@app.post("/chat", response_model=ChatResponse)
async def chat(question: str = Form(""), image: UploadFile | None = File(default=None),
               history: str = Form(""), last_location_id: str = Form(""), tts: str = Form("")):
    if not question.strip() and image is None:
        raise HTTPException(400, "Cần ít nhất câu hỏi hoặc ảnh.")

    # history là JSON string [{"role","content"}] các lượt TRƯỚC (frontend gửi lên)
    hist = None
    if history.strip():
        try:
            parsed = json.loads(history)
            if isinstance(parsed, list):
                hist = [{"role": m.get("role"), "content": m.get("content", "")}
                        for m in parsed if isinstance(m, dict) and m.get("content")]
        except (json.JSONDecodeError, AttributeError):
            hist = None   # history hỏng -> bỏ qua, vẫn trả lời được (không ngữ cảnh)

    img_path = None
    try:
        # Lưu ảnh upload ra file tạm để Vision đọc (Gemini cần đường dẫn/bytes)
        if image is not None:
            ext = os.path.splitext(image.filename or "")[1].lower()
            if ext not in ALLOWED_IMG_EXT:
                raise HTTPException(400, f"Định dạng ảnh không hỗ trợ: {ext or '?'}. "
                                         f"Cho phép: {', '.join(sorted(ALLOWED_IMG_EXT))}")
            fd, img_path = tempfile.mkstemp(suffix=ext)
            with os.fdopen(fd, "wb") as f:
                f.write(await image.read())

        try:
            text, sources, trace = ma.answer(question, image_path=img_path, verbose=False,
                                             history=hist, last_location_id=last_location_id or None)
        except Exception as e:
            msg = str(e)
            if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                raise HTTPException(429, "Hết quota Gemini (free-tier giới hạn theo phút). Thử lại sau ít phút.")
            if "503" in msg or "UNAVAILABLE" in msg:
                raise HTTPException(503, "Gemini API đang quá tải, vui lòng thử lại sau vài giây.")
            raise HTTPException(500, f"Lỗi xử lý: {msg[:200]}")

        # Tạo audio KÈM câu trả lời (khi client bật "tự đọc") -> frontend có audio ngay,
        # không phải gọi /tts riêng rồi chờ "đang tạo audio".
        audio_b64 = None
        if tts.strip() and text.strip():
            try:
                clean = _strip_md(text)
                lang = voice.detect_language_simple(clean)
                audio_bytes = voice.text_to_speech_bytes(clean, lang=lang)
                audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
            except Exception:
                audio_b64 = None   # TTS lỗi -> vẫn trả câu trả lời, chỉ thiếu audio

        return ChatResponse(answer=text, sources=sources, trace=trace, audio_b64=audio_b64)
    finally:
        if img_path and os.path.exists(img_path):
            os.remove(img_path)


@app.post("/stt")
async def stt(audio: UploadFile = File(...)):
    """Giọng nói -> text (Groq Whisper, tự detect ngôn ngữ)."""
    ext = os.path.splitext(audio.filename or "")[1].lower() or ".webm"
    fd, apath = tempfile.mkstemp(suffix=ext)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(await audio.read())
        result = voice.speech_to_text(apath)
        return {"text": result["text"].strip(), "language": result.get("language", "auto")}
    except Exception as e:
        raise HTTPException(500, f"Lỗi STT: {str(e)[:200]}")
    finally:
        if os.path.exists(apath):
            os.remove(apath)


class TTSRequest(BaseModel):
    text: str
    lang: str | None = None


@app.post("/tts")
def tts(req: TTSRequest = Body(...)):
    """Text -> audio mp3 (Edge TTS, đa ngôn ngữ, free)."""
    if not req.text.strip():
        raise HTTPException(400, "Thiếu text.")
    lang = req.lang or voice.detect_language_simple(req.text)
    try:
        audio_bytes = voice.text_to_speech_bytes(req.text, lang=lang)
    except Exception as e:
        raise HTTPException(500, f"Lỗi TTS: {str(e)[:200]}")
    return Response(content=audio_bytes, media_type="audio/mpeg")


# ── Web UI tĩnh (phục vụ cuối cùng để không che các route API) ─────────────────
# React/Vite build dùng /assets.
demo_assets = os.path.join(DEMO_DIST_DIR, "assets")
if os.path.isdir(demo_assets):
    app.mount("/assets", StaticFiles(directory=demo_assets), name="demo-assets")


@app.get("/")
def index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/{path:path}")
def spa_fallback(path: str):
    """Cho phép refresh/mở trực tiếp các route React như /chat, /explore."""
    target = os.path.join(FRONTEND_DIR, path)
    if os.path.isfile(target):
        return FileResponse(target)
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


if __name__ == "__main__":
    import uvicorn
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host=host, port=port)

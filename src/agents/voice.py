"""
voice.py — STT (Groq Whisper, free) + TTS (Edge TTS, free) đa ngôn ngữ.

STT: giọng nói → text (tự detect ngôn ngữ) — Groq Whisper large-v3 (free tier)
TTS: text → audio file (đa ngôn ngữ VI, EN, ZH, KO, JA...) — Edge TTS (free)

Toàn bộ $0 — không cần nạp tiền.

Chạy demo:
    python scripts/voice.py tts "Xin chào, đây là Văn Miếu!"
    python scripts/voice.py tts "Welcome to Ha Long Bay!" --lang en
    python scripts/voice.py tts "ここは文廟です" --lang ja
    python scripts/voice.py stt path/to/audio.wav
"""

import os
import sys
import time
import asyncio

sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv()

# ── Config ───────────────────────────────────────────────────────────────────
# Edge TTS config — giọng theo ngôn ngữ (tất cả free)
EDGE_VOICES = {
    "vi": "vi-VN-HoaiMyNeural",      # nữ Việt, tự nhiên
    "en": "en-US-JennyNeural",       # nữ Anh
    "zh": "zh-CN-XiaoxiaoNeural",    # nữ Trung
    "ko": "ko-KR-SunHiNeural",       # nữ Hàn
    "ja": "ja-JP-NanamiNeural",      # nữ Nhật
    "fr": "fr-FR-DeniseNeural",      # nữ Pháp
    "de": "de-DE-KatjaNeural",       # nữ Đức
}
EDGE_DEFAULT_VOICE = "vi-VN-HoaiMyNeural"

# STT config (Groq Whisper — free)
STT_MODEL = "whisper-large-v3"   # Groq hỗ trợ whisper-large-v3

OUTPUT_DIR = "data/audio"

_groq_client = None


def _get_groq():
    global _groq_client
    if _groq_client is None:
        from groq import Groq
        _groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))
    return _groq_client


# ── STT: Speech-to-Text (Whisper) ───────────────────────────────────────────
def speech_to_text(audio_path, language=None):
    """Chuyển file audio thành text bằng Groq Whisper (free, tự detect ngôn ngữ).

    Args:
        audio_path: file audio (mp3, wav, m4a, webm...)
        language: mã ISO-639-1 ("vi", "en"...). None = tự detect.

    Returns:
        dict: {"text": "...", "language": "vi"}
    """
    client = _get_groq()
    with open(audio_path, "rb") as f:
        kwargs = {"model": STT_MODEL, "file": f, "response_format": "verbose_json"}
        if language:
            kwargs["language"] = language
        resp = client.audio.transcriptions.create(**kwargs)

    return {
        "text": resp.text,
        "language": getattr(resp, "language", language or "auto"),
    }


# ── TTS: Text-to-Speech ─────────────────────────────────────────────────────
def text_to_speech(text, lang="vi", voice=None, output_path=None):
    """Chuyển text thành audio file bằng Edge TTS (free).

    Args:
        text: nội dung cần đọc
        lang: mã ngôn ngữ ("vi", "en", "zh", "ko", "ja"...) — chọn voice tự động
        voice: tên giọng cụ thể (override). None = tự chọn theo lang.
        output_path: đường dẫn lưu file. None = tự tạo.

    Returns:
        str: đường dẫn file audio (.mp3)
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if not output_path:
        ts = int(time.time() * 1000)
        output_path = os.path.join(OUTPUT_DIR, f"tts_{ts}.mp3")

    return _tts_edge(text, lang, voice, output_path)


def _tts_edge(text, lang, voice, output_path, retries=3):
    """TTS bằng Edge TTS — miễn phí, đa ngôn ngữ.

    Edge TTS thỉnh thoảng trả rỗng ("No audio was received") do dịch vụ Microsoft
    chập chờn — KHÔNG phụ thuộc nội dung. Vì là lỗi ngẫu nhiên -> thử lại vài lần.
    """
    import edge_tts

    if not voice:
        voice = EDGE_VOICES.get(lang, EDGE_DEFAULT_VOICE)

    async def _run():
        comm = edge_tts.Communicate(text, voice)
        await comm.save(output_path)

    last_err = None
    for i in range(retries):
        try:
            asyncio.run(_run())
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return output_path
            last_err = RuntimeError("Edge TTS trả file rỗng")
        except Exception as e:
            last_err = e
        # lỗi ngẫu nhiên -> chờ ngắn rồi thử lại
        if i < retries - 1:
            time.sleep(0.6 * (i + 1))
    raise last_err if last_err else RuntimeError("Edge TTS thất bại")


# ── TTS streaming bytes (cho FastAPI StreamingResponse) ──────────────────────
def text_to_speech_bytes(text, lang="vi", voice=None):
    """Trả về bytes audio — dùng cho API response.

    Ví dụ FastAPI:
        from fastapi.responses import Response
        @app.post("/tts")
        async def tts(req: TTSRequest):
            audio_bytes = text_to_speech_bytes(req.text, lang=req.lang)
            return Response(content=audio_bytes, media_type="audio/mpeg")
    """
    import tempfile
    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tmp.close()
    text_to_speech(text, lang=lang, voice=voice, output_path=tmp.name)
    with open(tmp.name, "rb") as f:
        data = f.read()
    os.unlink(tmp.name)
    return data


# ── Detect ngôn ngữ đơn giản (cho TTS chọn voice) ──────────────────────────
def detect_language_simple(text):
    """Detect ngôn ngữ đơn giản bằng Unicode range. Dùng cho TTS chọn voice.
    Không cần chính xác 100% — chỉ để chọn voice gần đúng."""
    # Đếm ký tự theo script
    cjk = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')        # CJK (Trung)
    hangul = sum(1 for c in text if '\uac00' <= c <= '\ud7af')     # Hangul (Hàn)
    kana = sum(1 for c in text if '\u3040' <= c <= '\u30ff')       # Hiragana/Katakana (Nhật)
    viet = sum(1 for c in text if c in 'àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ')
    latin = sum(1 for c in text if 'a' <= c.lower() <= 'z')

    if cjk > 2:
        return "zh"
    if hangul > 2:
        return "ko"
    if kana > 2:
        return "ja"
    if viet > 0:
        return "vi"
    if latin > 0:
        return "en"
    return "vi"  # default


# ── CLI demo ─────────────────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print("Dùng:")
        print('  python scripts/voice.py tts "Xin chào!"')
        print('  python scripts/voice.py tts "Hello!" --lang en')
        print('  python scripts/voice.py tts "こんにちは" --lang ja')
        print("  python scripts/voice.py stt path/to/audio.wav")
        print("\nEngine TTS: Edge TTS (free) · STT: Groq Whisper large-v3 (free)")
        print(f"Giọng Edge TTS: {EDGE_VOICES}")
        return

    mode = sys.argv[1]

    if mode == "tts":
        text = sys.argv[2] if len(sys.argv) > 2 else "Xin chào, tôi là hướng dẫn viên du lịch ảo."
        lang = "vi"
        if "--lang" in sys.argv:
            idx = sys.argv.index("--lang")
            lang = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "vi"
        else:
            lang = detect_language_simple(text)

        voice_name = EDGE_VOICES.get(lang, EDGE_DEFAULT_VOICE)
        print(f'TTS [edge]: "{text[:60]}..." (lang={lang}, voice={voice_name})')
        path = text_to_speech(text, lang=lang)
        size_kb = os.path.getsize(path) / 1024
        print(f"✅ Đã lưu: {path} ({size_kb:.0f} KB)")

    elif mode == "stt":
        audio_path = sys.argv[2] if len(sys.argv) > 2 else None
        if not audio_path or not os.path.exists(audio_path):
            print("Cần truyền đường dẫn file audio hợp lệ.")
            return
        print(f"STT [whisper]: {audio_path}")
        result = speech_to_text(audio_path)
        print(f"✅ Ngôn ngữ: {result['language']}")
        print(f"   Text: {result['text']}")

    else:
        print(f"Mode không hợp lệ: {mode}. Dùng 'tts' hoặc 'stt'.")


if __name__ == "__main__":
    main()

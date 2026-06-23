"""
weather.py — Dự báo thời tiết, dùng WeatherAPI.com (free, có tiếng Việt).

Thiết kế sau MỘT interface nhỏ:
  - get_forecast(lat, lon, days)        -> theo toạ độ (chính xác cho 30 điểm)
  - get_forecast_by_place(place, days)  -> theo TÊN địa danh (WeatherAPI tự geocode,
                                           dùng cho "Hà Nội", "Sa Pa"... ngoài 30 điểm)
=> muốn đổi provider chỉ sửa file này, agent không đổi.

Cấu hình: đặt WEATHERAPI_KEY trong .env (lấy ở weatherapi.com → My Account).
Dữ liệu động -> cache ngắn (mặc định 30 phút) và luôn kèm thời điểm lấy + nguồn.
"""

import os
import time
import logging
import threading
import unicodedata
import requests

from dotenv import load_dotenv
load_dotenv()

log = logging.getLogger(__name__)


def _ascii_vn(s: str) -> str:
    """Bỏ dấu tiếng Việt: 'Hà Nội' -> 'Ha Noi' (WeatherAPI geocode chuẩn hơn với ASCII)."""
    s = s.replace("đ", "d").replace("Đ", "D")
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn")

PROVIDER = "WeatherAPI"
_BASE = "https://api.weatherapi.com/v1/forecast.json"
_CACHE = {}              # {(q, days): (epoch, data)}
_CACHE_LOCK = threading.Lock()   # weather/itinerary lane chạy song song -> khóa khi đọc/ghi cache
_TTL = 1800             # 30 phút — thời tiết đổi chậm, đỡ tốn lượt gọi
_MAX_DAYS = 3           # bản free WeatherAPI cho tối đa 3 ngày


def is_configured() -> bool:
    return bool(os.environ.get("WEATHERAPI_KEY", "").strip())


def _fetch(q, days):
    """Gọi WeatherAPI với q = 'lat,lon' HOẶC tên địa danh. Trả dict chuẩn hoá / None."""
    key = os.environ.get("WEATHERAPI_KEY", "").strip()
    if not key or not q:
        return None

    days = max(1, min(int(days), _MAX_DAYS))
    ckey = (str(q), days)
    now = time.time()
    with _CACHE_LOCK:                       # đọc cache có khóa (lane song song)
        cached = _CACHE.get(ckey)
    if cached and now - cached[0] < _TTL:
        return cached[1]

    try:
        r = requests.get(_BASE, params={
            "key": key, "q": q, "days": days,
            "lang": "vi", "aqi": "no", "alerts": "no",
        }, timeout=8)
        r.raise_for_status()
        raw = r.json()
    except requests.HTTPError as e:
        # Phân biệt rõ để dễ debug: key sai (401/403) vs rate limit (429) vs lỗi HTTP khác
        code = e.response.status_code if e.response is not None else None
        if code in (401, 403):
            log.warning("WeatherAPI từ chối (HTTP %s) — kiểm tra WEATHERAPI_KEY", code)
        elif code == 429:
            log.warning("WeatherAPI hết hạn mức (HTTP 429) — thử lại sau")
        else:
            log.warning("WeatherAPI lỗi HTTP %s cho q=%r", code, q)
        return None
    except requests.RequestException as e:
        # mạng/timeout (transient) — tách khỏi lỗi HTTP ở trên
        log.warning("WeatherAPI lỗi kết nối (%s) cho q=%r", type(e).__name__, q)
        return None
    except Exception as e:
        log.warning("WeatherAPI lỗi không xác định (%s) cho q=%r", type(e).__name__, q)
        return None

    cur = raw.get("current", {})
    data = {
        "provider": PROVIDER,
        "fetched_at": time.strftime("%Y-%m-%d %H:%M"),
        "place": (raw.get("location") or {}).get("name"),  # tên WeatherAPI nhận diện
        "current": {
            "temp_c": cur.get("temp_c"),
            "feelslike_c": cur.get("feelslike_c"),
            "condition": (cur.get("condition") or {}).get("text"),
            "humidity": cur.get("humidity"),
            "wind_kph": cur.get("wind_kph"),
        },
        "days": [],
    }
    for fd in (raw.get("forecast", {}).get("forecastday") or []):
        day, astro = fd.get("day", {}), fd.get("astro", {})
        data["days"].append({
            "date": fd.get("date"),
            "min_c": day.get("mintemp_c"),
            "max_c": day.get("maxtemp_c"),
            "rain_chance": day.get("daily_chance_of_rain"),
            "condition": (day.get("condition") or {}).get("text"),
            "sunrise": astro.get("sunrise"),
            "sunset": astro.get("sunset"),
        })

    with _CACHE_LOCK:                       # ghi cache có khóa
        _CACHE[ckey] = (now, data)
    return data


def get_forecast(lat, lon, days=3):
    """Theo toạ độ — chính xác cho 30 điểm đã có coordinates."""
    if lat is None or lon is None:
        return None
    return _fetch(f"{lat},{lon}", days)


def get_forecast_by_place(place, days=3):
    """Theo tên địa danh — bỏ dấu + ép Việt Nam để geocode chuẩn (vd 'Hà Nội', 'Sa Pa')."""
    place = (place or "").strip()
    if not place:
        return None
    q = _ascii_vn(place)
    if "viet" not in q.lower():
        q = f"{q}, Vietnam"   # ép phạm vi VN, tránh trùng tên nước ngoài (Sapa->Sapanca/TR)
    return _fetch(q, days)


def format_forecast_text(place_name, fc) -> str:
    """Biến dict thời tiết -> đoạn text có nhãn + nguồn cho Synthesizer (grounded)."""
    if not fc:
        return ""
    lines = [f"Thời tiết tại {place_name} (nguồn {fc['provider']}, lấy lúc {fc['fetched_at']}):"]
    c = fc.get("current") or {}
    if c.get("temp_c") is not None:
        lines.append(
            f"- Hiện tại: {c.get('condition') or '—'}, {c['temp_c']}°C "
            f"(cảm giác {c.get('feelslike_c')}°C), độ ẩm {c.get('humidity')}%, gió {c.get('wind_kph')} km/h."
        )
    for i, d in enumerate(fc.get("days") or []):
        tag = " (hôm nay)" if i == 0 else ""
        lines.append(
            f"- {d['date']}{tag}: {d.get('condition') or '—'}, "
            f"{d.get('min_c')}–{d.get('max_c')}°C, khả năng mưa {d.get('rain_chance')}%. "
            f"Bình minh {d.get('sunrise')}, hoàng hôn {d.get('sunset')}."
        )
    return "\n".join(lines)

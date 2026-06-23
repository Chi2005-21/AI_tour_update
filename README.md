# AI Trợ Lý Hướng Dẫn Viên Du Lịch Ảo

**Tourism — Virtual Tour Guide using Multimodal RAG + MultiAgent**

---

## Tech Stack

| Layer | Công nghệ |
|---|---|
| **LLM + Vision** | Claude claude-sonnet-4-6 |
| **RAG Framework** | LlamaIndex |
| **Vector DB** | Qdrant |
| **STT** | OpenAI Whisper |
| **TTS** | OpenAI TTS |
| **Backend** | FastAPI (Python) |
| **Frontend** | React |

> Bảng trên là **stack mục tiêu** (đích nâng cấp). **Bản đang chạy thực tế** như sau:

| Thành phần | Provider / model (thực tế) | Quota |
|---|---|---|
| LLM — Orchestrator · Synthesizer · Vision | Google **Gemini 2.5 Flash-Lite** | Gemini |
| Embedding (dense) | **gemini-embedding-001** (3072d) — index Qdrant đã build bằng model này | Gemini |
| Retrieval sparse | **BM25** (FastEmbed, chạy local) | — |
| Vector DB | **Qdrant** (local mode) | — |
| STT (giọng → text) | **Groq Whisper large-v3** | Groq |
| TTS (text → giọng) | **Edge TTS** (đa ngôn ngữ) | — (free, không key) |
| Đánh giá (RAGAS judge) | **Groq Llama 3.3 70B** | Groq |
| Backend API | **FastAPI** | — |
| Frontend | **React + Vite + TypeScript + Tailwind** (web VietGuide); bản đồ **Leaflet**, định tuyến **OSRM** | — |

→ **Chat / RAG / Vision phụ thuộc Gemini** (gồm cả embedding — đổi embedding thì phải build lại index). **Voice & judge dùng Groq + Edge TTS**, KHÔNG tốn quota Gemini. Đổi key nào trong `.env` cũng phải **restart app** mới có hiệu lực.

---

## Cách chạy

**Yêu cầu:** Python 3.11, file `.env` có `GEMINI_API_KEY` (bắt buộc) + `GROQ_API_KEY`, `WEATHERAPI_KEY` (tuỳ chọn cho voice/thời tiết). Sẵn có `qdrant_data/` (index) và `data/processed/` (30 điểm).

**1) Backend (FastAPI) — bắt buộc:**
```bash
# từ THƯ MỤC GỐC dự án (đường dẫn qdrant_data/, data/ là tương đối)
pip install -r requirements.txt
python -m src.api.main          # → http://127.0.0.1:8000  (API + phục vụ frontend)
```

**2) Frontend — chọn 1 trong 2:**
- **Web React VietGuide** (giao diện chính, đẹp): cần Node.js
  ```bash
  cd demo_VietGuide_AI-main
  npm install
  npm run dev                   # → http://localhost:5173  (gọi backend :8000)
  ```
  Hoặc build sẵn rồi để backend phục vụ luôn ở `:8000`: `npm run build`.
- **Web tĩnh** (`web/`, bản nhẹ không framework): backend tự phục vụ ở `http://127.0.0.1:8000`.

API docs ở `/docs`.

---

## Cấu trúc thư mục

Code đã tổ chức theo package `src/` (tách "lúc chạy" khỏi "chuẩn bị dữ liệu"):

```
src/
├── api/main.py            # FastAPI: /chat /stt /tts /locations + phục vụ Web UI
├── agents/                # 🧠 LÕI CHATBOT (lúc chạy)
│   ├── multi_agent.py     #   orchestrator + 8 agent + lập lịch trình + chi phí + ngữ cảnh
│   ├── weather.py         #   agent thời tiết (WeatherAPI)
│   └── voice.py           #   STT (Groq Whisper) + TTS (Edge TTS)
├── models/rag.py          # RAG Hướng 1 (MVP)
├── ingestion/             # 📦 CHUẨN BỊ DỮ LIỆU (chạy 1 lần, offline)
│   ├── collectors/        #   thu thập: wikipedia, wikidata, images, osm, routing...
│   └── processors/        #   xử lý: chunk_data, build_index, build_related_to, captions...
└── evaluation/            # 📊 RAGAS (eval_ragas, eval_report)
demo_VietGuide_AI-main/    # 🌐 Frontend chính: web React (Vite + TS + Tailwind)
│   └── src/pages/ChatPage.tsx  # trang chat: gọi /chat /tts /stt, bản đồ, GPS, lịch trình
web/                       # 🌐 Web tĩnh (bản nhẹ, không framework) — phương án phụ
data/processed/            # 30 địa điểm (đã thu thập)
qdrant_data/               # vector index (đã build)
```

> Script chuẩn bị dữ liệu chạy dạng module, vd: `python -m src.ingestion.collectors.wikipedia --all`.

---

## Tiến độ dự án

Kiến trúc **2 hướng dùng chung xương sống RAG**: **Hướng 1 — Multimodal RAG cơ bản** (MVP) → **Hướng 2 — + Multi-Agent** (nâng cao). **Cả 2 hướng đã chạy end-to-end** (text · ảnh · multi-agent). **Voice (STT/TTS) và Web UI đã hoàn thành.**

> **Cập nhật mới nhất:**
> - **8 agent** (thêm thời tiết, lập lịch trình nhiều ngày, lộ trình tham quan bên trong 1 địa điểm, **chi phí/ngân sách chuyến đi**), **ngữ cảnh hội thoại đa lượt** (nhớ địa điểm lượt trước), code chuyển sang package **`src/`**.
> - **Frontend chính: web React VietGuide** (`demo_VietGuide_AI-main/`, Vite + TS + Tailwind) — thay cho web tĩnh. Đã tích hợp với backend (chat, ảnh, giọng nói, trace multi-agent).
> - **Tích hợp thêm vào web React:**
>   - 📍 **GPS bản thân** — đo tuyến từ vị trí của bạn → địa điểm (OSRM: km + phút lái xe), kèm link Google Maps; fallback đường chim bay khi mất mạng.
>   - 🗑️ **Xóa hội thoại** hiển thị rõ ở mọi màn hình.
>   - 📝 **Render markdown** câu trả lời (heading, đậm, danh sách, bảng).
>   - 🔊 **TTS** đọc **đúng ngôn ngữ** (Việt/Anh), **tạo audio kèm câu trả lời** (nghe ngay khi text hiện ra), nút **bật/tắt** (bấm lại để dừng).
> - **Sửa lỗi:** TTS đọc sai ngôn ngữ · TTS bỏ markdown/emoji · `edge-tts` lỗi ngẫu nhiên ("No audio") → **tự thử lại** · `load_dotenv` không nạp key mới → tài liệu hoá phải restart backend.

### Phase 0 — Thu thập dữ liệu (30 địa điểm miền Bắc) — ✅ Cơ bản xong

| Dữ liệu | Trạng thái |
|---|---|
| Text VI (`full_text` / `summary`) | 30/30 ✅ |
| Text EN | 24/30 (6 nơi không có trang Wikipedia EN — xử lý đa ngôn ngữ ở tầng trả lời) |
| Kể chuyện (`story` / `fun_fact`) VI + EN | 30/30 ✅ |
| Tọa độ GPS | 30/30 ✅ |
| Ảnh tham chiếu | 30/30 ✅ |
| **Caption ảnh (nhận diện)** | **30/30 ✅** |
| Thực dụng (giờ/vé) | 20/30 + 10 `null` hợp lý |
| `related_to` (lộ trình) | 21/30 (9 nơi xa >50km để rỗng — không bịa) |

### Phase 1 — RAG base (Hướng 1, MVP) — ✅ Đã chạy end-to-end
- [x] Chunk + metadata + `type` + ID ổn định (`chunk_data.py`) — **967 chunk**
- [x] Embedding `gemini-embedding-001` (3072 chiều) + Vector store **Qdrant local** (`build_index.py`)
- [x] Retrieval **HYBRID** — dense (Gemini) + sparse BM25 (FastEmbed) + RRF (`build_hybrid_index.py`)
- [x] LLM trả lời **grounded** — hybrid retrieve → Gemini, không bịa, đa ngôn ngữ, có nguồn (`src/models/rag.py`)
- [x] **Đánh giá RAGAS** — Context Precision **0.707**, Faithfulness **0.931** (judge Groq độc lập) (`src/evaluation/eval_ragas.py`)
- [x] **Vision: ảnh → nhận diện → RAG kiểm chứng** (không để Vision tự quyết nội dung) — tích hợp trong `src/agents/multi_agent.py`

### Phase 2 — Multi-Agent (Hướng 2) — ✅ Đã chạy end-to-end (`src/agents/multi_agent.py`)
- [x] **Orchestrator** — 1 LLM call: phân loại smalltalk, phát hiện địa điểm, **phân rã** câu hỏi dài nhiều chủ đề thành các sub-task
- [x] **8 agent** chuyên trách, mỗi agent = 1 "lane" lọc đúng `type` / nguồn của mình:
  `info` (description) · `story` (storytelling + fun_fact) · `practical` (practical) · `route` (đọc `related_to`) · `weather` (WeatherAPI) · `itinerary` (lập lịch trình nhiều ngày) · `inner_tour` (lộ trình bên trong 1 địa điểm) · `budget` (chi phí/ngân sách chuyến đi)
- [x] **Parallel retrieval per type** — các lane retrieve **song song** (ThreadPoolExecutor), mỗi lane sạch (type filter + sub-query riêng) → **không cần rerank**
- [x] **Synthesizer** — gộp các context đã gán nhãn → 1 câu trả lời grounded, có nguồn, đúng ngôn ngữ
- [x] **Multimodal** — ảnh → Vision nhận diện `location_id` + mô tả + OCR → khóa location cho mọi lane
- [x] **Ngữ cảnh hội thoại đa lượt** — đưa lịch sử vào orchestrator/synthesizer + **carry-over location_id** (nhớ địa điểm lượt trước, vd "Văn Miếu có gì?" → "thế giờ mở cửa?") — không tốn thêm LLM call

### Phase 3 — Trải nghiệm — ✅ Backend + Voice + Web UI xong
- [x] **REST API (FastAPI)** — `src/api/main.py`: `POST /chat` (text + ảnh + history) → `{answer, sources, trace}`, kèm `/stt`, `/tts`, `/health`, `/locations`; phục vụ luôn Web UI tĩnh
- [x] **Voice (STT + TTS)** — `src/agents/voice.py`: STT **Groq Whisper** (free) + TTS **Edge TTS** (free, đa ngôn ngữ). **Không tốn quota Gemini.**
- [x] **Web React VietGuide** (`demo_VietGuide_AI-main/`) — **giao diện chính**: React + Vite + TS + Tailwind. Chat (text/ảnh/giọng nói), trace multi-agent, bản đồ, **localStorage**, render markdown, **GPS đo tuyến từ vị trí của tôi** (OSRM), **TTS đúng ngôn ngữ + tạo kèm câu trả lời + nút bật/tắt**, xóa hội thoại.
- [x] **Web tĩnh** (`web/`) — bản nhẹ không framework (Leaflet), phương án phụ; backend tự phục vụ.
- [x] **Agent lập lịch trình** (`itinerary`) — lập kế hoạch 2–3 ngày: chọn cụm điểm gần → **nearest-neighbor** xếp thứ tự → chia ngày + giờ/vé + thời tiết + gợi ý "nên mang gì". **Code tính toàn bộ con số** (haversine), LLM chỉ diễn đạt → không bịa.
- [x] **Agent lộ trình bên trong** (`inner_tour`) — tham quan **BÊN TRONG 1 địa điểm** (vd "trong Văn Miếu thăm gì", "tham quan Văn Miếu 1 tiếng đi đâu"): đọc `inner_tour` (các khu + thời gian gợi ý), **code chọn điểm theo thứ tự + cộng dồn thời gian, cắt vừa ngân sách giờ** (vd 60' → chọn 5/7 điểm, bỏ điểm vượt giờ), LLM diễn đạt thành tuyến. Khác `route` (đi giữa các điểm) và `itinerary` (nhiều ngày).
- [x] **Agent thời tiết** (`weather`) — `src/agents/weather.py`: WeatherAPI, dự báo theo toạ độ (30 điểm) hoặc tên địa danh; cache 30 phút.
- [x] **Agent chi phí / ngân sách** (`budget`) — ước tính tiền chuyến đi, **code tính số có cơ sở → LLM diễn đạt, không bịa**:
  - **2 chế độ:** (A) "đi N ngày tốn bao nhiêu" → bảng dự toán; (B) "có X tiền đi được mấy ngày/đâu" → bài toán ngược, code tìm số ngày vừa ngân sách (+ tự hạ mức nếu thiếu).
  - **Công thức:** vé (GIÁ THẬT từ `practical`, có nguồn) + đi lại (khoảng cách thật × giá/km tham khảo) + lưu trú + ăn (theo **mức** bình dân/trung bình/cao cấp).
  - **Chống bịa:** KHÔNG cào giá từng khách sạn (giá động, khó nguồn) mà dùng **mức chi/ngày** lưu kèm `nguồn` + `ngày cập nhật`; trả lời luôn ở dạng **khoảng (min–max)**, **gắn nhãn rõ phần THẬT vs ƯỚC LƯỢNG** và nêu cơ sở. Điểm thiếu giá vé → ghi rõ "chưa có", không tự chế.
  - **Đọc dữ liệu sẵn** (Mô hình "offline": thu thập 1 lần có nguồn → đọc lúc chạy), KHÔNG gọi web mỗi lần hỏi.

### Prototype đã thử
- `identify_location.py` — bản v0 nhận diện ảnh. Đã **nâng cấp & tích hợp** vào `multi_agent.py`: nhận diện theo **kiến thức của model trước** (tránh nhầm khi caption tham chiếu trùng đặc điểm chung), ép thứ tự suy luận "mô tả trước → kết luận sau", có **đường từ chối ảnh lạ** (ngưỡng tin cậy + validate id).

---

## Triển khai RAG pipeline (Phase 1 — đã chạy)

Luồng hỏi-đáp text end-to-end đã hoạt động: **câu hỏi → hybrid retrieve → LLM trả lời grounded có nguồn**.

### Các bước & script

| Bước | Script | Công nghệ | Kết quả |
|---|---|---|---|
| **Chunking** (structural) | `chunk_data.py` | Tách theo trường + mục, gắn `type` + metadata, ID ổn định | 967 chunk → `data/chunks.json` |
| **Embedding + Index** | `build_index.py` | `gemini-embedding-001` (3072 chiều) → Qdrant local; throttle + resume | 967/967 vào Qdrant |
| **Hybrid retrieval** | `build_hybrid_index.py` | dense (Gemini) + sparse BM25 (FastEmbed) + RRF fusion | tái dùng dense (0 quota) + BM25 local |
| **LLM trả lời** | `rag_answer.py` | hybrid retrieve → Gemini sinh câu trả lời | grounded, có nguồn, đa ngôn ngữ |

### Quyết định kỹ thuật (thực tế đã dùng)

- **Vector DB:** Qdrant **local mode** (`./qdrant_data`, không cần Docker) — Docker để dành lúc deploy.
- **Embedding:** `gemini-embedding-001` (đa ngôn ngữ → câu hỏi tiếng Việt vẫn tìm được chunk tiếng Anh). Free tier giới hạn **theo phút** → script tự **throttle + resume** (idempotent qua `uuid5`, chạy lại không trùng/không tốn lại quota).
- **Retrieval — HYBRID:** vector (ngữ nghĩa) + **BM25** (khớp tên riêng tiếng Việt như "Bút Tháp"), gộp bằng **RRF**. BM25 chạy **local** (không tốn quota Gemini).
- **Trả lời:** `gemini-2.5-flash-lite`, prompt ép **chỉ dùng ngữ cảnh** (chống bịa) → thiếu data thì nói "chưa có thông tin chắc chắn"; trả lời đúng ngôn ngữ câu hỏi; kèm nguồn.
- **Đa ngôn ngữ:** xử lý ở **tầng trả lời** (LLM đọc chunk tiếng Việt → đáp theo ngôn ngữ user), KHÔNG lưu sẵn EN cho mọi địa điểm.

> Lưu ý: bản triển khai hiện dùng **Gemini + Qdrant + FastEmbed trực tiếp** (chưa qua LlamaIndex / Claude như bảng Tech Stack — đó là target khi nâng cấp).

### Chunking — phân loại `type` (cho multi-agent sau)

| Trường gốc → chunk | `type` | Agent dùng (Phase 2) |
|---|---|---|
| summary / full_text (tách mục) | `description` | Kể chuyện & Q&A |
| story | `storytelling` | Kể chuyện |
| fun_fact | `fun_fact` | Kể chuyện |
| practical | `practical` | Thông tin thực dụng |
| image_caption | `image` | Vision |

→ Mỗi agent (Phase 2) lọc đúng `type` của mình bằng metadata filter trên Qdrant.

---

## Đánh giá chất lượng (RAGAS)

Đánh giá RAG bằng **RAGAS**, **judge = Groq Llama 3.3 70B** (khác nhà cung cấp với hệ thống Gemini → đánh giá **độc lập**, tránh self-bias). Test set **12 câu** (mô tả / thực dụng / kể chuyện / EN / chống bịa).

### Kết quả (`eval_ragas.py` → `data/bao_cao_eval.md`)

| Metric | Điểm | Ý nghĩa |
|---|---|---|
| **Context Precision** (retrieval) | **0.707** | Chunk lấy về liên quan ở mức khá |
| **Faithfulness** (chống bịa) | **0.931** | Trả lời bám dữ liệu, gần như không bịa |

**Theo loại câu** — retrieval mạnh ở mô tả, **yếu ở thực dụng (giờ/vé)**:

| Loại câu | Context Precision |
|---|---|
| Mô tả | ~1.000 ✅ |
| Kể chuyện | 0.722 ✅ |
| Thực dụng (giờ/vé) | **0.20–0.33** ⚠️ |

### Insight: cần metadata filter `type` (chứng minh bằng số)

Câu thực dụng precision thấp vì hybrid lấy lẫn nhiều loại chunk. Bật **lọc `type=practical`**  sửa được:

| Câu "Bảo tàng mở cửa mấy giờ?" | Tỉ lệ chunk đúng loại | Vị trí chunk giờ/vé |
|---|---|---|
| **KHÔNG lọc** (Hướng 1) | 0.17 (1/6) | #5 (bị chôn) |
| **CÓ lọc `type=practical`** (Hướng 2) | **1.00** (6/6) | **#1** (lên top) |

→ Eval **chứng minh giá trị của metadata filter** — đúng cơ chế **agent thông tin thực dụng (Hướng 2)** lọc `type` của mình; cũng xác nhận quyết định **giữ `type` lúc chunking** là đúng.

> **Methodology:** judge khác nhà cung cấp với hệ thống → tránh self-preference bias. Eval chấm **từng lượt + lưu ngay** → **resume-able** khi hết token Groq (đổi key chạy tiếp).

### Đánh giá mở rộng (A/B + vận hành) — mới

Pipeline mở rộng so sánh **Hướng 1 (RAG)** với **Hướng 2 (Multi-Agent)** trên cùng 48 câu hỏi + đo vận hành:

```bash
# Windows
pwsh scripts/run_full_eval.ps1
# Linux/Mac
bash scripts/run_full_eval.sh
```

Output: `data/bao_cao_so_sanh.md` (5 mục: tổng quan / theo nhóm / routing / vận hành / kết luận).

Judge = Groq Llama 3.3 70B (độc lập Gemini). Có throttle + resume khi hết quota.

---

## Triển khai Multi-Agent (Hướng 2 — đã chạy)

Eval ở trên đã **chứng minh bằng số** rằng lọc `type` sửa được lỗi retrieve lẫn loại. Hướng 2 (`multi_agent.py`) hiện thực hóa điều đó: mỗi agent là một **"lane" retrieval sạch**, chỉ lọc đúng `type` của mình.

### Luồng xử lý

```
[ảnh?] → Vision (nhận diện location_id + mô tả + OCR)
      → Orchestrator (1 LLM call: smalltalk? + địa điểm? + PHÂN RÃ câu hỏi)
      → N lane chạy SONG SONG, mỗi lane lọc đúng type (+ khóa location)
      → Synthesizer (gộp context đã gán nhãn → 1 câu trả lời grounded)
```

### Các quyết định kỹ thuật

- **Classifier + phân rã (Orchestrator):** prompt dài nhiều chủ đề (vd *"Văn Miếu mở mấy giờ, vé bao nhiêu, có giai thoại gì?"*) được **tách thành nhiều sub-task**, mỗi sub-task có truy vấn riêng đi vào đúng 1 lane → retrieve sắc, không nhiễu chéo.
- **Parallel retrieval per type:** các lane retrieve **đồng thời** (ThreadPoolExecutor). Qdrant local không thread-safe → bọc query trong lock; phần chậm (gọi embedding mạng) vẫn song song.
- **8 agent:** `info` (description) · `story` (storytelling + fun_fact) · `practical` (practical) · `route` (đọc thẳng `related_to`, không cần Qdrant) · `weather` (WeatherAPI theo toạ độ/tên) · `itinerary` (lập lịch trình nhiều ngày) · `inner_tour` (lộ trình tham quan bên trong 1 địa điểm, đọc thẳng `inner_tour`) · `budget` (chi phí chuyến đi: vé thật + đi lại + ăn ở ước lượng có nguồn).
- **Agent lập lịch trình (`itinerary`) — code tính số, LLM diễn đạt:** để con số luôn đúng (không để LLM bịa), **code tự tính** bằng *haversine* + *nearest-neighbor*: chọn cụm điểm gần origin → xếp thứ tự thăm → chia theo ngày → tính tổng quãng; gộp giờ/vé (từ `practical`) + dự báo thời tiết. LLM (Lớp 2) **chỉ diễn đạt** thành lịch trình, xếp Sáng/Chiều theo giờ mở cửa, gợi ý "nên mang gì" suy từ thời tiết thật; thiếu data thì nói rõ "chưa có", không bịa.
- **Ngữ cảnh hội thoại:** đưa vài lượt gần nhất vào orchestrator + **carry-over location_id** — câu nối tiếp thiếu địa điểm ("thế giờ mở cửa?") vẫn hiểu đúng nơi đang nói, **không tốn thêm LLM call**.
- **Multimodal:** Vision **chỉ xác định danh tính** (location_id) + mô tả + OCR; **nội dung trả lời do RAG kiểm chứng** (Vision không tự quyết). Nhận diện dựa trên **kiến thức của model trước**, rồi mới tra vào danh sách 30 điểm — tránh nhầm khi caption tham chiếu trùng đặc điểm chung (vd tháp đá chùa ↔ tháp bát giác bảo tàng).
- **Smalltalk:** chào hỏi / cảm ơn / ngoài phạm vi → trả lời hội thoại, **bỏ qua retrieve, không gắn nguồn**.
- **Ngôn ngữ:** phát hiện theo **ký tự dấu tiếng Việt** (đáng tin với câu ngắn) → ép trả lời đúng ngôn ngữ câu hỏi.

### Vì sao KHÔNG dùng rerank?

Vấn đề của hệ thống là **"type confusion"** (retrieve lẫn loại chunk), KHÔNG phải sai thứ tự. Rerank chỉ **sắp lại 1 pool đã nhiễu** → vẫn nhiễu. **Type filter loại nhiễu TỪ ĐẦU**, mỗi lane sạch sẵn → đúng bài toán hơn rerank. (Rerank chỉ có ích khi cần sắp xếp trong *cùng một loại* — không phải vấn đề ở đây.)

### Phục vụ qua API

`src/api/main.py` (FastAPI) bọc pipeline thành REST, đồng thời phục vụ Web UI tĩnh:

| Endpoint | Chức năng |
|---|---|
| `GET /` | Web UI (chat) |
| `POST /chat` | `question` (+ ảnh + `history` + `last_location_id`) → `{answer, sources, trace}` |
| `POST /stt` | `audio` → `{text, language}` (Groq Whisper) |
| `POST /tts` | `{text, lang?}` → audio mp3 (Edge TTS) |
| `GET /health` | trạng thái + số địa điểm + danh sách agent |
| `GET /locations` | 30 địa điểm kèm toạ độ + ảnh (cho bản đồ) |

`trace` trả về toàn bộ bước (Vision → Orchestrator → các lane + thời gian, kèm khung lịch trình nếu có) để client hiển thị "trợ lý đã xử lý thế nào".

---

## Chiến lược thu thập dữ liệu

### Tổng quan

| Dạng dữ liệu | Nguồn chính | Agent sử dụng |
|---|---|---|
| Kể chuyện | Wikipedia + tự biên tập | Answer Agent |
| Mô tả / Q&A | Wikipedia + Wikidata | Retrieval + Answer |
| Thực dụng | Web search nguồn chính thức (kèm source_url) | Answer Agent |
| Lộ trình | Sơ đồ + OpenStreetMap | Route Agent |
| Ảnh tham chiếu | Wikipedia Commons | Vision Agent |
| Tiếng Anh | Wikipedia EN | Answer Agent |

---

### 1. Kể chuyện
**Nguồn:** Wikipedia (mục Lịch sử, Văn hóa) → tự biên tập lại giọng kể

**Thu thập:** Lịch sử hình thành, ý nghĩa văn hóa, giai thoại, nhân vật liên quan

**Ví dụ chunk:**
```
"Bia Tiến Sĩ được dựng năm 1484 theo lệnh vua Lê Thánh Tông, ghi danh
1304 vị tiến sĩ qua 82 khoa thi. Điều ít người biết là mỗi tấm bia đặt
trên lưng rùa đá — biểu tượng cho sự trường tồn của tri thức..."
```

---

### 2. Mô tả / Q&A
**Nguồn:** Wikipedia (mô tả chính) + Wikidata (năm, tọa độ, kiến trúc sư)

**Thu thập:** Mô tả tổng quan, kích thước, chất liệu, năm xây dựng, FAQ

**Ví dụ chunk:**
```
"Khuê Văn Các là lầu vuông 2 tầng, xây năm 1805. Tầng trên có 4 cửa
sổ tròn tượng trưng cho sao Khuê — ngôi sao chủ về văn chương."
```

---

### 3. Thực dụng (dữ liệu động)
**Nguồn:** Web search từ trang chính thức / uy tín (kèm `source_url`)

**Thu thập:** Giờ mở cửa, giá vé, SĐT, website, địa chỉ

**Lưu ý:** Mỗi địa điểm gắn `source_url` để truy nguồn và cập nhật — giá vé/giờ thay đổi thường xuyên. Trường nào không có nguồn tin cậy → để `null`, **không bịa**.

**Ví dụ chunk:**
```
"Văn Miếu mở cửa mùa nóng 07:30–17:30, mùa lạnh 08:00–17:00.
Vé: người lớn 70.000đ, HS-SV 35.000đ, trẻ dưới 16 tuổi miễn phí.
Nguồn: vanmieu.gov.vn"
```

---

### 4. Lộ trình
**Nguồn:** Sơ đồ khu tham quan + OpenStreetMap (overpass-turbo.eu)

**Thu thập:** Khoảng cách giữa các điểm, thứ tự tham quan, tuyến ngắn / đầy đủ

**Ví dụ chunk:**
```
"Tuyến 30 phút: Cổng chính → Hồ Văn → Bia Tiến Sĩ → Khuê Văn Các →
Cổng ra. Phù hợp khi thời gian hạn chế, bao phủ các điểm quan trọng nhất."
```

---

### 5. Ảnh tham chiếu
**Nguồn:** Wikimedia Commons (CC license) + chụp thực tế

**Thu thập:** 1–3 ảnh/địa điểm, caption mô tả chi tiết

**Lưu ý:** RAG tìm theo caption, không theo pixel — caption rõ quan trọng hơn số lượng ảnh

**Ví dụ caption:**
```
"Bia Tiến Sĩ Văn Miếu — 82 tấm bia đá đặt trên lưng rùa, nhìn từ
phía Nam, chụp ban ngày, nền trời xanh."
```

---

### 6. Tiếng Anh
**Nguồn:** Wikipedia EN (en.wikipedia.org) + tự dịch phần không có sẵn

**Thu thập:** Bản tiếng Anh của tất cả các chunk trên

**Lưu ý:** Lưu cùng metadata, chỉ khác trường `"language": "en"`

---

### Cấu trúc metadata mỗi chunk

```json
{
  "id": "van_mieu_bia_tien_si_vi",
  "type": "storytelling",
  "name": "Bia Tiến Sĩ",
  "location": "Văn Miếu - Quốc Tử Giám",
  "content": "...",
  "related_to": ["dai_thanh", "khue_van_cac"],
  "language": "vi",
  "source": "https://vi.wikipedia.org/wiki/Bia_tiến_sĩ_Văn_Miếu",
  "last_updated": "2026-06-06"
}
```

---

## Thực tế đã làm — Scripts & APIs

### Kết quả tổng

| Loại dữ liệu | Script | API / Tool | Kết quả |
|---|---|---|---|
| Text Wikipedia | `fetch_wikipedia.py` | wikipedia-api | 30/30 ✅ |
| Tọa độ GPS | `fetch_wikidata_coords.py` | Wikipedia API + Wikidata SPARQL | 30/30 ✅ |
| Nội dung viết lại | `rewrite_content.py` | Google Gemini 2.5 Flash | 30/30 ✅ |
| Ảnh tham chiếu | `fetch_images.py` + `fetch_images_missing.py` | Wikimedia Commons API | 30/30 ✅ |
| Thực dụng | `fill_practical_curated.py` | Web search nguồn chính thức | 20/30 có giờ/vé + 10 null hợp lý ✅ |
| Caption ảnh | `generate_captions.py` | Google Gemini 2.5 Flash-Lite Vision | 30/30 ✅ |
| Lộ trình | `build_related_to.py` | OSRM Table API | 21/30 (9 nơi xa >50km để rỗng, không bịa) |

---

### 1. Text Wikipedia — `fetch_wikipedia.py`
**API:** `wikipedia-api` (Python library)

Gọi Wikipedia tiếng Việt + tiếng Anh cho 30 địa điểm. Lấy `summary` và `full_text` của từng trang. Dùng `time.sleep(0.5)` giữa các request để tránh bị block.

**Output:** `data/raw/<id>.json` — chứa `summary_vi`, `full_text_vi`, `summary_en`, `full_text_en`

---

### 2. Tọa độ GPS — `fetch_wikidata_coords.py`
**API:** Wikipedia API (batch) → Wikidata SPARQL → Nominatim (OSM)

3 bước cascade, mỗi bước chỉ gọi API **1 lần** cho tất cả địa điểm:
- **Bước 1:** Gửi 30 tên tiếng Việt cùng lúc → Wikipedia API trả về Wikidata ID
- **Bước 2:** Fallback: gửi tên tiếng Anh cho các địa điểm còn thiếu
- **Bước 3:** Wikidata SPARQL lấy tọa độ GPS từ tất cả IDs tìm được

Tổng cộng chỉ **3 lần gọi API** thay vì 60 lần.

**Output:** Điền `coordinates` và `wikidata_id` vào từng file JSON

---

### 3. Nội dung viết lại — `rewrite_content.py`
**API:** Google Gemini 2.5 Flash (miễn phí 20 request/ngày)

Đọc `summary_vi` từ Wikipedia → prompt Gemini viết lại theo giọng hướng dẫn viên → trả JSON gồm 4 trường.

**Prompt yêu cầu trả về JSON:**
```json
{
  "story_vi": "2-3 đoạn kể chuyện tiếng Việt",
  "fun_fact_vi": "1 điều thú vị ít người biết",
  "story_en": "English storytelling version",
  "fun_fact_en": "English fun fact"
}
```

**Output:** `data/processed/<id>.json` — merge với data gốc

---

### 4. Ảnh tham chiếu — `fetch_images.py` + `fetch_images_missing.py`
**API:** Wikipedia pageimages API + Wikimedia Commons Search API

- **Script 1:** Batch 30 địa điểm → Wikipedia trả về URL ảnh đại diện của từng trang → download về `data/images/`
- **Script 2:** 7 địa điểm không có ảnh Wikipedia → tìm trên Wikimedia Commons bằng từ khoá tiếng Anh

Dùng thumbnail (1200px) thay vì ảnh gốc để tránh file quá nặng và bị timeout.

**Output:** `data/images/<id>.jpg` + điền `image_url`, `image_path` vào JSON

---

### 5. Thực dụng — `fill_practical_curated.py`
**Nguồn:** Web search từ trang chính thức/uy tín, kèm `source_url`. **Dữ liệu cuối cùng 100% từ web search.**

**Vì sao không dùng Google Places API:** Google Maps **bắt buộc có billing account active** mới gọi được (kể cả phần free). Thẻ ghi nợ kẹt ở bước nạp cọc, tài khoản bị Google khóa billing (lỗi `OR_BACR2_44`) → mọi request trả về `403`. Ngoài ra Google Places **không trả về giá vé tham quan** (chỉ có `priceLevel` $-$$$$ cho hàng quán). Nên chuyển sang **web search**: chính xác hơn cho danh thắng nổi tiếng, **có giá vé**, có nguồn dẫn chứng, 0 đồng.

**Cách làm:** `fill_practical_curated.py` điền dữ liệu tra từ web chính thức (vanmieu.gov.vn, hoangthanhthanglong.vn, baotanglichsu.vn, trangandanhthang.vn...) vào 30 file, mỗi điểm kèm `source_url`.

> **Vì sao không dùng OSM:** Bước thử ban đầu dùng OSM Overpass API hay **vớ nhầm POI bên cạnh** (vd Văn Miếu → Bảo tàng Mỹ thuật; khách sạn/cửa hàng đặt tên theo địa danh) → dữ liệu dễ sai. Vì vậy dự án **chuyển hẳn sang web search** có nguồn dẫn chứng. (Script OSM thử nghiệm đã được gỡ bỏ.)

**Schema `practical` thống nhất:**
```json
{
  "opening_hours": "Mùa nóng 07:30–17:30; mùa lạnh 08:00–17:00",
  "ticket_price": "Người lớn 70.000đ; HS-SV 35.000đ; trẻ dưới 16 tuổi miễn phí",
  "phone": null,
  "website": "http://vanmieu.gov.vn",
  "address": null,
  "note": null,
  "source_url": "http://vanmieu.gov.vn/vi/tham-quan/huong-dan/"
}
```

**Kết quả:** 20/30 có giờ mở cửa + giá vé thật (kèm nguồn). 10 còn lại để `null` + `note`:
- 8 **vùng/tự nhiên** (Hồ Tây, Hồ Hoàn Kiếm, Sa Pa, Phố cổ HN, Đồng Văn, Mù Cang Chải, Mã Pì Lèng, Bạch Long Vĩ) — khu vực mở, không có giờ/vé cố định.
- 2 **chưa có nguồn vé/giờ chính thức** (Chùa Bút Tháp, Làng tranh Đông Hồ) — có địa chỉ + ghi chú rõ.

**Output:** Field `practical` (schema trên) trong từng file `data/processed/<id>.json`

---

### 6. Lộ trình — `build_related_to.py`
**API:** OSRM Table API (miễn phí, không cần key)

Gửi tọa độ 30 địa điểm → OSRM tính ma trận khoảng cách 30×30 (đường bộ thực tế, tính bằng km và phút) → **1 lần gọi API duy nhất**.

Địa điểm nào trong vòng **50km đường bộ** thì được thêm vào `related_to`.

```json
"related_to": [
  { "id": "den_ngoc_son", "name": "Đền Ngọc Sơn", "distance_km": 0.5, "duration_min": 1 },
  { "id": "nha_tho_lon",  "name": "Nhà thờ Lớn",  "distance_km": 1.0, "duration_min": 3 }
]
```

**Kết quả:** 21/30 địa điểm có `related_to`. **9 nơi xa biệt lập** (Sa Pa, Điện Biên, Hạ Long, Cát Bà, Bạch Long Vĩ, Đền Hùng, Mù Cang Chải, Yên Tử, Xuân Sơn) cách mọi điểm khác >50km → để **rỗng**, đúng thực tế (không có điểm gần đáng kể). Đã thử bù bằng haversine (`fill_related_to.py`) nhưng **gỡ bỏ** vì tọa độ là 1 điểm đại diện cho cả 1 vùng → khoảng cách suy ra là "chính xác giả" → vi phạm quy tắc không-bịa. Nếu cần proximity cho 9 nơi này, sẽ tính lúc chạy + ghi rõ "ước lượng".

**Output:** Điền `related_to` vào từng file JSON

---

### 7. Caption ảnh — `generate_captions.py`
**API:** Google Gemini 2.5 Flash-Lite Vision (free tier, quota cao hơn `flash`)

Sinh `image_caption` cho 30 ảnh để phục vụ **nhận diện hình ảnh**. Hai lớp chống đọc sai:
- **Đưa sẵn tên địa điểm** cho model → khỏi đoán danh tính → hết nhận nhầm
- **Ép "chỉ tả cái NHÌN THẤY"**, cấm thêm kiến thức ngoài → không bịa

Model tự chấm `image_clarity` (ro / mo_xa / khong_dac_trung) và `image_needs_review`. Có **cache skip** (ảnh đã có caption thì bỏ qua) + logic **dừng hẳn khi hết quota** (không retry vô ích).

**Ví dụ caption sinh ra:**
```json
{
  "image_caption": "Ảnh chụp toàn cảnh vịnh với nhiều đảo đá vôi xanh mướt nhô lên khỏi mặt nước màu xanh ngọc bích và nhiều thuyền du lịch.",
  "image_clarity": "ro",
  "image_needs_review": false
}
```

**Kết quả:** 30/30 ảnh có caption, không ảnh nào bị đánh dấu cần xem lại. **Soát chất lượng:** `review_captions.py` tạo trang HTML hiện ảnh kèm caption để kiểm bằng mắt.

**Output:** Field `image_caption`, `image_clarity`, `image_needs_review` trong từng file `data/processed/<id>.json`

---

### Nguyên tắc chất lượng

- Đối chiếu ít nhất 2 nguồn cho mỗi dữ kiện lịch sử
- Tách dữ liệu tĩnh (lịch sử) và động (giá vé, giờ) để dễ cập nhật
- Mỗi chunk = 1 ý hoàn chỉnh, khoảng 150–300 chữ
- Biên tập Wikipedia từ giọng bách khoa sang giọng kể chuyện trước khi đưa vào RAG

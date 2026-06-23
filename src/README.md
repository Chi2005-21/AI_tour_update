# Cấu trúc source code

```text
src/
├── agents/                 # Orchestrator và các agent nghiệp vụ
├── api/                    # FastAPI routes và request adapters
├── core/                   # Config, constants, exceptions
├── evaluation/             # Chỗ đặt benchmark production đã gán nhãn
├── ingestion/
│   ├── collectors/         # Wikipedia, Wikidata, OSM, ảnh, routing
│   └── processors/         # Làm sạch, chunking, caption, graph extraction
├── models/                 # Contract dùng chung
├── rag/
│   ├── embeddings/         # Embedding provider adapters
│   ├── generation/         # OpenRouter/OpenAI answer generators
│   ├── repositories/       # Adapter đọc dữ liệu production
│   ├── retrieval/          # Lexical, Qdrant và hybrid retrieval
│   ├── vectorstores/       # Qdrant storage adapter
│   └── pipeline.py         # Context, citation và câu trả lời
└── main.py                 # CLI
```

## Ranh giới phụ thuộc

```text
api -> agents -> rag -> repositories -> data/processed
             -> models

ingestion -> data/raw, data/processed, data/graph
evaluation -> rag/agents
core -> được dùng bởi mọi layer
```

- Runtime chỉ đọc dữ liệu production qua `ProcessedDataRepository`.
- `data/processed` là nguồn hiện tại; repository không ghi ngược vào dữ liệu.
- Dữ liệu graph production nên được sinh sang `data/graph`, không nhét kết quả
  suy luận trở lại file nguồn.
- Thiết kế Graph RAG chi tiết nằm trong `docs/GRAPH_RAG_DATA.md`.

## Lệnh hiện tại

```powershell
python -m src.main index --tao-lai
python -m src.main query "Bia Tiến sĩ có ý nghĩa gì?" --khong-sinh
python -m unittest discover -s tests -v
```

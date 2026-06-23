"""Điểm chạy chính cho RAG pipeline và ứng dụng sau này (Multimodal + Multi-Agent)."""

from __future__ import annotations

import argparse
import sys
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def parse_filters(values: list[str]) -> dict[str, Any]:
    filters: dict[str, Any] = {}
    for value in values:
        if "=" not in value:
            raise argparse.ArgumentTypeError(
                f"Filter phải có dạng khóa=giá_trị, nhận được: {value}"
            )
        key, filter_value = value.split("=", 1)
        filters[key.strip()] = filter_value.strip()
    return filters


def run_query(args: argparse.Namespace) -> int:
    import src.agents.multi_agent as ma
    ma.setup()
    try:
        image_path = getattr(args, "image", None)
        text, sources, trace = ma.answer(args.cau_hoi, image_path=image_path, verbose=not args.json)
    except Exception as exc:
        print(f"Lỗi: {exc}", file=sys.stderr)
        return 2

    if args.json:
        import json
        print(json.dumps({"answer": text, "sources": sources, "trace": trace}, ensure_ascii=False, indent=2))
        return 0

    print(f"\nCâu trả lời:")
    print(text)
    if sources:
        print("\nTrích dẫn:")
        for source in sources:
            print(f"- {source}")
    return 0


def run_index(args: argparse.Namespace) -> int:
    from src.ingestion.processors.build_index import main as build_dense_index
    from src.ingestion.processors.build_hybrid_index import main as build_hybrid_index

    print("--- 1. Xây dựng Dense Index ---")
    try:
        build_dense_index()
    except Exception as exc:
        print(f"Lỗi xây dựng dense index: {exc}", file=sys.stderr)
        return 2

    print("\n--- 2. Nâng cấp lên Hybrid Index (BM25) ---")
    try:
        build_hybrid_index()
    except Exception as exc:
        print(f"Lỗi nâng cấp hybrid index: {exc}", file=sys.stderr)
        return 2

    return 0


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="RAG pipeline cho AI Trợ lý Hướng dẫn viên Du lịch Ảo (Multimodal & Multi-Agent)."
    )
    subparsers = parser.add_subparsers(dest="lenh", required=True)

    query_parser = subparsers.add_parser(
        "query",
        help="Truy xuất context cho một câu hỏi.",
    )
    query_parser.add_argument("cau_hoi", help="Câu hỏi cần truy xuất.")
    query_parser.add_argument("--image", default=None, help="Đường dẫn ảnh đính kèm (Vision).")
    query_parser.add_argument("--ngon-ngu", default="vi", choices=["vi", "en"])
    query_parser.add_argument(
        "--filter",
        action="append",
        default=[],
        help="Metadata filter dạng khóa=giá_trị; có thể truyền nhiều lần.",
    )
    query_parser.add_argument("--top-k", type=int, default=5)
    query_parser.add_argument("--diem-toi-thieu", type=float, default=0.4)
    query_parser.add_argument(
        "--retriever",
        choices=["hybrid", "qdrant", "lexical"],
        default="hybrid",
    )
    query_parser.add_argument(
        "--khong-sinh",
        action="store_true",
        help="Chỉ truy xuất context, không gọi LLM sinh câu trả lời.",
    )
    query_parser.add_argument("--json", action="store_true")
    query_parser.set_defaults(handler=run_query)

    index_parser = subparsers.add_parser(
        "index",
        help="Tạo embedding và index tài liệu vào Qdrant.",
    )
    index_parser.add_argument(
        "--tao-lai",
        action="store_true",
        help="Xóa collection cũ trước khi index.",
    )
    index_parser.add_argument("--batch-size", type=int, default=64)
    index_parser.set_defaults(handler=run_index)

    return parser


def main() -> int:
    parser = create_parser()
    args = parser.parse_args()
    try:
        return args.handler(args)
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        print(f"Lỗi: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

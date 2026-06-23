"""Adapter Hướng 1 (RAG đơn) — wrap src.models.rag_h1.answer() cho eval framework.

Bỏ qua image_path và history (Hướng 1 không hỗ trợ) để so sánh công bằng với Hướng 2.
"""
from __future__ import annotations

import sys
from typing import Any

sys.stdout.reconfigure(encoding="utf-8")

from src.models import rag_h1


def run(question: str, image_path: str | None = None, history: list | None = None) -> dict:
    """Chạy RAG Hướng 1 cho 1 câu. image_path/history bị bỏ qua (không hỗ trợ)."""
    out = rag_h1.answer(question)
    return {
        "system": "huong1",
        "question": question,
        "answer": out["answer"],
        "contexts": out["contexts"],
        "sources": out["sources"],
    }

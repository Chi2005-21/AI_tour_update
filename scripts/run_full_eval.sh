#!/usr/bin/env bash
# Chạy toàn bộ pipeline eval. Usage: bash scripts/run_full_eval.sh
set -euo pipefail
cd "$(dirname "$0")/.."

echo "[1/4] Tạo data Hướng 1 (RAG)..."
.venv/bin/python -m src.evaluation.eval_ragas h1

echo "[2/4] Tạo data Hướng 2 (Multi-Agent)..."
.venv/bin/python -m src.evaluation.eval_ragas h2

echo "[3/4] Chạy perf instrumentation..."
.venv/bin/python -m src.evaluation.eval_perf

echo "[4/4] Sinh báo cáo..."
.venv/bin/python -m src.evaluation.eval_compare

echo "Xong. Mở data/bao_cao_so_sanh.md"
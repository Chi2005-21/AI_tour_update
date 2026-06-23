# Chạy toàn bộ pipeline eval: produce data H1 + H2, chấm RAGAS, đo perf, sinh báo cáo.
# Usage: pwsh scripts/run_full_eval.ps1
# Yêu cầu: GEMINI_API_KEY, GROQ_API_KEY đã có trong .env

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

Write-Host "[1/4] Tạo data Hướng 1 (RAG)..."
& .venv/Scripts/python.exe -m src.evaluation.eval_ragas h1

Write-Host "[2/4] Tạo data Hướng 2 (Multi-Agent)..."
& .venv/Scripts/python.exe -m src.evaluation.eval_ragas h2

Write-Host "[3/4] Chạy perf instrumentation..."
& .venv/Scripts/python.exe -m src.evaluation.eval_perf

Write-Host "[4/4] Sinh báo cáo..."
& .venv/Scripts/python.exe -m src.evaluation.eval_compare

Write-Host "Xong. Mở data/bao_cao_so_sanh.md"
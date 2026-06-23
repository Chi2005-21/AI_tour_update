@echo off
REM Bật backend FastAPI đúng môi trường (vdk1) — double-click để chạy.
REM Giữ cửa sổ này MỞ trong khi dùng web. Bấm Ctrl+C hoặc đóng cửa sổ để tắt.
cd /d "%~dp0"
echo === Dang khoi dong backend (vdk1) tai http://127.0.0.1:8000 ===
"C:\Users\FPT\anaconda3\envs\vdk1\python.exe" -m src.api.main
echo.
echo === Backend da dung. Neu thay loi o tren, doc dong loi roi bao lai. ===
pause

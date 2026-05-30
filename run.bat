@echo off
echo === Instagram Monitor Bot ===
echo.

REM Kiểm tra Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [LOI] Python chua duoc cai dat!
    echo Tai Python tai: https://www.python.org/downloads/
    pause
    exit
)

REM Cài thư viện nếu chưa có
echo [1/2] Cai dat thu vien...
pip install -r requirements.txt -q

echo [2/2] Khoi dong bot...
echo.
python bot.py

pause

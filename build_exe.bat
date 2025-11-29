@echo off
REM Build LightClip v1.9 EXE using PyInstaller (單 EXE)

REM 安裝依賴：
REM   pip install -r requirements.txt
REM   pip install pyinstaller

pyinstaller ^
 --noconfirm ^
 --windowed ^
 --onefile ^
 --name "LightClip_v1_9" ^
 --add-data "assets;assets" ^
 --add-data "languages;languages" ^
 --add-data "docs;docs" ^
 main.py

echo.
echo 構建完成，請到 dist\ 內查看 LightClip_v1_9.exe。
pause

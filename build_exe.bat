@echo off
REM Build LightClip v1.8 EXE using PyInstaller (單 EXE)

REM 安裝依賴：
REM   pip install -r requirements.txt pyinstaller

pyinstaller ^
 --noconfirm ^
 --windowed ^
 --onefile ^
 --name "LightClip_v1_8" ^
 --add-data "assets;assets" ^
 --add-data "languages;languages" ^
 --add-data "docs;docs" ^
 main.py

echo.
echo 構建完成，請到 dist\ 內查看 LightClip_v1_8.exe。
pause

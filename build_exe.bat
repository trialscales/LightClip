@echo off
REM Build LightClip v1.7 EXE using PyInstaller
REM 先安裝依賴： pip install -r requirements.txt pyinstaller

pyinstaller ^
 --noconfirm ^
 --windowed ^
 --name "LightClip_v1_7" ^
 --add-data "assets;assets" ^
 --add-data "languages;languages" ^
 --add-data "docs;docs" ^
 main.py

echo.
echo 構建完成，請到 dist\LightClip_v1_7\ 內查看 EXE。
pause

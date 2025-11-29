@echo off
REM Build LightClip v1.6.1a EXE using PyInstaller
REM 確保已在虛擬環境中並安裝： pip install -r requirements.txt pyinstaller

pyinstaller ^
 --noconfirm ^
 --windowed ^
 --name "LightClip_v1_6_1a" ^
 --add-data "assets;assets" ^
 --add-data "languages;languages" ^
 --add-data "docs;docs" ^
 main.py

echo.
echo 構建完成，請到 dist\LightClip_v1_6_1a\ 內查看 EXE。
pause

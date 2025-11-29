@echo off
REM Build LightClip v1.6 EXE using PyInstaller
pyinstaller --noconfirm --onefile --windowed --name "LightClip_v1_6" main.py
pause

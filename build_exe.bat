
@echo off
echo Building LightClip v1.3 EXE...

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

pyinstaller LightClip.spec

echo.
echo Build finished.
echo EXE 在 dist\LightClip\LightClip.exe
pause

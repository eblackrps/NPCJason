@echo off
echo === NPCJason EXE Build ===
echo.

echo [1/3] Installing dependencies...
pip install pyinstaller pystray Pillow --quiet
if errorlevel 1 (
    echo ERROR: pip install failed. Make sure Python is on PATH.
    pause
    exit /b 1
)

echo [2/3] Generating icon...
python generate_icon.py
if errorlevel 1 (
    echo ERROR: Icon generation failed.
    pause
    exit /b 1
)

echo [3/3] Building EXE with PyInstaller...
pyinstaller npcjason.spec --clean --noconfirm
if errorlevel 1 (
    echo ERROR: PyInstaller build failed.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Build complete: dist\NPCJason.exe
echo ============================================
echo.
pause

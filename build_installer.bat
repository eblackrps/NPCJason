@echo off
echo === NPCJason Full Build (EXE + Installer) ===
echo.

echo [1/4] Installing dependencies...
pip install pyinstaller pystray Pillow --quiet
if errorlevel 1 (
    echo ERROR: pip install failed. Make sure Python is on PATH.
    pause
    exit /b 1
)

echo [2/4] Generating icon...
python generate_icon.py
if errorlevel 1 (
    echo ERROR: Icon generation failed.
    pause
    exit /b 1
)

echo [3/4] Building EXE with PyInstaller...
pyinstaller npcjason.spec --clean --noconfirm
if errorlevel 1 (
    echo ERROR: PyInstaller build failed.
    pause
    exit /b 1
)

echo [4/4] Building installer with Inno Setup...
set ISCC=
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe
) else if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set ISCC=C:\Program Files\Inno Setup 6\ISCC.exe
)

if not defined ISCC (
    echo.
    echo WARNING: Inno Setup 6 not found in default locations.
    echo   EXE is ready at: dist\NPCJason.exe
    echo.
    echo   To build the installer manually:
    echo     1. Install Inno Setup 6 from https://jrsoftware.org/isinfo.php
    echo     2. Run: "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
    echo.
    pause
    exit /b 0
)

"%ISCC%" installer.iss
if errorlevel 1 (
    echo ERROR: Inno Setup compilation failed.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  EXE:       dist\NPCJason.exe
echo  Installer: NPCJason_Setup_1.0.0.exe
echo ============================================
echo.
pause

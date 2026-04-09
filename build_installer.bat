@echo off
echo === NPCJason Full Build (EXE + Installer) ===
echo.
for /f %%i in ('python -c "from npcjason_app.version import APP_VERSION; print(APP_VERSION)"') do set APP_VERSION=%%i

echo [1/7] Installing dependencies...
python -m pip install --upgrade pip --quiet
python -m pip install ".[build]" --quiet
if errorlevel 1 (
    echo ERROR: pip install failed. Make sure Python is on PATH.
    pause
    exit /b 1
)

echo [2/6] Validating installed dependencies...
python -m pip check
if errorlevel 1 (
    echo ERROR: pip dependency check failed.
    pause
    exit /b 1
)

echo [3/7] Running tests...
python -m unittest discover -s tests -v
if errorlevel 1 (
    echo ERROR: Tests failed.
    pause
    exit /b 1
)

echo [4/7] Compiling source files...
python -m compileall npcjason_app tests npcjason.py
if errorlevel 1 (
    echo ERROR: Source compilation check failed.
    pause
    exit /b 1
)

echo [5/7] Generating icon...
python generate_icon.py
if errorlevel 1 (
    echo ERROR: Icon generation failed.
    pause
    exit /b 1
)

echo [6/7] Building EXE with PyInstaller...
python -m PyInstaller npcjason.spec --clean --noconfirm
if errorlevel 1 (
    echo ERROR: PyInstaller build failed.
    pause
    exit /b 1
)

echo [7/7] Building installer with Inno Setup...
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
echo  Installer: NPCJason_Setup_%APP_VERSION%.exe
echo ============================================
echo.
pause

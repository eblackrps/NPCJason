@echo off
echo === NPCJason EXE Build ===
echo.

echo [1/6] Installing dependencies...
python -m pip install --upgrade pip --quiet
python -m pip install ".[build]" --quiet
if errorlevel 1 (
    echo ERROR: pip install failed. Make sure Python is on PATH.
    pause
    exit /b 1
)

echo [2/5] Validating installed dependencies...
python -m pip check
if errorlevel 1 (
    echo ERROR: pip dependency check failed.
    pause
    exit /b 1
)

echo [3/6] Running tests...
python -m unittest discover -s tests -v
if errorlevel 1 (
    echo ERROR: Tests failed.
    pause
    exit /b 1
)

echo [4/6] Compiling source files...
python -m compileall npcjason_app tests npcjason.py
if errorlevel 1 (
    echo ERROR: Source compilation check failed.
    pause
    exit /b 1
)

echo [5/6] Generating icon...
python generate_icon.py
if errorlevel 1 (
    echo ERROR: Icon generation failed.
    pause
    exit /b 1
)

echo [6/6] Building EXE with PyInstaller...
python -m PyInstaller npcjason.spec --clean --noconfirm
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

@echo off
echo === NPCJason EXE Build ===
echo.

set "PYTHON_CMD=python"
py -3.13 -c "import sys" >nul 2>nul && set "PYTHON_CMD=py -3.13"
if /I "%PYTHON_CMD%"=="python" (
    py -3 -c "import sys" >nul 2>nul && set "PYTHON_CMD=py -3"
)

echo Using Python command: %PYTHON_CMD%
echo.

echo [1/6] Installing dependencies...
%PYTHON_CMD% -m pip install --upgrade pip --quiet
%PYTHON_CMD% -m pip install ".[build]" --quiet
if errorlevel 1 (
    echo ERROR: pip install failed. Make sure Python is on PATH.
    pause
    exit /b 1
)

echo [2/6] Validating installed dependencies...
%PYTHON_CMD% -m pip check
if errorlevel 1 (
    echo ERROR: pip dependency check failed.
    pause
    exit /b 1
)

echo [3/6] Running tests...
%PYTHON_CMD% -m unittest discover -s tests -v
if errorlevel 1 (
    echo ERROR: Tests failed.
    pause
    exit /b 1
)

echo [4/6] Compiling source files...
%PYTHON_CMD% -m compileall npcjason_app tests npcjason.py
if errorlevel 1 (
    echo ERROR: Source compilation check failed.
    pause
    exit /b 1
)

echo [5/6] Generating icon...
%PYTHON_CMD% generate_icon.py
if errorlevel 1 (
    echo ERROR: Icon generation failed.
    pause
    exit /b 1
)

echo [6/6] Building EXE with PyInstaller...
%PYTHON_CMD% -m PyInstaller npcjason.spec --clean --noconfirm
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

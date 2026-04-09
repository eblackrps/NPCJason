@echo off
echo Starting NPCJason Desktop Pet...
echo.

set "PYTHON_CMD=python"
py -3.13 -c "import sys" >nul 2>nul && set "PYTHON_CMD=py -3.13"
if /I "%PYTHON_CMD%"=="python" (
    py -3 -c "import sys" >nul 2>nul && set "PYTHON_CMD=py -3"
)

echo Using Python command: %PYTHON_CMD%
echo.
%PYTHON_CMD% -m pip install . --quiet 2>nul
%PYTHON_CMD% npcjason.py
pause

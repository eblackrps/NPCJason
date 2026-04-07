@echo off
echo Starting NPCJason Desktop Pet...
echo.
python -m pip install -r requirements.txt --quiet 2>nul
python npcjason.py
pause

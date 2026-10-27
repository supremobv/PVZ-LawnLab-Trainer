@echo off
cd /d "%~dp0"
if exist "release\LawnLab\LawnLab.exe" (
  start "" "release\LawnLab\LawnLab.exe"
  exit /b
)
if exist ".venv\Scripts\pythonw.exe" (
  start "" ".venv\Scripts\pythonw.exe" "lawnlab.py"
  exit /b
)
echo Install the requirements first: python -m pip install -r requirements.txt
pause

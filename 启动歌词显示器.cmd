@echo off
cd /d "%~dp0"
if not exist "%~dp0.venv\Scripts\pythonw.exe" python -m venv "%~dp0.venv"
"%~dp0.venv\Scripts\python.exe" -c "import PySide6.QtWidgets" >nul 2>&1
if not errorlevel 1 goto launch
echo Preparing desktop lyrics...
"%~dp0.venv\Scripts\python.exe" -m pip install -r "%~dp0requirements.txt"
if errorlevel 1 goto failed
:launch
start "" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0desktop_lyrics.py"
exit /b
:failed
pause

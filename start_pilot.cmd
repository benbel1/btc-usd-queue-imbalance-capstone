@echo off
setlocal
rem Run from any checkout location. Activate a Python environment first,
rem or create .venv beside this file. CAPSTONE_PYTHON may name an executable.
if defined CAPSTONE_PYTHON (
  set "PILOT_PYTHON=%CAPSTONE_PYTHON%"
) else if exist "%~dp0.venv\Scripts\python.exe" (
  set "PILOT_PYTHON=%~dp0.venv\Scripts\python.exe"
) else (
  set "PILOT_PYTHON=python"
)
"%PILOT_PYTHON%" -B -u "%~dp0monitor_pilot.py" %*
exit /b %errorlevel%

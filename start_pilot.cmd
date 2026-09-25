@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe py -3 -m venv .venv
if errorlevel 1 goto error
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto error
.venv\Scripts\python.exe -m unittest discover -s tests -v
if errorlevel 1 goto error
.venv\Scripts\python.exe collect.py --hours 48 --out data\pilot
if errorlevel 1 goto error
.venv\Scripts\python.exe analyze.py --input data\pilot\observations.csv --out results\pilot --mode pilot
pause
exit /b 0
:error
echo Collection or setup stopped. Keep this window open and copy the error for review.
pause
exit /b 1

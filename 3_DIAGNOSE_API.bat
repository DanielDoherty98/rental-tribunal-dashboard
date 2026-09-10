@echo off
setlocal
REM ---------------------------------------------------------------
REM  Self-locating launcher. %~dp0 is the folder this .bat lives in,
REM  so the project works from ANY drive with no editing.
REM ---------------------------------------------------------------
cd /d "%~dp0"
echo Project folder: %CD%
echo.
call conda activate tribunal 2>nul
if errorlevel 1 (
  echo [!] Could not activate the 'tribunal' environment.
  echo     Run 1_SETUP.bat first, and use Anaconda Prompt ^(not PowerShell^).
  echo.
  pause
  exit /b 1
)
echo ==============================================================
echo  GOV.UK API check - run this if you ever see a 422
echo ==============================================================
echo.
python scripts\00_diagnose_api.py
echo.
echo --- what the scraper will actually send ---
python run_all.py --check

echo.
pause
endlocal

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
echo  FULL SCRAPE - several hours on the first run
echo ==============================================================
echo.
echo Deliberately polite to GOV.UK. Later runs are incremental.
echo.
set /p go="Type Y then Enter to start: "
if /i not "%go%"=="Y" (
  echo Cancelled.
  pause
  exit /b 0
)
echo.
python run_all.py

echo.
pause
endlocal

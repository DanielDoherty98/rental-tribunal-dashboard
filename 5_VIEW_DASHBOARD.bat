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
echo  Local dashboard preview
echo ==============================================================
echo.
echo Opening http://127.0.0.1:8000 ...
echo Press Ctrl+C in this window when finished.
echo.
start "" http://127.0.0.1:8000
cd docs
python -m http.server 8000

echo.
pause
endlocal

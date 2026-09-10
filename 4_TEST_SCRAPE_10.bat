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
echo  Live test - fetches only 10 real decisions
echo ==============================================================
echo.
python run_all.py --test 10
echo.
echo Now open: output\rental_tribunal_decisions_v5.xlsx
echo Check the 'Needs Review' tab first, then the rent columns.

echo.
pause
endlocal

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
echo  Offline tests - no internet needed
echo ==============================================================
echo.
python doctor.py
if errorlevel 1 (
  echo.
  echo [!] Blocking problems found above. Fix them before continuing.
  pause
  exit /b 1
)
echo.
echo --- money / rent-number tests ---
python tests\test_money.py
if errorlevel 1 goto :failed
echo.
echo --- parser tests ---
python tests\test_parser.py
if errorlevel 1 goto :failed
echo.
echo --- API parameter tests ---
python tests\test_api_422.py
if errorlevel 1 goto :failed
echo.
echo ==============================================================
echo  All offline tests passed. Next: 3_DIAGNOSE_API.bat
echo ==============================================================
goto :done
:failed
echo.
echo [!] Tests failed. Do not scrape until this is resolved.
:done

echo.
pause
endlocal

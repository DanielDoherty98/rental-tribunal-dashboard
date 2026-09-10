@echo off
setlocal
cd /d "%~dp0"
echo ==============================================================
echo  RentalTribunalScraper V5.2 - one-time setup
echo ==============================================================
echo Project folder: %CD%
echo.
where conda >nul 2>nul
if errorlevel 1 (
  echo [!] conda was not found on PATH.
  echo     Reopen using: Start menu -^> Anaconda3 -^> Anaconda Prompt
  echo.
  pause
  exit /b 1
)
echo [1/3] Creating the 'tribunal' environment ^(skipped if it exists^)...
call conda create -n tribunal python=3.11 -y
echo.
echo [2/3] Activating...
call conda activate tribunal
if errorlevel 1 (
  echo [!] Activation failed. Run: conda init cmd.exe
  echo     then reopen Anaconda Prompt and try again.
  pause
  exit /b 1
)
echo.
echo [3/3] Installing dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
echo.
echo ==============================================================
echo  Setup finished. Next: 2_TEST_OFFLINE.bat
echo ==============================================================
pause
endlocal

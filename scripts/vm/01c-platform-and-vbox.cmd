@echo off
REM ============================================================================
REM Step 1c: enable Windows Hypervisor Platform and install VirtualBox.
REM MUST RUN ELEVATED. A reboot is required afterwards.
REM
REM Why HypervisorPlatform: this machine runs VBS/Core Isolation, so a
REM hypervisor is already loaded. Without WHP, VirtualBox falls back to a slow
REM software path or asks to disable Core Isolation. With it, VirtualBox runs on
REM top of the existing hypervisor and Core Isolation stays on.
REM
REM Hyper-V itself is NOT available on this SKU - DISM reports
REM "Microsoft-Hyper-V-All is unknown". Verified 12/11/2026. See README.md.
REM ============================================================================
setlocal
set LOG=%~dp0platform.log

echo === Enabling Windows Hypervisor Platform ===
dism /online /enable-feature /featurename:HypervisorPlatform /all /norestart >"%LOG%" 2>&1
echo   exit code: %errorlevel%

echo.
echo === Installing VirtualBox (winget) ===
winget install --id Oracle.VirtualBox --exact --silent ^
  --accept-package-agreements --accept-source-agreements >>"%LOG%" 2>&1
echo   exit code: %errorlevel%

echo.
echo === Done. Log: %LOG% ===
echo A RESTART IS REQUIRED before the VM will run properly.
echo.
pause

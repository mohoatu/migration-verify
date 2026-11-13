@echo off
REM ============================================================================
REM Undo everything the VM experiment installed or switched on.
REM MUST RUN ELEVATED. A reboot is required to finish removing the features.
REM
REM Put the machine back the way it was on 12/11/2026 before any of this:
REM   - VirtualBox          installed 12/11, removed here
REM   - HypervisorPlatform  switched on 12/11, switched off here
REM   - VirtualMachinePlatform  switched on 12/11, switched off here
REM
REM Note: VirtualMachinePlatform is also what WSL2 needs. If WSL is ever wanted,
REM it has to be switched back on. That is the only thing lost here.
REM ============================================================================
setlocal
set LOG=%~dp0uninstall.log

echo === Uninstalling VirtualBox ===
winget uninstall --id Oracle.VirtualBox --silent --accept-source-agreements >"%LOG%" 2>&1
echo   exit code: %errorlevel%

echo === Turning off Windows Hypervisor Platform ===
dism /online /disable-feature /featurename:HypervisorPlatform /norestart >>"%LOG%" 2>&1
echo   exit code: %errorlevel%

echo === Turning off Virtual Machine Platform ===
dism /online /disable-feature /featurename:VirtualMachinePlatform /norestart >>"%LOG%" 2>&1
echo   exit code: %errorlevel%

echo.
echo === Done. Log: %LOG% ===
echo A RESTART IS REQUIRED to finish removing the features.
echo.
pause

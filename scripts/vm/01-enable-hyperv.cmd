@echo off
REM ============================================================================
REM Step 1 of the VM setup: enable Hyper-V and the Virtual Machine Platform.
REM MUST RUN ELEVATED. A reboot is required afterwards.
REM
REM ASCII only, on purpose: .cmd files are read with the OEM codepage and
REM non-ASCII text turns into mojibake or breaks parsing. The explanation in
REM Vietnamese lives in scripts\vm\README.md.
REM ============================================================================
setlocal
set LOG=%~dp0enable.log

echo === Enabling Hyper-V (several minutes) ===
dism /online /enable-feature /featurename:Microsoft-Hyper-V-All /all /norestart >"%LOG%" 2>&1
echo   exit code: %errorlevel%

echo === Enabling Virtual Machine Platform ===
dism /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart >>"%LOG%" 2>&1
echo   exit code: %errorlevel%

echo.
echo === Done. Log: %LOG% ===
echo A RESTART IS REQUIRED before the VM can be created.
echo.
pause

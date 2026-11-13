@echo off
REM Dump the optional features this Windows image actually offers.
REM Needs elevation. Written because guessing which features a SKU exposes
REM is exactly how the first attempt went wrong.
setlocal
set OUT=%~dp0features.txt
dism /online /get-features /format:table > "%OUT%" 2>&1
echo Written to %OUT%
timeout /t 3 >nul

# Install this repo's sub-agents and skills into .claude\ on this machine.
#
#   powershell -ExecutionPolicy Bypass -File harness\install.ps1
#
# ASCII only, on purpose. Windows PowerShell 5.1 reads .ps1 files as ANSI unless
# they carry a UTF-8 BOM, so non-ASCII text here breaks the parser on a machine
# that never asked for it. Explanations live in CLAUDE.md, where UTF-8 is safe.
#
# Why harness\ and not .claude\ directly: .claude\ is machine config, harness\ is
# repo property. Split that way, the repo travels and anyone who clones it is one
# command away from the same setup.

$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')

New-Item -ItemType Directory -Force -Path '.claude\agents', '.claude\skills' | Out-Null
Copy-Item 'harness\agents\*.md' '.claude\agents\' -Force
Copy-Item 'harness\skills\*' '.claude\skills\' -Recurse -Force

Write-Output 'installed:'
Get-ChildItem '.claude\agents' -Name | ForEach-Object { "  agent: $_" }
Get-ChildItem '.claude\skills' -Name | ForEach-Object { "  skill: $_" }
Write-Output ''
Write-Output 'Restart Claude Code so it picks them up.'

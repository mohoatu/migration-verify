# Snapshot work in progress onto the `snapshots` branch.
#
#   powershell -ExecutionPolicy Bypass -File scripts\snapshot.ps1
#
# PowerShell twin of snapshot.sh. Both exist because the work machine is Windows
# with no bash on PATH, and a script that only runs somewhere else is not a
# script.
#
# ASCII only, on purpose: Windows PowerShell 5.1 reads .ps1 as ANSI unless the
# file carries a UTF-8 BOM, so non-ASCII text breaks the parser.
#
# Snapshots go to the `snapshots` branch, never to the working branch. Main
# history stays clean, one concern per commit.

$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')

if (-not (git rev-parse --git-dir 2>$null)) {
  Write-Output 'not a git repo - run: git init'; exit 1
}

$status = git status --porcelain
if (-not $status) { Write-Output 'nothing changed, skipping'; exit 0 }

# Keep customer data out of snapshots. .gitignore already blocks it, but a
# snapshot runs unattended with nobody watching, so it checks again itself.
if ($status | Select-String -Pattern 'customer/|\.(cust|prod)\.txt' -Quiet) {
  Write-Output 'STOP: customer/ files are staged. Not snapshotting.'
  exit 1
}

$branch = git rev-parse --abbrev-ref HEAD
$stamp  = Get-Date -Format 'yyyy-MM-dd HH:mm'

$tree = git stash create "wip"
if (-not $tree) { $tree = git rev-parse HEAD }

$parent = git rev-parse --verify -q refs/heads/snapshots
if ($parent) {
  $commit = git commit-tree "$tree^{tree}" -p $parent -m "snapshot $stamp ($branch)"
} else {
  $commit = git commit-tree "$tree^{tree}" -m "snapshot $stamp ($branch)"
}
git update-ref refs/heads/snapshots $commit

Write-Output "snapshot $stamp -> snapshots ($(git rev-parse --short $commit))"
Write-Output 'review:  git log --oneline snapshots'
Write-Output 'restore: git checkout snapshots -- <path>'

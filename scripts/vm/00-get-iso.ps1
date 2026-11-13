# ============================================================================
# Step 0: fetch the Windows 11 ISO, then prove it came from Microsoft.
#
#   powershell -ExecutionPolicy Bypass -File scripts\vm\00-get-iso.ps1
#
# Why this exists: microsoft.com/software-download/windows11 only shows the ISO
# picker to non-Windows browsers, and rate-limits link creation per IP. On a
# Windows machine the page errors out.
#
# Fido (github.com/pbatard/Fido, by the author of Rufus) calls Microsoft's own
# download API and returns a genuine microsoft.com link. The ISO still comes
# from Microsoft's servers; Fido only gets past the gate.
#
# Running third-party code is a real cost, so this script pays it down:
#  1. The URL Fido returns is checked to be a microsoft.com host before anything
#     is downloaded. A link anywhere else aborts the run.
#  2. The finished ISO is hashed and compared against the SHA256 that Microsoft
#     publishes on its own download page. Match means the bytes are Microsoft's,
#     whatever path they travelled.
# Without step 2 this would be trust. With it, it is verification.
#
# ASCII only (PowerShell 5.1 reads .ps1 as ANSI without a BOM).
# ============================================================================

param(
  [string]$OutDir   = 'D:\iso',
  [string]$Edition  = 'Home/Pro',
  [string]$Language = 'English',
  [string]$Url      = '',   # reuse a link Fido already returned (valid 24h)
  [switch]$SkipDownload
)

$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# SHA256 published by Microsoft for the Windows 11 2026 Update (26H2),
# "English 64-bit", read from the official download page on 12/11/2026.
# If Fido hands back a different build this will not match - that is the point:
# a mismatch must stop the run, not be explained away.
$ExpectedSha = 'BD4307DF32BC8AF33B39CCECB1174AEB345386630F89A2B86C7A4E36B55EA650'

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

if ($Url) {
  # Microsoft's "Sentinel" rejects repeat link requests from the same IP within
  # a short window, so a link that was already obtained is worth reusing rather
  # than burning another request. Links stay valid 24 hours.
  Write-Host '=== Reusing a link obtained earlier ==='
  $url = $Url
} else {
  $fido = Join-Path $OutDir 'Fido.ps1'
  if (-not (Test-Path $fido)) {
    Write-Host '=== Fetching Fido ==='
    Invoke-WebRequest -UseBasicParsing `
      -Uri 'https://raw.githubusercontent.com/pbatard/Fido/master/Fido.ps1' `
      -OutFile $fido
  }

  Write-Host '=== Asking Microsoft for a download link ==='
  $url = & $fido -Win 11 -Rel Latest -Ed $Edition -Lang $Language -Arch x64 -GetUrl

  if (-not $url) {
    Write-Error ('Fido returned no URL. Microsoft rate-limits link creation per IP ' +
                 '("Sentinel marked this request as rejected"). Wait a few hours, or ' +
                 'pass a link you already have with -Url.')
  }
  $url = ($url | Select-Object -Last 1).ToString().Trim()
}

# Guard 1: the link must be Microsoft's. Anything else and we stop.
$host_ = ([Uri]$url).Host
if ($host_ -notmatch '\.microsoft\.com$') {
  Write-Error "Refusing to download: link points at '$host_', not microsoft.com. URL was: $url"
}
Write-Host "Link host: $host_  (ok)"

$name = [IO.Path]::GetFileName(([Uri]$url).AbsolutePath)
if (-not $name -or $name -notmatch '\.iso$') { $name = 'Win11_x64.iso' }
$iso = Join-Path $OutDir $name

if ($SkipDownload) { Write-Host "URL: $url"; exit 0 }

Write-Host "=== Downloading to $iso (about 6-7 GB, this takes a while) ==="
# curl.exe ships with Windows 10/11 and resumes with -C -, which matters on a
# 6 GB file over a connection that may drop.
& curl.exe -L --fail --retry 5 --retry-delay 5 -C - -o $iso $url
if ($LASTEXITCODE -ne 0) { Write-Error "Download failed with exit code $LASTEXITCODE" }

$sizeGB = [math]::Round((Get-Item $iso).Length / 1GB, 2)
Write-Host "Downloaded: $sizeGB GB"

Write-Host '=== Verifying against the hash Microsoft publishes ==='
$sha = (Get-FileHash -Algorithm SHA256 $iso).Hash
Write-Host "  got:      $sha"
Write-Host "  expected: $ExpectedSha"

if ($sha -eq $ExpectedSha) {
  Write-Host ''
  Write-Host 'VERIFIED - these bytes are Microsoft published Windows 11 English x64.'
} else {
  Write-Host ''
  Write-Host 'HASH DOES NOT MATCH the value recorded on 12/11/2026.'
  Write-Host 'Two innocent explanations: Microsoft shipped a newer build, or a'
  Write-Host 'different edition/language was selected. One not-innocent one.'
  Write-Host 'Check the current hash table at'
  Write-Host '  https://www.microsoft.com/en-us/software-download/windows11'
  Write-Host 'before using this ISO. Do not skip this.'
  exit 1
}

Write-Host ''
Write-Host "ISO ready: $iso"
Write-Host 'Next: powershell -ExecutionPolicy Bypass -File scripts\vm\02-create-vm.ps1'

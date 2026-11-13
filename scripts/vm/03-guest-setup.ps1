# ============================================================================
# Step 3: turn the freshly installed guest into something an agent can drive,
# then run the test suite inside it.
#
#   powershell -ExecutionPolicy Bypass -File scripts\vm\03-guest-setup.ps1
#
# Runs on the HOST. Two phases:
#   A. Over VBoxManage guestcontrol (Guest Additions) - switch on OpenSSH.
#   B. Over ssh/scp - Python, the repo, the tests.
#
# Phase A exists because the chicken-and-egg problem has to be broken somehow:
# SSH is how we want to talk to the guest, but SSH is not on yet. Guest
# Additions is the only channel available at that moment.
#
# ASCII only (PowerShell 5.1 reads .ps1 as ANSI without a BOM).
# ============================================================================

param(
  [string]$Name      = 'win11-verify',
  [int]   $SshPort   = 2222,
  [string]$GuestUser = 'agent',
  [string]$GuestPass = 'ChangeMe!2026',
  [string]$RepoHost  = 'D:\startup\migration-verify',
  [int]   $WaitMin   = 45
)

$ErrorActionPreference = 'Stop'
$vbox = Join-Path $env:ProgramFiles 'Oracle\VirtualBox\VBoxManage.exe'
$target = "$GuestUser@127.0.0.1"

function Quiet($block) {
  # Native tools write progress and warnings to stderr, which PowerShell treats
  # as fatal under ErrorActionPreference='Stop'. Steps allowed to fail say so.
  $old = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
  try { & $block } finally { $ErrorActionPreference = $old }
}

# ---- A1. wait for Guest Additions to answer --------------------------------
Write-Host "=== Waiting for Windows setup to finish (up to $WaitMin min) ==="
$deadline = (Get-Date).AddMinutes($WaitMin)
$ready = $false
while ((Get-Date) -lt $deadline) {
  $out = Quiet { & $vbox guestproperty get $Name '/VirtualBox/GuestInfo/OS/LoggedInUsers' 2>&1 }
  if ("$out" -match 'Value:\s*[1-9]') { $ready = $true; break }
  Start-Sleep 20
  Write-Host -NoNewline '.'
}
Write-Host ''
if (-not $ready) {
  Write-Error "Guest never reported a logged-in user within $WaitMin minutes. Open the VM window and look at what setup is asking."
}
Write-Host 'Guest is up and a user is logged in.'
Start-Sleep 30   # let first-logon tasks settle before pushing work at it

# ---- A2. copy in and run the SSH enabler -----------------------------------
Write-Host '=== Enabling OpenSSH in the guest ==='
$script = Join-Path $PSScriptRoot 'guest\enable-ssh.ps1'

Quiet { & $vbox guestcontrol $Name copyto $script 'C:\enable-ssh.ps1' `
          --username $GuestUser --password $GuestPass }

Quiet { & $vbox guestcontrol $Name run `
          --username $GuestUser --password $GuestPass `
          --exe 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' `
          --wait-stdout --wait-stderr `
          -- powershell -ExecutionPolicy Bypass -File C:\enable-ssh.ps1 }

# ---- B1. prove SSH works ----------------------------------------------------
Write-Host '=== Checking SSH ==='
function Guest([string]$cmd) {
  ssh -p $SshPort -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL `
      -o ConnectTimeout=10 $target $cmd
}

$probe = Quiet { Guest 'echo ok' }
if ("$probe" -notmatch 'ok') {
  Write-Error "No SSH on port $SshPort. Check C:\enable-ssh.log inside the guest."
}
Write-Host "SSH works: ssh -p $SshPort $target"

# ---- B2. toolchain ----------------------------------------------------------
# Same Python major version as the host on purpose: this VM is here to reproduce
# what a customer's Windows does, not to invent a third environment with its own
# quirks to debug.
Write-Host '=== Installing Python 3.13 and git ==='
Quiet { Guest 'winget install --id Python.Python.3.13 --exact --silent --accept-package-agreements --accept-source-agreements' }
Quiet { Guest 'winget install --id Git.Git --exact --silent --accept-package-agreements --accept-source-agreements' }

# ---- B3. the repo -----------------------------------------------------------
# scp rather than a shared folder: a shared folder puts customer data one
# misclick away from the host filesystem, and keeping that data inside the VM is
# the main reason this VM exists.
Write-Host '=== Copying the repo in ==='
Quiet { Guest 'Remove-Item -Recurse -Force C:\work\migration-verify -ErrorAction SilentlyContinue' }
Quiet { Guest 'New-Item -ItemType Directory -Force -Path C:\work | Out-Null' }
scp -P $SshPort -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL -r `
    "$RepoHost" "${target}:C:/work/migration-verify"

# ---- B4. the point of all this ---------------------------------------------
Write-Host ''
Write-Host '=== Running the test suite inside the guest ==='
Guest 'cd C:\work\migration-verify; python tests\run.py'
Write-Host ''
Write-Host '=== Mutation check inside the guest ==='
Guest 'cd C:\work\migration-verify; python tests\mutate.py'

Write-Host ''
Write-Host 'Guest ready.'
Write-Host "  shell:    ssh -p $SshPort $target"
Write-Host "  snapshot: VBoxManage snapshot $Name take clean-$(Get-Date -Format yyyyMMdd)"

# ============================================================================
# Step 2: create the Windows 11 test VM in VirtualBox and start an unattended
# install. Run as a normal user - VirtualBox does not need elevation.
#
#   powershell -ExecutionPolicy Bypass -File scripts\vm\02-create-vm.ps1
#
# ASCII only, on purpose: Windows PowerShell 5.1 reads .ps1 as ANSI without a
# UTF-8 BOM. Vietnamese explanation lives in scripts\vm\README.md.
#
# Design notes worth keeping:
#  - VirtualBox 7's own unattended installer is used instead of a hand-written
#    autounattend.xml. It generates the answer file, injects Guest Additions and
#    runs a post-install command. Fewer moving parts to get subtly wrong.
#  - NAT with a port-forward on 2222 is what makes this VM usable by an agent:
#    everything afterwards happens over `ssh -p 2222`, not by clicking inside a
#    VM window. A VM you can only drive with a mouse is a VM an agent cannot use.
#  - TPM 2.0 and Secure Boot are mandatory for Windows 11; the installer refuses
#    without them.
#  - The disk lives on D: because C: has ~55 GB free and this takes 60.
# ============================================================================

param(
  [string]$Name    = 'win11-verify',
  [string]$Iso     = '',
  [string]$BaseDir = 'D:\VMs',
  [int]   $MemMB   = 6144,
  [int]   $Cpus    = 4,
  [int]   $DiskMB  = 61440,
  [int]   $SshPort = 2222,
  [string]$GuestUser = 'agent',
  [string]$GuestPass = 'ChangeMe!2026'
)

$ErrorActionPreference = 'Stop'

$vbox = Join-Path $env:ProgramFiles 'Oracle\VirtualBox\VBoxManage.exe'
if (-not (Test-Path $vbox)) {
  $vbox = Join-Path $env:ProgramFiles 'Oracle\VirtualBox VM\VBoxManage.exe'
}
if (-not (Test-Path $vbox)) {
  Write-Error 'VBoxManage.exe not found. Run 01c-platform-and-vbox.cmd first.'
}

# ---- locate the ISO --------------------------------------------------------
if (-not $Iso) {
  $candidates = @()
  foreach ($dir in 'D:\iso', "$env:USERPROFILE\Downloads", 'D:\') {
    if (Test-Path $dir) {
      $candidates += Get-ChildItem $dir -Filter '*.iso' -File -ErrorAction SilentlyContinue
    }
  }
  $win = $candidates | Where-Object { $_.Name -match 'win' } | Sort-Object Length -Descending
  if (-not $win) {
    Write-Host 'No Windows ISO found in D:\iso, Downloads or D:\'
    Write-Host 'Download it from https://www.microsoft.com/software-download/windows11'
    Write-Host 'Choose English (United States) and save it to D:\iso\'
    exit 1
  }
  $Iso = $win[0].FullName
}
Write-Host "ISO: $Iso"

# ---- fail early on the things that silently ruin the install ---------------
$isoGB = [math]::Round((Get-Item $Iso).Length / 1GB, 1)
if ($isoGB -lt 3) { Write-Error "ISO is only ${isoGB} GB - looks truncated." }

$freeGB = [math]::Round((Get-PSDrive (Split-Path $BaseDir -Qualifier).Trim(':')).Free / 1GB, 1)
$needGB = [math]::Round($DiskMB / 1024, 1)
if ($freeGB -lt $needGB + 5) {
  Write-Error "Only ${freeGB} GB free on $BaseDir, need about ${needGB} GB plus headroom."
}

New-Item -ItemType Directory -Force -Path $BaseDir | Out-Null

# ---- remove any previous attempt -------------------------------------------
$existing = & $vbox list vms
if ($existing -match [regex]::Escape("`"$Name`"")) {
  Write-Host "Removing previous VM '$Name'"
  # PowerShell with ErrorActionPreference='Stop' treats ANY native-command
  # stderr as fatal, and `controlvm poweroff` on a stopped VM writes to stderr.
  # Clean-up steps that are allowed to fail must say so explicitly.
  $old = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
  & $vbox controlvm $Name poweroff *>$null
  Start-Sleep 2
  & $vbox unregistervm $Name --delete *>$null
  $ErrorActionPreference = $old
}

# ---- create -----------------------------------------------------------------
Write-Host "Creating VM '$Name' - ${MemMB} MB RAM, ${Cpus} CPUs, ${needGB} GB disk"
& $vbox createvm --name $Name --ostype 'Windows11_64' --basefolder $BaseDir --register

# NOTE: VBoxManage 7.2 has no `--secure-boot` on modifyvm - that was a wrong
# guess and it made the WHOLE modifyvm call fail, leaving the VM on defaults.
# Secure Boot is set through modifynvram instead, below.
& $vbox modifyvm $Name `
    --memory $MemMB --cpus $Cpus --vram 128 `
    --firmware efi --tpm-type 2.0 `
    --graphicscontroller vboxsvga --audio-driver none `
    --nic1 nat --clipboard-mode bidirectional `
    --nested-hw-virt off
if ($LASTEXITCODE -ne 0) { Write-Error 'modifyvm failed - settings were not applied.' }

# Secure Boot: Windows 11 setup refuses without it. Order matters - the UEFI
# variable store has to exist before signatures can be enrolled into it.
& $vbox modifynvram $Name inituefivarstore
& $vbox modifynvram $Name enrollmssignatures   # Microsoft KEK and DB
& $vbox modifynvram $Name enrollorclpk         # platform key - without it the
                                               # next line fails with
                                               # "PK is not enrolled"
& $vbox modifynvram $Name secureboot --enable
if ($LASTEXITCODE -ne 0) { Write-Error 'Could not enable Secure Boot.' }

# SSH is the whole point: without this forward the VM is mouse-only.
& $vbox modifyvm $Name --nat-pf1 "ssh,tcp,127.0.0.1,$SshPort,,22"

$disk = Join-Path $BaseDir "$Name\$Name.vdi"
& $vbox createmedium disk --filename $disk --size $DiskMB --format VDI
& $vbox storagectl $Name --name 'SATA' --add sata --controller IntelAhci --portcount 2
& $vbox storageattach $Name --storagectl 'SATA' --port 0 --device 0 --type hdd --medium $disk
& $vbox storageattach $Name --storagectl 'SATA' --port 1 --device 0 --type dvddrive --medium emptydrive

# ---- unattended install -----------------------------------------------------
# No --post-install-command here, on purpose. The obvious thing to do is pass a
# PowerShell one-liner that turns on OpenSSH, but that string contains spaces and
# quotes, and PowerShell 5.1's native-argument handling mangles it - VBoxManage
# received "-Online" as its own argument and rejected the whole command. Guest
# Additions are installed instead, and step 03 turns on SSH through
# `VBoxManage guestcontrol`, where each argument is passed separately and nothing
# depends on quoting surviving two layers of shell.
# --hostname must be a fully qualified name; VBoxManage rejects a bare label
# with "Incomplete hostname - must include both a name and a domain".
Write-Host 'Preparing unattended installation'
& $vbox unattended install $Name `
    --iso=$Iso `
    --user=$GuestUser --password=$GuestPass `
    --full-user-name='Verify Agent' `
    --install-additions `
    --locale=en_US --country=US `
    --time-zone='SE Asia Standard Time' `
    --hostname='win11-verify.local' `
    --start-vm=gui
if ($LASTEXITCODE -ne 0) { Write-Error 'unattended install failed to start.' }

Write-Host ''
Write-Host "VM '$Name' is installing. Unattended, 20-40 minutes."
Write-Host 'Next: scripts\vm\03-guest-setup.ps1 (turns on SSH, installs Python, runs the tests).'

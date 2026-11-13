# Runs INSIDE the guest. Copied in and executed by 03-guest-setup.ps1 through
# VBoxManage guestcontrol.
#
# It exists as a file rather than a one-liner for one reason: every attempt to
# pass this as a quoted command string got mangled somewhere between PowerShell,
# VBoxManage and the guest shell. A file path has no spaces to lose.
#
# ASCII only (PowerShell 5.1 reads .ps1 as ANSI without a BOM).

$ErrorActionPreference = 'Continue'
$log = 'C:\enable-ssh.log'
function Say($m) { "$((Get-Date).ToString('HH:mm:ss'))  $m" | Tee-Object -FilePath $log -Append }

Say 'Installing the OpenSSH server capability'
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0 | Out-Null

Say 'Starting sshd and setting it to start automatically'
Set-Service -Name sshd -StartupType Automatic
Start-Service sshd

Say 'Opening TCP 22 in the firewall'
if (-not (Get-NetFirewallRule -Name 'sshd' -ErrorAction SilentlyContinue)) {
  New-NetFirewallRule -Name 'sshd' -DisplayName 'OpenSSH Server' `
    -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22 | Out-Null
}

# Default shell PowerShell, not cmd: everything driven over SSH afterwards is
# PowerShell, and having to prefix every command with `powershell -Command` is
# an invitation for the same quoting bugs all over again.
Say 'Setting the default SSH shell to PowerShell'
New-Item -Path 'HKLM:\SOFTWARE\OpenSSH' -Force | Out-Null
New-ItemProperty -Path 'HKLM:\SOFTWARE\OpenSSH' -Name DefaultShell `
  -Value 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' `
  -PropertyType String -Force | Out-Null

Say ('sshd status: ' + (Get-Service sshd).Status)
Say 'done'

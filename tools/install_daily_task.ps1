[CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'Medium')]
param(
    [ValidatePattern('^([01]\d|2[0-3]):[0-5]\d$')]
    [string]$At = '08:00',

    [ValidateRange(1, 5)]
    [int]$Top = 3,

    [ValidateRange(0, 100)]
    [int]$MinScore = 60,

    [ValidateRange(0.01, 1000)]
    [decimal]$MaxBudgetUsd = 12.00,

    [string]$PublishTo = '',

    [string]$ClaudePath = $env:CLAUDE_CODE_CLI,

    [string]$TaskName = 'AI Job Search Daily',

    [string]$RepoPath = ''
)

$ErrorActionPreference = 'Stop'
if (-not $RepoPath) {
    $RepoPath = Split-Path -Parent $PSScriptRoot
}
$repo = (Resolve-Path -LiteralPath $RepoPath).Path
$script = Join-Path $repo 'tools\run_daily.ps1'
if (-not (Test-Path -LiteralPath $script -PathType Leaf)) {
    throw "Daily runner not found: $script"
}
foreach ($value in @($repo, $script, $PublishTo, $TaskName)) {
    if ($value.Contains('"')) { throw 'Paths and task names cannot contain a double quote.' }
}
if ($ClaudePath) {
    if ($ClaudePath.Contains('"')) { throw 'ClaudePath cannot contain a double quote.' }
    if (-not (Test-Path -LiteralPath $ClaudePath -PathType Leaf)) {
        throw "Claude Code CLI not found at -ClaudePath '$ClaudePath'."
    }
    $ClaudePath = (Resolve-Path -LiteralPath $ClaudePath).Path
}
else {
    $claude = Get-Command claude -ErrorAction SilentlyContinue
    $nativeClaude = Join-Path $env:USERPROFILE '.local\bin\claude.exe'
    $wingetRoot = Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Packages'
    $wingetClaude = Get-ChildItem -Path $wingetRoot -Filter 'claude.exe' -File -Recurse -ErrorAction SilentlyContinue |
        Where-Object { $_.Directory.Name -like 'Anthropic.ClaudeCode_*' } |
        Select-Object -First 1
    if (-not $claude -and -not (Test-Path -LiteralPath $nativeClaude -PathType Leaf) -and -not $wingetClaude) {
        throw @"
Claude Code CLI was not found. Install it and verify 'claude --version' before
registering the task, or pass -ClaudePath / set CLAUDE_CODE_CLI to claude.exe.
"@
    }
}

$powerShell = (Get-Command powershell.exe -ErrorAction Stop).Source
$budget = $MaxBudgetUsd.ToString([Globalization.CultureInfo]::InvariantCulture)
$arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$script`" -RepoPath `"$repo`" -Top $Top -MinScore $MinScore -MaxBudgetUsd $budget"
if ($ClaudePath) {
    $arguments += " -ClaudePath `"$ClaudePath`""
}
if ($PublishTo) {
    $arguments += " -PublishTo `"$([IO.Path]::GetFullPath($PublishTo))`""
}

$clock = [DateTime]::ParseExact($At, 'HH:mm', [Globalization.CultureInfo]::InvariantCulture)
$action = New-ScheduledTaskAction -Execute $powerShell -Argument $arguments -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -Daily -At $clock
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited

if ($PSCmdlet.ShouldProcess($TaskName, "Register daily task at $At")) {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description 'Scrape, rank, prepare a bounded job batch, and publish a private delivery page.' -Force | Out-Null
    Write-Output "Installed scheduled task '$TaskName' for $At. It runs only while this user is logged in."
}

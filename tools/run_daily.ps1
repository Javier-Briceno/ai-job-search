[CmdletBinding()]
param(
    [ValidateRange(1, 5)]
    [int]$Top = 3,

    [ValidateRange(0, 100)]
    [int]$MinScore = 60,

    [ValidateRange(0.01, 1000)]
    [decimal]$MaxBudgetUsd = 12.00,

    [string]$RepoPath = '',

    [string]$ClaudePath = $env:CLAUDE_CODE_CLI,

    [string]$PublishTo = $env:JOB_SEARCH_DELIVERY_DIR
)

$ErrorActionPreference = 'Stop'
if (-not $RepoPath) {
    $RepoPath = Split-Path -Parent $PSScriptRoot
}
$repo = (Resolve-Path -LiteralPath $RepoPath).Path
$runner = Join-Path $repo '.claude\commands\daily.md'
if (-not (Test-Path -LiteralPath $runner -PathType Leaf)) {
    throw "Not an AI Job Search repository: $repo"
}

$claudeSource = $null
if ($ClaudePath) {
    if (-not (Test-Path -LiteralPath $ClaudePath -PathType Leaf)) {
        throw "Claude Code CLI not found at -ClaudePath '$ClaudePath'."
    }
    $claudeSource = (Resolve-Path -LiteralPath $ClaudePath).Path
}
else {
    $claude = Get-Command claude -ErrorAction SilentlyContinue
    if ($claude) {
        $claudeSource = $claude.Source
    }
    else {
        $nativeClaude = Join-Path $env:USERPROFILE '.local\bin\claude.exe'
        if (Test-Path -LiteralPath $nativeClaude -PathType Leaf) {
            $claudeSource = $nativeClaude
        }
        else {
            $wingetRoot = Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Packages'
            $wingetClaude = Get-ChildItem -Path $wingetRoot -Filter 'claude.exe' -File -Recurse -ErrorAction SilentlyContinue |
                Where-Object { $_.Directory.Name -like 'Anthropic.ClaudeCode_*' } |
                Select-Object -First 1
            if ($wingetClaude) {
                $claudeSource = $wingetClaude.FullName
            }
        }
    }
}

if (-not $claudeSource) {
    throw @"
Claude Code CLI was not found. The VS Code extension alone is not available to
Windows Task Scheduler. Install the Claude Code CLI, reopen PowerShell, and run
'claude --version'; or pass -ClaudePath / set CLAUDE_CODE_CLI to claude.exe.
"@
}

$python = Get-Command python -ErrorAction Stop
$logDir = Join-Path $repo 'daily_runs'
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$stamp = Get-Date -Format 'yyyy-MM-dd_HHmmss'
$logPath = Join-Path $logDir "$stamp.json"

$prompt = "Read .claude/commands/daily.md and execute it now as /daily with arguments --top $Top --min-score $MinScore --yes. Do not merely explain the command."
$budget = $MaxBudgetUsd.ToString([Globalization.CultureInfo]::InvariantCulture)
$claudeArgs = @(
    '-p', $prompt,
    '--model', 'sonnet',
    '--permission-mode', 'auto',
    '--max-turns', '240',
    '--max-budget-usd', $budget,
    '--no-session-persistence',
    '--output-format', 'json'
)

Push-Location $repo
try {
    & $claudeSource @claudeArgs 2>&1 | Tee-Object -FilePath $logPath
    $claudeExit = $LASTEXITCODE

    # Always rebuild from durable tracker state. A partial Claude run may still
    # have completed one valid application before a later portal/job failed.
    & $python.Source 'tools/build_delivery_report.py'
    $reportExit = $LASTEXITCODE
}
finally {
    Pop-Location
}

if ($reportExit -ne 0) {
    throw "Delivery report failed with exit code $reportExit. See $logPath"
}

if ($PublishTo) {
    $destination = [IO.Path]::GetFullPath($PublishTo)
    $destinationRoot = [IO.Path]::GetPathRoot($destination).TrimEnd('\')
    if ($destination.TrimEnd('\') -eq $destinationRoot) {
        throw "Refusing to publish directly into a drive root: $destination"
    }
    if ($destination.TrimEnd('\') -eq $repo.TrimEnd('\')) {
        throw "PublishTo must be a separate shared folder, not the repository root."
    }
    New-Item -ItemType Directory -Path $destination -Force | Out-Null
    $deliverySource = Join-Path $repo 'deliveries'
    Get-ChildItem -LiteralPath $deliverySource -Force | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination $destination -Recurse -Force
    }
    Write-Output "Published delivery package to: $destination"
}

Write-Output "Daily run log: $logPath"
if ($claudeExit -ne 0) {
    throw "Claude daily pipeline exited with code $claudeExit. The report was rebuilt from valid existing state."
}

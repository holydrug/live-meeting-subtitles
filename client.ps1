<#
.SYNOPSIS
    Voice Analyzer Client (Windows)
.EXAMPLE
    .\client.ps1
    .\client.ps1 -Device "CABLE"
    .\client.ps1 -ListDevices
#>

param(
    [string]$HostName = "localhost",
    [int]$Port = 9876,
    [string]$Device = "",
    [switch]$NoOverlay,
    [switch]$ListDevices,
    [switch]$Interactive,
    [switch]$Help
)

function Show-Menu {
    param(
        [string]$Title,
        [string[]]$Options,
        [int]$Default = 0
    )
    Write-Host "`n$Title" -ForegroundColor Yellow
    for ($i = 0; $i -lt $Options.Length; $i++) {
        $marker = if ($i -eq $Default) { ">" } else { " " }
        $color = if ($i -eq $Default) { "Green" } else { "White" }
        Write-Host "  $marker [$($i + 1)] $($Options[$i])" -ForegroundColor $color
    }
    $choice = Read-Host "Choose [1-$($Options.Length), default=$($Default + 1)]"
    if ([string]::IsNullOrWhiteSpace($choice)) { return $Default }
    $idx = [int]$choice - 1
    if ($idx -ge 0 -and $idx -lt $Options.Length) { return $idx }
    return $Default
}

function Show-YesNo {
    param(
        [string]$Question,
        [bool]$Default = $true
    )
    $defaultStr = if ($Default) { "Y/n" } else { "y/N" }
    $answer = Read-Host "$Question [$defaultStr]"
    if ([string]::IsNullOrWhiteSpace($answer)) { return $Default }
    return $answer.ToLower().StartsWith("y")
}

if ($Help) {
    Write-Host "Usage: .\client.ps1 [options]"
    Write-Host "  -Interactive    Interactive mode (choose settings)"
    Write-Host "  -HostName       Server host (default: localhost)"
    Write-Host "  -Port           Server port (default: 9876)"
    Write-Host "  -Device         Audio device name (partial match)"
    Write-Host "  -NoOverlay      Console only mode"
    Write-Host "  -ListDevices    List available audio devices"
    exit 0
}

Set-Location $PSScriptRoot

# Activate venv
if (Test-Path "venv_win\Scripts\Activate.ps1") {
    . .\venv_win\Scripts\Activate.ps1
}

# List devices mode
if ($ListDevices) {
    python -m client.main --list-devices
    exit 0
}

# Interactive mode
if ($Interactive -or [string]::IsNullOrWhiteSpace($Device)) {
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  Voice Analyzer Client - Setup" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan

    # Get available audio devices
    Write-Host "`nDetecting audio devices..." -ForegroundColor Gray
    $deviceOutput = python -m client.main --list-devices 2>&1
    $devices = @()
    foreach ($line in $deviceOutput) {
        if ($line -match "^\s*-\s+(.+?)\s*\[Loopback\]") {
            $devices += $Matches[1].Trim()
        }
    }

    if ($devices.Count -gt 0) {
        # Find preferred device (virtual cables first)
        $defaultIdx = 0
        for ($i = 0; $i -lt $devices.Count; $i++) {
            if ($devices[$i] -match "CABLE|VB-Audio|Virtual") {
                $defaultIdx = $i
                break
            }
        }

        $devIdx = Show-Menu -Title "Select Audio Device:" -Options $devices -Default $defaultIdx
        $Device = $devices[$devIdx]
        Write-Host "  Selected: $Device" -ForegroundColor Green
    } else {
        Write-Host "  No audio devices found. Using default." -ForegroundColor Yellow
    }

    # Overlay option
    Write-Host ""
    $useOverlay = Show-YesNo -Question "Enable overlay window?" -Default $true
    if (-not $useOverlay) {
        $NoOverlay = $true
    }

    Write-Host ""
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Voice Analyzer Client" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Server: ${HostName}:${Port}"
if ($Device) {
    Write-Host "  Device: $Device" -ForegroundColor Green
}
Write-Host "  Overlay: $(if ($NoOverlay) { 'OFF' } else { 'ON' })"
Write-Host "========================================"
Write-Host ""

# Build arguments
$PythonArgs = @("--host", $HostName, "--port", $Port)
if ($Device) { $PythonArgs += @("--device", $Device) }
if ($NoOverlay) { $PythonArgs += "--no-overlay" }

# Run client
python -m client.main @PythonArgs

<#
.SYNOPSIS
    Voice Analyzer Server (launches in WSL)
.EXAMPLE
    .\server.ps1
    .\server.ps1 -Transcriber parakeet
    .\server.ps1 -Stop
#>

param(
    [ValidateSet("whisper", "parakeet")]
    [string]$Transcriber = "",

    [ValidateSet("google", "deepl", "local", "none")]
    [string]$Translator = "",

    [int]$Port = 9876,

    [switch]$Interactive,
    [switch]$Stop,
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

if ($Help) {
    Write-Host "Usage: .\server.ps1 [options]"
    Write-Host "  -Interactive    Interactive mode (choose settings)"
    Write-Host "  -Transcriber    whisper | parakeet"
    Write-Host "  -Translator     google | deepl | local | none"
    Write-Host "  -Port           Server port (default: 9876)"
    Write-Host "  -Stop           Stop running server"
    exit 0
}

# Get WSL path
$WinPath = $PSScriptRoot
$WslPath = (wsl wslpath -u "'$WinPath'").Trim()

if ($Stop) {
    Write-Host "Stopping server..." -ForegroundColor Yellow
    wsl bash -c "pkill -f 'python -m server.main'" 2>$null
    Write-Host "Done." -ForegroundColor Green
    exit 0
}

# Interactive mode
if ($Interactive -or ([string]::IsNullOrWhiteSpace($Transcriber) -and [string]::IsNullOrWhiteSpace($Translator))) {
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  Voice Analyzer Server - Setup" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan

    # Transcriber selection
    $transcribers = @(
        "parakeet  - NVIDIA NeMo (2x faster, recommended)",
        "whisper   - OpenAI Whisper large-v3"
    )
    $tIdx = Show-Menu -Title "Select Transcriber:" -Options $transcribers -Default 0
    $Transcriber = @("parakeet", "whisper")[$tIdx]

    # Translator selection
    $translators = @(
        "google - Google Translate (free, fast)",
        "deepl  - DeepL API (needs key)",
        "local  - NLLB local model (offline)",
        "none   - No translation"
    )
    $trIdx = Show-Menu -Title "Select Translator:" -Options $translators -Default 0
    $Translator = @("google", "deepl", "local", "none")[$trIdx]

    Write-Host ""
}

# Apply defaults
if ([string]::IsNullOrWhiteSpace($Transcriber)) { $Transcriber = "parakeet" }
if ([string]::IsNullOrWhiteSpace($Translator)) { $Translator = "google" }

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Voice Analyzer Server (WSL)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
$tcColor = if ($Transcriber -eq "parakeet") { "Green" } else { "White" }
Write-Host "  Transcriber: $Transcriber" -ForegroundColor $tcColor
Write-Host "  Translator:  $Translator"
Write-Host "  Port:        $Port"
Write-Host "========================================"
Write-Host ""

# Run server in WSL
$cmd = "cd '$WslPath' && source venv/bin/activate 2>/dev/null; python -m server.main --host 0.0.0.0 --port $Port --transcriber $Transcriber --translator $Translator --target-lang RU --source-lang en"
wsl bash -c $cmd

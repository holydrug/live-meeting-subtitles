# Run Voice Analyzer client on Windows
# Project is in WSL, client runs on Windows Python

$ProjectPath = "\\wsl.localhost\Ubuntu\home\amogusik\projects\voice-analyzer"
$Host_ = "localhost"
$Port = 9876

Write-Host "================================" -ForegroundColor Cyan
Write-Host "Voice Analyzer Client" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Server: ${Host_}:${Port}"
Write-Host "================================"
Write-Host ""

Set-Location $ProjectPath

# Activate venv if exists
if (Test-Path "venv_win\Scripts\Activate.ps1") {
    . .\venv_win\Scripts\Activate.ps1
}

python -m client.main --host $Host_ --port $Port @args

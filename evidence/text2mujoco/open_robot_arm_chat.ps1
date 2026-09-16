param()

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot

Write-Host "Opening Text2MuJoCo robot-arm chat." -ForegroundColor Green
Write-Host "Type a natural-language action, then press Run."
Write-Host "The app validates contact-only physics before opening MuJoCo Viewer."
Write-Host ""

python -m text2mujoco arm-chat

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Robot arm chat failed. Check the error message above." -ForegroundColor Red
}

Read-Host "Press Enter to close"

param(
    [string]$Spec = "",
    [double]$Speed = 0.25
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot

Write-Host "Running robot arm pick-and-place demo." -ForegroundColor Green
Write-Host "Mode: contact-only MuJoCo grasp, no cube teleport and no weld constraint."
Write-Host "Playback speed: $Speed. Default 0.25 is 4x slower than real time."
Write-Host ""

if ([string]::IsNullOrWhiteSpace($Spec)) {
    python -m text2mujoco.arm_demo_viewer --speed $Speed
} else {
    python -m text2mujoco.arm_demo_viewer --spec "$Spec" --speed $Speed
}

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Robot arm demo viewer failed. Check the error message above." -ForegroundColor Red
}

Read-Host "Press Enter to close"
